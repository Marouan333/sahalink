import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.database import connection, verify_password


SESSION_LIFETIME = timedelta(hours=8)
PUBLIC_USER_FIELDS = ("id", "username", "display_name", "role", "patient_id")


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def public_user(row) -> dict:
    return {field: row[field] for field in PUBLIC_USER_FIELDS}


def authenticate(username: str, password: str) -> Optional[dict]:
    with connection() as db:
        row = db.execute("SELECT * FROM users WHERE username = ?", (username.strip().lower(),)).fetchone()
    if not row or not verify_password(password, row["password_salt"], row["password_hash"]):
        return None
    return public_user(row)


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    with connection() as db:
        db.execute("DELETE FROM sessions WHERE expires_at < ?", (_now().isoformat(),))
        db.execute(
            "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
            (_token_hash(token), user_id, (_now() + SESSION_LIFETIME).isoformat()),
        )
    return token


def user_for_token(token: Optional[str]) -> Optional[dict]:
    if not token:
        return None
    with connection() as db:
        row = db.execute(
            """SELECT users.* FROM sessions JOIN users ON users.id = sessions.user_id
               WHERE sessions.token_hash = ? AND sessions.expires_at > ?""",
            (_token_hash(token), _now().isoformat()),
        ).fetchone()
    return public_user(row) if row else None


def delete_session(token: Optional[str]) -> None:
    if not token:
        return
    with connection() as db:
        db.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))
