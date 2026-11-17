import json
import os
import tempfile
import unittest
from pathlib import Path

os.environ["SAHALINK_DB_PATH"] = str(Path(tempfile.gettempdir()) / "sahalink-test.db")

from fastapi.testclient import TestClient

from app.database import DATABASE_PATH
from app.main import app


class SahaLinkApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Path(DATABASE_PATH).unlink(missing_ok=True)
        cls.client = TestClient(app)
        with cls.client:
            pass

    @classmethod
    def tearDownClass(cls):
        Path(DATABASE_PATH).unlink(missing_ok=True)

    def test_health_check(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_normal_vital_is_stored_without_alert(self):
        response = self.client.post("/api/patients/1/vitals", json={"systolic": 122, "diastolic": 76, "heart_rate": 68, "spo2": 98, "temperature": 36.6, "source": "simulated"})
        self.assertEqual(response.status_code, 201)
        self.assertNotIn("alert", response.json())

    def test_critical_vital_creates_an_alert(self):
        response = self.client.post("/api/patients/1/vitals", json={"systolic": 188, "diastolic": 122, "heart_rate": 138, "spo2": 89, "temperature": 39.2, "source": "simulated"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["alert"]["severity"], "critical")
        alerts = self.client.get("/api/alerts").json()
        self.assertGreaterEqual(len(alerts), 1)

    def test_acknowledge_alert(self):
        created = self.client.post("/api/patients/1/vitals", json={"systolic": 190, "diastolic": 121, "heart_rate": 80, "spo2": 98, "temperature": 36.7, "source": "simulated"}).json()
        response = self.client.patch(f"/api/alerts/{created['alert']['id']}/acknowledge")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "acknowledged")

    def test_invalid_vital_is_rejected(self):
        response = self.client.post("/api/patients/1/vitals", json={"systolic": 500, "diastolic": 76, "heart_rate": 68, "spo2": 98, "temperature": 36.6})
        self.assertEqual(response.status_code, 422)

    def test_signaling_relays_between_two_peers(self):
        with TestClient(app) as client:
            with client.websocket_connect("/ws/signaling/demo-room") as first_peer:
                with client.websocket_connect("/ws/signaling/demo-room") as second_peer:
                    first_peer.send_text('{"type":"offer","sdp":{"type":"offer"}}')
                    self.assertIn('"type":"offer"', second_peer.receive_text())

    def test_signaling_room_rejects_a_third_peer(self):
        with TestClient(app) as client:
            with client.websocket_connect("/ws/signaling/full-room"), client.websocket_connect("/ws/signaling/full-room"):
                with client.websocket_connect("/ws/signaling/full-room") as third_peer:
                    self.assertEqual(json.loads(third_peer.receive_text())["type"], "room-full")

    def test_signaling_notifies_remaining_peer_when_one_leaves(self):
        with TestClient(app) as client:
            with client.websocket_connect("/ws/signaling/leave-room") as staying_peer:
                with client.websocket_connect("/ws/signaling/leave-room"):
                    pass
                self.assertEqual(json.loads(staying_peer.receive_text())["type"], "leave")

    def test_tests_do_not_touch_the_demo_database(self):
        self.assertNotEqual(Path(DATABASE_PATH).name, "telecare.db")


if __name__ == "__main__":
    unittest.main()

