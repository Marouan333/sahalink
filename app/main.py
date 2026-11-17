import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.database import connection, initialize_database


ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "static"
app = FastAPI(title="SahaLink API", version="1.0.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class VitalInput(BaseModel):
    systolic: int = Field(ge=70, le=250)
    diastolic: int = Field(ge=40, le=160)
    heart_rate: int = Field(ge=30, le=220)
    spo2: int = Field(ge=70, le=100)
    temperature: float = Field(ge=32, le=43)
    source: Literal["manual", "simulated"] = "manual"


class ConsentInput(BaseModel):
    accepted: bool
    purpose: str = Field(min_length=10, max_length=300)


alert_clients: set[WebSocket] = set()
signal_rooms: dict[str, set[WebSocket]] = {}


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def row_dict(row):
    return dict(row) if row else None


def alert_for(vital: VitalInput):
    issues = []
    if vital.systolic >= 180 or vital.diastolic >= 120:
        issues.append("Tension arterielle critique")
    if vital.spo2 < 90:
        issues.append("Saturation en oxygene critique")
    if vital.heart_rate < 45 or vital.heart_rate > 130:
        issues.append("Frequence cardiaque hors seuil")
    if vital.temperature >= 39.0:
        issues.append("Fievre elevee")
    if not issues:
        return None
    severity = "critical" if any("critique" in issue for issue in issues) else "warning"
    return severity, " · ".join(issues)


async def publish_alert(alert):
    stale = []
    payload = json.dumps({"type": "alert", "alert": alert})
    for client in alert_clients:
        try:
            await client.send_text(payload)
        except Exception:
            stale.append(client)
    for client in stale:
        alert_clients.discard(client)


@app.on_event("startup")
async def startup():
    initialize_database()


@app.get("/", include_in_schema=False)
async def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "SahaLink", "data_mode": "simulated"}


@app.get("/api/patients/{patient_id}")
async def patient(patient_id: int):
    with connection() as db:
        result = db.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()
    if not result:
        raise HTTPException(404, "Patient introuvable")
    return row_dict(result)


@app.get("/api/patients/{patient_id}/vitals")
async def vitals(patient_id: int):
    with connection() as db:
        rows = db.execute(
            "SELECT * FROM vitals WHERE patient_id = ? ORDER BY recorded_at DESC LIMIT 20", (patient_id,)
        ).fetchall()
    return [row_dict(row) for row in rows]


@app.post("/api/patients/{patient_id}/vitals", status_code=201)
async def add_vital(patient_id: int, vital: VitalInput):
    recorded_at = now_iso()
    with connection() as db:
        patient_row = db.execute("SELECT full_name FROM patients WHERE id = ?", (patient_id,)).fetchone()
        if not patient_row:
            raise HTTPException(404, "Patient introuvable")
        cursor = db.execute(
            """INSERT INTO vitals (patient_id, systolic, diastolic, heart_rate, spo2, temperature, source, recorded_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (patient_id, vital.systolic, vital.diastolic, vital.heart_rate, vital.spo2, vital.temperature, vital.source, recorded_at),
        )
        response = {"id": cursor.lastrowid, "patient_id": patient_id, **vital.model_dump(), "recorded_at": recorded_at}
        evaluated = alert_for(vital)
        if evaluated:
            severity, message = evaluated
            alert_cursor = db.execute(
                "INSERT INTO alerts (patient_id, vital_id, severity, message, status, created_at) VALUES (?, ?, ?, ?, 'open', ?)",
                (patient_id, cursor.lastrowid, severity, message, recorded_at),
            )
            alert = {
                "id": alert_cursor.lastrowid,
                "patient_id": patient_id,
                "patient_name": patient_row["full_name"],
                "vital_id": cursor.lastrowid,
                "severity": severity,
                "message": message,
                "status": "open",
                "created_at": recorded_at,
            }
            asyncio.create_task(publish_alert(alert))
            response["alert"] = alert
    return response


@app.post("/api/patients/{patient_id}/consents", status_code=201)
async def add_consent(patient_id: int, consent: ConsentInput):
    created_at = now_iso()
    with connection() as db:
        if not db.execute("SELECT id FROM patients WHERE id = ?", (patient_id,)).fetchone():
            raise HTTPException(404, "Patient introuvable")
        cursor = db.execute(
            "INSERT INTO consents (patient_id, accepted, purpose, created_at) VALUES (?, ?, ?, ?)",
            (patient_id, int(consent.accepted), consent.purpose, created_at),
        )
    return {"id": cursor.lastrowid, "patient_id": patient_id, **consent.model_dump(), "created_at": created_at}


@app.get("/api/alerts")
async def alerts():
    with connection() as db:
        rows = db.execute(
            """SELECT alerts.*, patients.full_name AS patient_name FROM alerts
               JOIN patients ON patients.id = alerts.patient_id
               ORDER BY alerts.created_at DESC LIMIT 20"""
        ).fetchall()
    return [row_dict(row) for row in rows]


@app.patch("/api/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: int):
    with connection() as db:
        cursor = db.execute("UPDATE alerts SET status = 'acknowledged' WHERE id = ?", (alert_id,))
    if not cursor.rowcount:
        raise HTTPException(404, "Alerte introuvable")
    return {"id": alert_id, "status": "acknowledged"}


@app.get("/api/dashboard")
async def dashboard():
    with connection() as db:
        patient_row = db.execute("SELECT * FROM patients WHERE id = 1").fetchone()
        last_vital = db.execute("SELECT * FROM vitals WHERE patient_id = 1 ORDER BY recorded_at DESC LIMIT 1").fetchone()
        active_alerts = db.execute("SELECT COUNT(*) AS total FROM alerts WHERE status = 'open'").fetchone()["total"]
        consent = db.execute("SELECT * FROM consents WHERE patient_id = 1 ORDER BY created_at DESC LIMIT 1").fetchone()
    return {"patient": row_dict(patient_row), "latest_vital": row_dict(last_vital), "open_alerts": active_alerts, "latest_consent": row_dict(consent)}


@app.websocket("/ws/alerts")
async def alerts_socket(websocket: WebSocket):
    await websocket.accept()
    alert_clients.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        alert_clients.discard(websocket)


MAX_PEERS_PER_ROOM = 2


async def relay(peers: set[WebSocket], sender: WebSocket, message: str):
    for peer in list(peers):
        if peer is sender:
            continue
        try:
            await peer.send_text(message)
        except Exception:
            peers.discard(peer)


@app.websocket("/ws/signaling/{room}")
async def signaling_socket(websocket: WebSocket, room: str):
    await websocket.accept()
    peers = signal_rooms.setdefault(room, set())
    if len(peers) >= MAX_PEERS_PER_ROOM:
        await websocket.send_text(json.dumps({"type": "room-full"}))
        await websocket.close()
        return
    peers.add(websocket)
    try:
        while True:
            await relay(peers, websocket, await websocket.receive_text())
    except WebSocketDisconnect:
        pass
    finally:
        peers.discard(websocket)
        await relay(peers, websocket, json.dumps({"type": "leave", "from": "server"}))
        if not peers:
            signal_rooms.pop(room, None)

