import asyncio
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Literal, Optional
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.auth import authenticate, create_session, delete_session, user_for_token
from app.database import connection, initialize_database


ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "static"
app = FastAPI(title="SahaLink API", version="1.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

MAX_PEERS_PER_ROOM = 2
SOCKET_AUTH_TIMEOUT_SECONDS = 10


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


class LoginInput(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class ConsultationInput(BaseModel):
    patient_id: int


event_clients: dict[WebSocket, dict] = {}
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


def bearer_token(request: Request) -> Optional[str]:
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    return token.strip() if scheme.lower() == "bearer" and token.strip() else None


def current_user(request: Request) -> dict:
    user = user_for_token(bearer_token(request))
    if not user:
        raise HTTPException(401, "Session absente ou expiree. Veuillez vous reconnecter.")
    return user


def doctor_only(user: dict = Depends(current_user)) -> dict:
    if user["role"] != "doctor":
        raise HTTPException(403, "Action reservee au medecin.")
    return user


def ensure_patient_access(user: dict, patient_id: int) -> None:
    if user["role"] == "patient" and user["patient_id"] != patient_id:
        raise HTTPException(403, "Acces refuse a ce dossier patient.")


def require_patient(db, patient_id: int):
    patient_row = db.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()
    if not patient_row:
        raise HTTPException(404, "Patient introuvable")
    return patient_row


def latest_consent(db, patient_id: int):
    return db.execute(
        "SELECT * FROM consents WHERE patient_id = ? ORDER BY id DESC LIMIT 1", (patient_id,)
    ).fetchone()


CONSULTATION_QUERY = """SELECT consultations.*, users.display_name AS doctor_name, patients.full_name AS patient_name
    FROM consultations
    JOIN users ON users.id = consultations.doctor_id
    JOIN patients ON patients.id = consultations.patient_id"""


def open_consultation_for(db, user: dict):
    if user["role"] == "doctor":
        clause, value = "consultations.doctor_id = ?", user["id"]
    else:
        clause, value = "consultations.patient_id = ?", user["patient_id"]
    return db.execute(
        f"{CONSULTATION_QUERY} WHERE consultations.status = 'open' AND {clause} ORDER BY consultations.id DESC LIMIT 1",
        (value,),
    ).fetchone()


def is_participant(user: dict, consultation) -> bool:
    if user["role"] == "doctor":
        return consultation["doctor_id"] == user["id"]
    return consultation["patient_id"] == user["patient_id"]


async def send_event(audience: Callable[[dict], bool], payload: dict) -> None:
    message = json.dumps(payload)
    for socket, user in list(event_clients.items()):
        if not audience(user):
            continue
        try:
            await socket.send_text(message)
        except Exception:
            event_clients.pop(socket, None)


def is_doctor(user: dict) -> bool:
    return user["role"] == "doctor"


def patient_audience(patient_id: int) -> Callable[[dict], bool]:
    return lambda user: user["role"] == "patient" and user["patient_id"] == patient_id


@app.on_event("startup")
async def startup():
    initialize_database()


@app.get("/", include_in_schema=False)
async def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "SahaLink", "data_mode": "simulated"}


@app.post("/api/auth/login")
async def login(credentials: LoginInput):
    user = authenticate(credentials.username, credentials.password)
    if not user:
        raise HTTPException(401, "Identifiant ou mot de passe incorrect.")
    return {"token": create_session(user["id"]), "user": user}


@app.post("/api/auth/logout")
async def logout(request: Request, user: dict = Depends(current_user)):
    delete_session(bearer_token(request))
    return {"status": "logged_out"}


@app.get("/api/auth/me")
async def me(user: dict = Depends(current_user)):
    return user


@app.get("/api/patients/{patient_id}")
async def patient(patient_id: int, user: dict = Depends(current_user)):
    ensure_patient_access(user, patient_id)
    with connection() as db:
        result = row_dict(require_patient(db, patient_id))
        result["latest_consent"] = row_dict(latest_consent(db, patient_id))
    return result


@app.get("/api/patients/{patient_id}/vitals")
async def vitals(patient_id: int, user: dict = Depends(current_user)):
    ensure_patient_access(user, patient_id)
    with connection() as db:
        rows = db.execute(
            "SELECT * FROM vitals WHERE patient_id = ? ORDER BY recorded_at DESC LIMIT 20", (patient_id,)
        ).fetchall()
    return [row_dict(row) for row in rows]


@app.post("/api/patients/{patient_id}/vitals", status_code=201)
async def add_vital(patient_id: int, vital: VitalInput, user: dict = Depends(current_user)):
    ensure_patient_access(user, patient_id)
    recorded_at = now_iso()
    with connection() as db:
        patient_row = require_patient(db, patient_id)
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
            asyncio.create_task(send_event(is_doctor, {"type": "alert", "alert": alert}))
            response["alert"] = alert
    return response


@app.post("/api/patients/{patient_id}/consents", status_code=201)
async def add_consent(patient_id: int, consent: ConsentInput, user: dict = Depends(current_user)):
    if user["role"] != "patient" or user["patient_id"] != patient_id:
        raise HTTPException(403, "Seul le patient concerne peut donner ou retirer son consentement.")
    created_at = now_iso()
    with connection() as db:
        require_patient(db, patient_id)
        cursor = db.execute(
            "INSERT INTO consents (patient_id, accepted, purpose, created_at) VALUES (?, ?, ?, ?)",
            (patient_id, int(consent.accepted), consent.purpose, created_at),
        )
    return {"id": cursor.lastrowid, "patient_id": patient_id, **consent.model_dump(), "created_at": created_at}


@app.get("/api/alerts")
async def alerts(user: dict = Depends(doctor_only)):
    with connection() as db:
        rows = db.execute(
            """SELECT alerts.*, patients.full_name AS patient_name FROM alerts
               JOIN patients ON patients.id = alerts.patient_id
               ORDER BY alerts.created_at DESC LIMIT 20"""
        ).fetchall()
    return [row_dict(row) for row in rows]


@app.patch("/api/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: int, user: dict = Depends(doctor_only)):
    with connection() as db:
        cursor = db.execute("UPDATE alerts SET status = 'acknowledged' WHERE id = ?", (alert_id,))
    if not cursor.rowcount:
        raise HTTPException(404, "Alerte introuvable")
    return {"id": alert_id, "status": "acknowledged"}


@app.get("/api/dashboard")
async def dashboard(user: dict = Depends(doctor_only)):
    with connection() as db:
        patient_row = db.execute("SELECT * FROM patients WHERE id = 1").fetchone()
        last_vital = db.execute("SELECT * FROM vitals WHERE patient_id = 1 ORDER BY recorded_at DESC LIMIT 1").fetchone()
        active_alerts = db.execute("SELECT COUNT(*) AS total FROM alerts WHERE status = 'open'").fetchone()["total"]
        consent = latest_consent(db, 1)
    return {"patient": row_dict(patient_row), "latest_vital": row_dict(last_vital), "open_alerts": active_alerts, "latest_consent": row_dict(consent)}


@app.post("/api/consultations", status_code=201)
async def start_consultation(request_body: ConsultationInput, user: dict = Depends(doctor_only)):
    created_at = now_iso()
    with connection() as db:
        require_patient(db, request_body.patient_id)
        consent = latest_consent(db, request_body.patient_id)
        if not consent or not consent["accepted"]:
            raise HTTPException(409, "Le patient n'a pas encore donne son consentement a la teleconsultation.")
        db.execute(
            "UPDATE consultations SET status = 'ended', ended_at = ? WHERE patient_id = ? AND status = 'open'",
            (created_at, request_body.patient_id),
        )
        consultation_id = db.execute(
            "INSERT INTO consultations (room, doctor_id, patient_id, status, created_at) VALUES (?, ?, ?, 'open', ?)",
            (secrets.token_urlsafe(12), user["id"], request_body.patient_id, created_at),
        ).lastrowid
        consultation = row_dict(db.execute(f"{CONSULTATION_QUERY} WHERE consultations.id = ?", (consultation_id,)).fetchone())
    await send_event(patient_audience(request_body.patient_id), {"type": "invitation", "consultation": consultation})
    return consultation


@app.get("/api/consultations/active")
async def active_consultation(user: dict = Depends(current_user)):
    with connection() as db:
        return row_dict(open_consultation_for(db, user))


@app.post("/api/consultations/{room}/end")
async def end_consultation(room: str, user: dict = Depends(doctor_only)):
    with connection() as db:
        consultation = db.execute(f"{CONSULTATION_QUERY} WHERE consultations.room = ?", (room,)).fetchone()
        if not consultation or not is_participant(user, consultation):
            raise HTTPException(404, "Consultation introuvable")
        db.execute("UPDATE consultations SET status = 'ended', ended_at = ? WHERE id = ?", (now_iso(), consultation["id"]))
    await send_event(patient_audience(consultation["patient_id"]), {"type": "consultation-ended", "room": room})
    return {"room": room, "status": "ended"}


def same_origin(websocket: WebSocket) -> bool:
    origin = websocket.headers.get("origin")
    return not origin or urlparse(origin).netloc == websocket.headers.get("host")


async def authenticate_socket(websocket: WebSocket) -> Optional[dict]:
    """The first message must be {"type": "auth", "token": ...}; tokens never go in the URL."""
    try:
        message = json.loads(await asyncio.wait_for(websocket.receive_text(), timeout=SOCKET_AUTH_TIMEOUT_SECONDS))
    except (asyncio.TimeoutError, ValueError, WebSocketDisconnect):
        message = {}
    user = user_for_token(message.get("token")) if isinstance(message, dict) and message.get("type") == "auth" else None
    if not user:
        try:
            await websocket.send_text(json.dumps({"type": "auth-failed"}))
            await websocket.close(code=4401)
        except Exception:
            pass
    return user


@app.websocket("/ws/events")
async def events_socket(websocket: WebSocket):
    if not same_origin(websocket):
        await websocket.close(code=4403)
        return
    await websocket.accept()
    user = await authenticate_socket(websocket)
    if not user:
        return
    event_clients[websocket] = user
    try:
        await websocket.send_text(json.dumps({"type": "auth-ok"}))
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        event_clients.pop(websocket, None)


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
    if not same_origin(websocket):
        await websocket.close(code=4403)
        return
    await websocket.accept()
    user = await authenticate_socket(websocket)
    if not user:
        return
    with connection() as db:
        consultation = db.execute(
            "SELECT * FROM consultations WHERE room = ? AND status = 'open'", (room,)
        ).fetchone()
    if not consultation or not is_participant(user, consultation):
        await websocket.send_text(json.dumps({"type": "forbidden"}))
        await websocket.close(code=4403)
        return
    peers = signal_rooms.setdefault(room, set())
    if len(peers) >= MAX_PEERS_PER_ROOM:
        await websocket.send_text(json.dumps({"type": "room-full"}))
        await websocket.close()
        return
    peers.add(websocket)
    try:
        await websocket.send_text(json.dumps({"type": "auth-ok"}))
        while True:
            await relay(peers, websocket, await websocket.receive_text())
    except WebSocketDisconnect:
        pass
    finally:
        peers.discard(websocket)
        await relay(peers, websocket, json.dumps({"type": "leave", "from": "server"}))
        if not peers:
            signal_rooms.pop(room, None)
