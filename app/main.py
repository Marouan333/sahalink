import asyncio
import json
import os
import re
import secrets
import sqlite3
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Literal, Optional
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from app.auth import authenticate, create_session, delete_session, user_for_token
from app.database import connection, hash_password, initialize_database


ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "static"
app = FastAPI(title="SahaLink API", version="1.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

MAX_PEERS_PER_ROOM = 2
SOCKET_AUTH_TIMEOUT_SECONDS = 10
DEFAULT_ICE_SERVERS = [{"urls": ["stun:stun.l.google.com:19302", "stun:stun.cloudflare.com:3478"]}]


def configured_ice_servers() -> list:
    """ICE_SERVERS may hold a JSON list of RTCIceServer objects, e.g. a TURN relay for strict NATs."""
    raw = os.environ.get("ICE_SERVERS", "").strip()
    if not raw:
        return DEFAULT_ICE_SERVERS
    try:
        servers = json.loads(raw)
    except ValueError:
        return DEFAULT_ICE_SERVERS
    return servers if isinstance(servers, list) and servers else DEFAULT_ICE_SERVERS


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


USERNAME_PATTERN = re.compile(r"^[a-z0-9._-]{3,32}$")
NAME_PATTERN = re.compile(r"^[^\W\d_][\w .'’-]{1,59}$")
CARE_PLAN_FORBIDDEN = re.compile(r"[<>]")
MAX_PATIENTS = 200


class RegisterInput(BaseModel):
    username: str
    display_name: str
    password: str = Field(min_length=8, max_length=128)
    birth_year: int = Field(ge=1900, le=datetime.now().year)
    care_plan: str = Field(default="Suivi à distance", max_length=80)

    @field_validator("username", mode="before")
    @classmethod
    def normalise_username(cls, value):
        value = str(value).strip().lower()
        if not USERNAME_PATTERN.match(value):
            raise ValueError("L'identifiant doit contenir 3 à 32 caractères : lettres minuscules, chiffres, point, tiret ou tiret bas.")
        return value

    @field_validator("display_name", mode="before")
    @classmethod
    def clean_display_name(cls, value):
        value = re.sub(r"\s+", " ", str(value)).strip()
        if not NAME_PATTERN.match(value):
            raise ValueError("Le nom doit contenir 2 à 60 caractères : lettres, espaces, apostrophe, point ou tiret.")
        return value

    @field_validator("care_plan", mode="before")
    @classmethod
    def clean_care_plan(cls, value):
        value = re.sub(r"\s+", " ", str(value or "")).strip() or "Suivi à distance"
        if CARE_PLAN_FORBIDDEN.search(value):
            raise ValueError("Le motif du suivi ne peut pas contenir de chevrons.")
        return value


class RateLimiter:
    """In-memory sliding-window counter; enough to slow guessing and sign-up spam on one server."""

    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window = window_seconds
        self.events: dict[str, deque] = defaultdict(deque)

    def _prune(self, key: str) -> deque:
        queue = self.events[key]
        cutoff = time.monotonic() - self.window
        while queue and queue[0] < cutoff:
            queue.popleft()
        if not queue:
            self.events.pop(key, None)
        return queue

    def blocked(self, key: str) -> bool:
        return len(self._prune(key)) >= self.limit

    def hit(self, key: str) -> None:
        self._prune(key)
        self.events[key].append(time.monotonic())

    def clear(self, key: str) -> None:
        self.events.pop(key, None)

    def reset(self) -> None:
        self.events.clear()


login_limiter = RateLimiter(limit=8, window_seconds=300)
register_limiter = RateLimiter(limit=10, window_seconds=3600)


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "inconnu"


event_clients: dict[WebSocket, dict] = {}
signal_rooms: dict[str, set[WebSocket]] = {}


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def row_dict(row):
    return dict(row) if row else None


def alert_for(vital: VitalInput):
    issues = []
    if vital.systolic >= 180 or vital.diastolic >= 120:
        issues.append("Tension artérielle critique")
    if vital.spo2 < 90:
        issues.append("Saturation en oxygène critique")
    if vital.heart_rate < 45 or vital.heart_rate > 130:
        issues.append("Fréquence cardiaque hors seuil")
    if vital.temperature >= 39.0:
        issues.append("Fièvre élevée")
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
        raise HTTPException(403, "Action réservée au médecin.")
    return user


def ensure_patient_access(user: dict, patient_id: int) -> None:
    if user["role"] == "patient" and user["patient_id"] != patient_id:
        raise HTTPException(403, "Accès refusé à ce dossier patient.")


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


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(self), microphone=(self), geolocation=()"
    if request.url.path == "/" or request.url.path.startswith("/static/"):
        # Names typed by patients reach the doctor's screen, so scripts from anywhere else must never run.
        host = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; "
            "font-src https://fonts.gstatic.com; img-src 'self' data:; media-src 'self' blob:; "
            f"connect-src 'self' wss://{host} ws://{host}; object-src 'none'; base-uri 'none'; "
            "form-action 'self'; frame-ancestors 'none'"
        )
    return response


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
async def login(credentials: LoginInput, request: Request):
    key = f"{client_ip(request)}|{credentials.username.strip().lower()}"
    if login_limiter.blocked(key):
        raise HTTPException(429, "Trop de tentatives échouées. Réessayez dans quelques minutes.")
    user = await run_in_threadpool(authenticate, credentials.username, credentials.password)
    if not user:
        login_limiter.hit(key)
        raise HTTPException(401, "Identifiant ou mot de passe incorrect.")
    login_limiter.clear(key)
    return {"token": create_session(user["id"]), "user": user}


