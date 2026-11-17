import hashlib
import hmac
import os
import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path


DATABASE_PATH = Path(os.environ.get("SAHALINK_DB_PATH") or Path(__file__).resolve().parent.parent / "telecare.db")
PBKDF2_ITERATIONS = 200_000
DEMO_PASSWORD = "Demo-2026!"
DEMO_USERS = (
    ("dr.benali", "Dr. Benali", "doctor", None),
    ("amal", "Amal El Idrissi", "patient", 1),
)


def hash_password(password: str, salt_hex: str):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), PBKDF2_ITERATIONS).hex()


def verify_password(password: str, salt_hex: str, expected_hex: str) -> bool:
    return hmac.compare_digest(hash_password(password, salt_hex), expected_hex)


@contextmanager
def connection():
    db = sqlite3.connect(DATABASE_PATH)
    db.row_factory = sqlite3.Row
    try:
        yield db
        db.commit()
    finally:
        db.close()


def initialize_database():
    with connection() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY,
                full_name TEXT NOT NULL,
                birth_year INTEGER NOT NULL,
                care_plan TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS consents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                accepted INTEGER NOT NULL,
                purpose TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(patient_id) REFERENCES patients(id)
            );
            CREATE TABLE IF NOT EXISTS vitals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                systolic INTEGER NOT NULL,
                diastolic INTEGER NOT NULL,
                heart_rate INTEGER NOT NULL,
                spo2 INTEGER NOT NULL,
                temperature REAL NOT NULL,
                source TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                FOREIGN KEY(patient_id) REFERENCES patients(id)
            );
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                vital_id INTEGER NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                created_at TEXT NOT NULL,
                FOREIGN KEY(patient_id) REFERENCES patients(id),
                FOREIGN KEY(vital_id) REFERENCES vitals(id)
            );
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('doctor', 'patient')),
                patient_id INTEGER,
                password_salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                FOREIGN KEY(patient_id) REFERENCES patients(id)
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS consultations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room TEXT NOT NULL UNIQUE,
                doctor_id INTEGER NOT NULL,
                patient_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                created_at TEXT NOT NULL,
                ended_at TEXT,
                FOREIGN KEY(doctor_id) REFERENCES users(id),
                FOREIGN KEY(patient_id) REFERENCES patients(id)
            );
            """
        )
        patient = db.execute("SELECT id FROM patients WHERE id = 1").fetchone()
        if not patient:
            db.execute(
                "INSERT INTO patients (id, full_name, birth_year, care_plan) VALUES (1, ?, ?, ?)",
                ("Amal El Idrissi", 1972, "Suivi hypertension arterielle"),
            )
        vital = db.execute("SELECT id FROM vitals WHERE patient_id = 1 LIMIT 1").fetchone()
        if not vital:
            db.execute(
                """INSERT INTO vitals (patient_id, systolic, diastolic, heart_rate, spo2, temperature, source, recorded_at)
                   VALUES (1, 128, 78, 72, 98, 36.7, 'simulated', '2026-11-16T09:15:00+00:00')"""
            )
        for username, display_name, role, patient_id in DEMO_USERS:
            if db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone():
                continue
            salt = secrets.token_hex(16)
            db.execute(
                """INSERT INTO users (username, display_name, role, patient_id, password_salt, password_hash)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (username, display_name, role, patient_id, salt, hash_password(DEMO_PASSWORD, salt)),
            )

