import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone

import psycopg
import redis
from fastapi import FastAPI, HTTPException, Request, Response
from psycopg.types.json import Jsonb
from pydantic import BaseModel

DB_URL = os.getenv("DATABASE_URL", "postgresql://sehat:sehat_local_pw@localhost:5433/sehatsaathi")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_TTL_SECONDS = 60

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("scheduling")

app = FastAPI(title="Scheduling Service")
cache = redis.Redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=1, socket_connect_timeout=1)


def jlog(event, **fields):
    log.info(json.dumps({"service": "scheduling", "event": event, **fields}))


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    cid = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    request.state.cid = cid
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = cid
    return response


def read_slots_from_db(doctor_id: int):
    with psycopg.connect(DB_URL) as conn:
        rows = conn.execute(
            "SELECT id, start_time, status FROM scheduling.slots "
            "WHERE doctor_id = %s ORDER BY start_time",
            (doctor_id,),
        ).fetchall()
    return [{"id": r[0], "start_time": r[1].isoformat(), "status": r[2]} for r in rows]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/doctors/{doctor_id}/slots")
def get_slots(doctor_id: int, request: Request, response: Response):
    started = time.perf_counter()
    key = f"schedule:{doctor_id}"
    source = "redis"

    try:
        cached = cache.get(key)
    except redis.RedisError as e:
        cached = None
        jlog("redis_unavailable", correlation_id=request.state.cid, error=str(e))

    if cached:
        slots = json.loads(cached)
    else:
        source = "postgres"
        slots = read_slots_from_db(doctor_id)
        try:
            cache.setex(key, CACHE_TTL_SECONDS, json.dumps(slots))
        except redis.RedisError:
            pass

    elapsed_ms = (time.perf_counter() - started) * 1000
    response.headers["X-Source"] = source
    response.headers["X-Time-Ms"] = f"{elapsed_ms:.2f}"
    jlog("get_slots", correlation_id=request.state.cid, doctor_id=doctor_id,
         source=source, ms=round(elapsed_ms, 2))
    return {"doctor_id": doctor_id, "source": source, "slots": slots}


class BookingRequest(BaseModel):
    slot_id: int
    patient_id: int


@app.post("/appointments", status_code=201)
def book_appointment(body: BookingRequest, request: Request):
    cid = request.state.cid
    try:
        with psycopg.connect(DB_URL) as conn:
            # take the slot only if it is still free
            slot = conn.execute(
                "UPDATE scheduling.slots SET status = 'booked' "
                "WHERE id = %s AND status = 'free' "
                "RETURNING doctor_id, start_time",
                (body.slot_id,),
            ).fetchone()
            if slot is None:
                jlog("booking_rejected", correlation_id=cid, slot_id=body.slot_id)
                raise HTTPException(status_code=409, detail="Slot is not available")
            doctor_id, start_time = slot

            appt_id = conn.execute(
                "INSERT INTO scheduling.appointments (slot_id, patient_id) "
                "VALUES (%s, %s) RETURNING id",
                (body.slot_id, body.patient_id),
            ).fetchone()[0]

            event = {
                "event_id": str(uuid.uuid4()),
                "type": "AppointmentBooked",
                "occurred_at": datetime.now(timezone.utc).isoformat(),
                "correlation_id": cid,
                "appointment_id": appt_id,
                "patient_id": body.patient_id,
                "doctor_id": doctor_id,
                "slot_time": start_time.isoformat(),
            }
            conn.execute(
                "INSERT INTO scheduling.outbox (event_type, payload, correlation_id) "
                "VALUES (%s, %s, %s)",
                ("AppointmentBooked", Jsonb(event), cid),
            )
        # the with-block commits everything together if we got here
    except psycopg.errors.UniqueViolation:
        raise HTTPException(status_code=409, detail="Slot is not available")

    try:
        cache.delete(f"schedule:{doctor_id}")
    except redis.RedisError:
        pass

    jlog("booked", correlation_id=cid, appointment_id=appt_id, slot_id=body.slot_id)
    return {"appointment_id": appt_id, "slot_id": body.slot_id, "doctor_id": doctor_id}