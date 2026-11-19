import json
import logging
import os
import uuid

import psycopg
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

DB_URL = os.getenv("DATABASE_URL", "postgresql://sehat:sehat_local_pw@localhost:5433/sehatsaathi")

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("patient")

app = FastAPI(title="Patient Service")
VERSION = (Path(__file__).parent / "VERSION").read_text().strip()


def jlog(event, **fields):
    log.info(json.dumps({"service": "patient", "event": event, **fields}))


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    cid = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    request.state.cid = cid
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = cid
    return response


class PatientIn(BaseModel):
    name: str
    phone: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/version")
def version():
    return {"service": "patient", "version": VERSION}


@app.get("/", response_class=HTMLResponse)
def home():
    return f"<h1>SehatSaathi Patient Service</h1><p>Version: {VERSION}</p>"


@app.post("/patients", status_code=201)
def register_patient(body: PatientIn, request: Request):
    with psycopg.connect(DB_URL) as conn:
        pid = conn.execute(
            "INSERT INTO patient.patients (name, phone) VALUES (%s, %s) RETURNING id",
            (body.name, body.phone),
        ).fetchone()[0]
    jlog("registered", correlation_id=request.state.cid, patient_id=pid)
    return {"id": pid, "name": body.name, "phone": body.phone}


@app.get("/patients/{patient_id}")
def get_patient(patient_id: int):
    with psycopg.connect(DB_URL) as conn:
        r = conn.execute(
            "SELECT id, name, phone FROM patient.patients WHERE id = %s", (patient_id,)
        ).fetchone()
    if r is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {"id": r[0], "name": r[1], "phone": r[2]}