@app.post("/api/auth/register", status_code=201)
async def register(data: RegisterInput, request: Request):
    ip = client_ip(request)
    if register_limiter.blocked(ip):
        raise HTTPException(429, "Trop de créations de compte depuis cette adresse. Réessayez plus tard.")
    register_limiter.hit(ip)
    salt = secrets.token_hex(16)
    password_hash = await run_in_threadpool(hash_password, data.password, salt)
    try:
        with connection() as db:
            if db.execute("SELECT COUNT(*) AS total FROM patients").fetchone()["total"] >= MAX_PATIENTS:
                raise HTTPException(409, "Le nombre maximal de comptes de démonstration est atteint.")
            patient_id = db.execute(
                "INSERT INTO patients (full_name, birth_year, care_plan) VALUES (?, ?, ?)",
                (data.display_name, data.birth_year, data.care_plan),
            ).lastrowid
            user_id = db.execute(
                """INSERT INTO users (username, display_name, role, patient_id, password_salt, password_hash)
                   VALUES (?, ?, 'patient', ?, ?, ?)""",
                (data.username, data.display_name, patient_id, salt, password_hash),
            ).lastrowid
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Cet identifiant est déjà utilisé.")
    asyncio.create_task(send_event(is_doctor, {"type": "patient-registered", "patient_id": patient_id}))
    token = create_session(user_id)
    return {"token": token, "user": user_for_token(token)}


@app.post("/api/auth/logout")
async def logout(request: Request, user: dict = Depends(current_user)):
    delete_session(bearer_token(request))
    return {"status": "logged_out"}


@app.get("/api/auth/me")
async def me(user: dict = Depends(current_user)):
    return user


@app.get("/api/rtc-config")
async def rtc_config(user: dict = Depends(current_user)):
    return {"iceServers": configured_ice_servers()}


