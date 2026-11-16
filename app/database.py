import sqlite3
from contextlib import contextmanager
from pathlib import Path


DATABASE_PATH = Path(__file__).resolve().parent.parent / "telecare.db"


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

