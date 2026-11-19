import json
import logging
import os
import uuid
from datetime import datetime, timezone

import psycopg
import redis
from fastapi import FastAPI, HTTPException, Request
from psycopg.types.json import Jsonb
from pydantic import BaseModel

DB_URL = os.getenv("DATABASE_URL", "postgresql://sehat:sehat_local_pw@localhost:5433/sehatsaathi")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("queue")

app = FastAPI(title="Queue Service")
cache = redis.Redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=1, socket_connect_timeout=1)


def jlog(event, **fields):
    log.info(json.dumps({"service": "queue", "event": event, **fields}))


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    cid = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    request.state.cid = cid
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = cid
    return response


def drop_cache(doctor_id):
    try:
        cache.delete(f"queue:{doctor_id}")
    except redis.RedisError:
        pass


class CheckIn(BaseModel):
    doctor_id: int
    patient_id: int
    appointment_id: int | None = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/checkins", status_code=201)
def check_in(body: CheckIn, request: Request):
    with psycopg.connect(DB_URL) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (body.doctor_id,))
        token = conn.execute(
            "SELECT COALESCE(MAX(token_no), 0) + 1 FROM queue.checkins WHERE doctor_id = %s",
            (body.doctor_id,),
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO queue.checkins (doctor_id, patient_id, appointment_id, token_no) "
            "VALUES (%s, %s, %s, %s)",
            (body.doctor_id, body.patient_id, body.appointment_id, token),
        )
    drop_cache(body.doctor_id)
    jlog("checked_in", correlation_id=request.state.cid, doctor_id=body.doctor_id, token_no=token)
    return {"doctor_id": body.doctor_id, "patient_id": body.patient_id, "token_no": token}


@app.get("/doctors/{doctor_id}/queue")
def get_queue(doctor_id: int, request: Request):
    key = f"queue:{doctor_id}"
    source = "redis"
    try:
        cached = cache.get(key)
    except redis.RedisError as e:
        cached = None
        jlog("redis_unavailable", correlation_id=request.state.cid, error=str(e))

    if cached:
        waiting = json.loads(cached)
    else:
        source = "postgres"
        with psycopg.connect(DB_URL) as conn:
            rows = conn.execute(
                "SELECT token_no, patient_id FROM queue.checkins "
                "WHERE doctor_id = %s AND status = 'waiting' ORDER BY token_no",
                (doctor_id,),
            ).fetchall()
        waiting = [{"position": i + 1, "token_no": r[0], "patient_id": r[1]} for i, r in enumerate(rows)]
        try:
            cache.setex(key, 30, json.dumps(waiting))
        except redis.RedisError:
            pass
    jlog("get_queue", correlation_id=request.state.cid, doctor_id=doctor_id, source=source)
    return {"doctor_id": doctor_id, "source": source, "waiting": waiting}


@app.post("/doctors/{doctor_id}/call-next")
def call_next(doctor_id: int, request: Request):
    cid = request.state.cid
    with psycopg.connect(DB_URL) as conn:
        called = conn.execute(
            "UPDATE queue.checkins SET status = 'called' WHERE id = ("
            " SELECT id FROM queue.checkins WHERE doctor_id = %s AND status = 'waiting'"
            " ORDER BY token_no LIMIT 1 FOR UPDATE SKIP LOCKED) "
            "RETURNING token_no, patient_id",
            (doctor_id,),
        ).fetchone()
        if called is None:
            raise HTTPException(status_code=404, detail="Nobody is waiting")
        nxt = conn.execute(
            "SELECT token_no, patient_id FROM queue.checkins "
            "WHERE doctor_id = %s AND status = 'waiting' ORDER BY token_no LIMIT 1",
            (doctor_id,),
        ).fetchone()
        event = {
            "event_id": str(uuid.uuid4()),
            "type": "QueueMoved",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "correlation_id": cid,
            "doctor_id": doctor_id,
            "called_token": called[0],
            "called_patient_id": called[1],
            "notify_patient_id": nxt[1] if nxt else None,
        }
        conn.execute(
            "INSERT INTO queue.outbox (event_type, payload, correlation_id) VALUES (%s, %s, %s)",
            ("QueueMoved", Jsonb(event), cid),
        )
    drop_cache(doctor_id)
    jlog("called_next", correlation_id=cid, doctor_id=doctor_id, token_no=called[0])
    return {"called_token": called[0], "called_patient_id": called[1],
            "notify_patient_id": event["notify_patient_id"]}