@app.get("/api/patients")
async def patients(user: dict = Depends(doctor_only)):
    with connection() as db:
        rows = db.execute(
            """SELECT p.id, p.full_name, p.birth_year, p.care_plan,
                      (SELECT accepted FROM consents c WHERE c.patient_id = p.id ORDER BY c.id DESC LIMIT 1) AS consent_accepted,
                      (SELECT COUNT(*) FROM alerts a WHERE a.patient_id = p.id AND a.status = 'open') AS open_alerts,
                      (SELECT MAX(recorded_at) FROM vitals v WHERE v.patient_id = p.id) AS last_reading_at
               FROM patients p ORDER BY open_alerts DESC, p.full_name COLLATE NOCASE"""
        ).fetchall()
    return [row_dict(row) for row in rows]


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
            "SELECT * FROM vitals WHERE patient_id = ? ORDER BY recorded_at DESC, id DESC LIMIT 30", (patient_id,)
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
        else:
            asyncio.create_task(send_event(is_doctor, {"type": "vital", "patient_id": patient_id}))
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
    asyncio.create_task(send_event(is_doctor, {"type": "consent", "patient_id": patient_id, "accepted": consent.accepted}))
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
async def dashboard(patient_id: Optional[int] = None, user: dict = Depends(doctor_only)):
    with connection() as db:
        if patient_id is None:
            first = db.execute("SELECT id FROM patients ORDER BY id LIMIT 1").fetchone()
            patient_id = first["id"] if first else None
        patient_row = db.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone() if patient_id else None
        if patient_id and not patient_row:
            raise HTTPException(404, "Patient introuvable")
        last_vital = (
            db.execute("SELECT * FROM vitals WHERE patient_id = ? ORDER BY recorded_at DESC, id DESC LIMIT 1", (patient_id,)).fetchone()
            if patient_row else None
        )
        consent = latest_consent(db, patient_id) if patient_row else None
        active_alerts = db.execute("SELECT COUNT(*) AS total FROM alerts WHERE status = 'open'").fetchone()["total"]
        patients_total = db.execute("SELECT COUNT(*) AS total FROM patients").fetchone()["total"]
    return {
        "patient": row_dict(patient_row),
        "latest_vital": row_dict(last_vital),
        "open_alerts": active_alerts,
        "latest_consent": row_dict(consent),
        "patients_total": patients_total,
    }


@app.post("/api/consultations", status_code=201)
async def start_consultation(request_body: ConsultationInput, user: dict = Depends(doctor_only)):
    created_at = now_iso()
    with connection() as db:
        require_patient(db, request_body.patient_id)
        consent = latest_consent(db, request_body.patient_id)
        if not consent or not consent["accepted"]:
            raise HTTPException(409, "Le patient n'a pas encore donné son consentement à la téléconsultation.")
        # A doctor runs one consultation at a time and a patient has at most one open room.
        replaced = db.execute(
            "SELECT room, patient_id FROM consultations WHERE status = 'open' AND (doctor_id = ? OR patient_id = ?)",
            (user["id"], request_body.patient_id),
        ).fetchall()
        db.execute(
            "UPDATE consultations SET status = 'ended', ended_at = ? WHERE status = 'open' AND (doctor_id = ? OR patient_id = ?)",
            (created_at, user["id"], request_body.patient_id),
        )
        consultation_id = db.execute(
            "INSERT INTO consultations (room, doctor_id, patient_id, status, created_at) VALUES (?, ?, ?, 'open', ?)",
            (secrets.token_urlsafe(12), user["id"], request_body.patient_id, created_at),
        ).lastrowid
        consultation = row_dict(db.execute(f"{CONSULTATION_QUERY} WHERE consultations.id = ?", (consultation_id,)).fetchone())
    for old in replaced:
        await send_event(patient_audience(old["patient_id"]), {"type": "consultation-ended", "room": old["room"]})
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
    if not origin:
        return True
    # Behind a tunnel or reverse proxy the public host arrives in X-Forwarded-Host.
    hosts = {websocket.headers.get("host"), websocket.headers.get("x-forwarded-host")}
    return urlparse(origin).netloc in hosts


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
