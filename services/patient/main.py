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


HOME_HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SehatSaathi</title>
<style>
*{box-sizing:border-box}
body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;font-family:Segoe UI,Arial,sans-serif;background:linear-gradient(135deg,#0f766e,#0ea5e9);color:#0f172a}
.card{background:#fff;border-radius:20px;padding:40px;max-width:560px;width:92%;text-align:center;box-shadow:0 20px 50px rgba(0,0,0,.25)}
.logo{font-size:48px}
h1{margin:8px 0 4px;font-size:32px;color:#0f766e}
.sub{color:#475569;margin:0 0 24px}
.ver{display:inline-block;background:#ecfeff;color:#0e7490;border:2px solid #67e8f9;border-radius:999px;padding:10px 26px;font-size:30px;font-weight:700;margin-bottom:24px}
.links a{display:inline-block;margin:6px;padding:10px 20px;border-radius:10px;background:#0f766e;color:#fff;text-decoration:none;font-weight:600}
.links a:hover{background:#115e59}
.foot{margin-top:24px;font-size:13px;color:#64748b}
</style></head><body>
<div class="card">
<div class="logo">&#127973;</div>
<h1>SehatSaathi</h1>
<p class="sub">Hospital Appointment &amp; Queue System &middot; Patient Service</p>
<div class="ver">Version __VERSION__</div>
<div class="links">
<a href="/docs">API Docs (Swagger)</a>
<a href="/health">Health</a>
<a href="/version">Version JSON</a>
</div>
<p class="foot">Deployed automatically by GitHub Actions &rarr; S3 &rarr; EC2</p>
</div></body></html>"""


@app.get("/", response_class=HTMLResponse)
def home():
    return HOME_HTML.replace("__VERSION__", VERSION)


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