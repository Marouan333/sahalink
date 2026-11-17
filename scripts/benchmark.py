"""Mesure chiffree des performances de l'API SahaLink (voir docs/validation.md).

Usage: python scripts/benchmark.py
"""
import os
import random
import statistics
import tempfile
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["SAHALINK_DB_PATH"] = str(Path(tempfile.gettempdir()) / "sahalink-benchmark.db")

from fastapi.testclient import TestClient

from app.database import DATABASE_PATH
from app.main import app

Path(DATABASE_PATH).unlink(missing_ok=True)
client = TestClient(app)

with client:
    normal_latencies = []
    for _ in range(30):
        payload = {
            "systolic": random.randint(100, 135),
            "diastolic": random.randint(65, 85),
            "heart_rate": random.randint(60, 90),
            "spo2": random.randint(95, 100),
            "temperature": round(random.uniform(36.2, 37.2), 1),
            "source": "simulated",
        }
        t0 = time.perf_counter()
        response = client.post("/api/patients/1/vitals", json=payload)
        t1 = time.perf_counter()
        assert response.status_code == 201
        normal_latencies.append((t1 - t0) * 1000)

    degraded_cases = [
        {"systolic": 188, "diastolic": 122, "heart_rate": 138, "spo2": 89, "temperature": 39.2, "source": "simulated"},
        {"systolic": 185, "diastolic": 80, "heart_rate": 75, "spo2": 98, "temperature": 36.8, "source": "simulated"},
        {"systolic": 120, "diastolic": 75, "heart_rate": 75, "spo2": 88, "temperature": 36.8, "source": "simulated"},
        {"systolic": 120, "diastolic": 75, "heart_rate": 40, "spo2": 98, "temperature": 36.8, "source": "simulated"},
        {"systolic": 120, "diastolic": 75, "heart_rate": 135, "spo2": 98, "temperature": 36.8, "source": "simulated"},
        {"systolic": 120, "diastolic": 75, "heart_rate": 75, "spo2": 98, "temperature": 39.5, "source": "simulated"},
    ]
    detection_latencies = []
    detected = 0
    for case in degraded_cases:
        t0 = time.perf_counter()
        response = client.post("/api/patients/1/vitals", json=case)
        t1 = time.perf_counter()
        assert response.status_code == 201
        if "alert" in response.json():
            detected += 1
            detection_latencies.append((t1 - t0) * 1000)

    invalid_cases = [
        {"systolic": 500, "diastolic": 76, "heart_rate": 68, "spo2": 98, "temperature": 36.6},
        {"systolic": 120, "diastolic": 76, "heart_rate": 68, "spo2": 150, "temperature": 36.6},
        {"systolic": 120, "diastolic": 76, "heart_rate": 68, "spo2": 98, "temperature": 60.0},
    ]
    rejected = sum(1 for case in invalid_cases if client.post("/api/patients/1/vitals", json=case).status_code == 422)

    ack_latencies = []
    for _ in range(10):
        created = client.post(
            "/api/patients/1/vitals",
            json={"systolic": 190, "diastolic": 121, "heart_rate": 80, "spo2": 98, "temperature": 36.7, "source": "simulated"},
        ).json()
        t0 = time.perf_counter()
        ack = client.patch(f"/api/alerts/{created['alert']['id']}/acknowledge")
        t1 = time.perf_counter()
        assert ack.status_code == 200
        ack_latencies.append((t1 - t0) * 1000)

print("=== Latence d'ecriture d'une mesure normale (ms), n=30 ===")
print(
    f"moyenne={statistics.mean(normal_latencies):.2f} mediane={statistics.median(normal_latencies):.2f} "
    f"min={min(normal_latencies):.2f} max={max(normal_latencies):.2f} ecart-type={statistics.stdev(normal_latencies):.2f}"
)

print("\n=== Detection du cas degrade ===")
print(f"detecte {detected}/{len(degraded_cases)} = {100 * detected / len(degraded_cases):.1f}%")
if detection_latencies:
    print(
        f"latence creation alerte moyenne={statistics.mean(detection_latencies):.2f}ms "
        f"min={min(detection_latencies):.2f}ms max={max(detection_latencies):.2f}ms"
    )

print("\n=== Rejet des valeurs hors plage ===")
print(f"rejete {rejected}/{len(invalid_cases)} = {100 * rejected / len(invalid_cases):.1f}%")

print("\n=== Latence d'acquittement d'une alerte (ms), n=10 ===")
print(f"moyenne={statistics.mean(ack_latencies):.2f} min={min(ack_latencies):.2f} max={max(ack_latencies):.2f}")

Path(DATABASE_PATH).unlink(missing_ok=True)
