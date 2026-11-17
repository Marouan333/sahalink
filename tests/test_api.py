import json
import os
import tempfile
import unittest
from pathlib import Path

os.environ["SAHALINK_DB_PATH"] = str(Path(tempfile.gettempdir()) / "sahalink-test.db")

from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.database import DATABASE_PATH, DEMO_PASSWORD
from app.main import app


NORMAL_VITAL = {"systolic": 122, "diastolic": 76, "heart_rate": 68, "spo2": 98, "temperature": 36.6, "source": "simulated"}
CRITICAL_VITAL = {"systolic": 188, "diastolic": 122, "heart_rate": 138, "spo2": 89, "temperature": 39.2, "source": "simulated"}


class SahaLinkApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Path(DATABASE_PATH).unlink(missing_ok=True)
        cls.client = TestClient(app)
        cls.client.__enter__()
        cls.doctor_token = cls.login("dr.benali")
        cls.patient_token = cls.login("amal")

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)
        Path(DATABASE_PATH).unlink(missing_ok=True)

    @classmethod
    def login(cls, username, password=DEMO_PASSWORD):
        response = cls.client.post("/api/auth/login", json={"username": username, "password": password})
        assert response.status_code == 200, response.text
        return response.json()["token"]

    @staticmethod
    def auth(token):
        return {"Authorization": f"Bearer {token}"}

    def give_consent(self):
        response = self.client.post(
            "/api/patients/1/consents",
            json={"accepted": True, "purpose": "Teleconsultation pedagogique et suivi des constantes."},
            headers=self.auth(self.patient_token),
        )
        self.assertEqual(response.status_code, 201)

    def start_consultation(self):
        self.give_consent()
        response = self.client.post("/api/consultations", json={"patient_id": 1}, headers=self.auth(self.doctor_token))
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def join_room(self, room, token):
        socket = self.client.websocket_connect(f"/ws/signaling/{room}")
        peer = socket.__enter__()
        peer.send_text(json.dumps({"type": "auth", "token": token}))
        return socket, peer

    def test_health_check_is_public(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_login_rejects_a_wrong_password(self):
        response = self.client.post("/api/auth/login", json={"username": "dr.benali", "password": "wrong"})
        self.assertEqual(response.status_code, 401)

    def test_me_returns_the_role(self):
        doctor = self.client.get("/api/auth/me", headers=self.auth(self.doctor_token)).json()
        patient = self.client.get("/api/auth/me", headers=self.auth(self.patient_token)).json()
        self.assertEqual((doctor["role"], patient["role"], patient["patient_id"]), ("doctor", "patient", 1))

    def test_logout_invalidates_the_session(self):
        token = self.login("amal")
        self.client.post("/api/auth/logout", headers=self.auth(token))
        self.assertEqual(self.client.get("/api/auth/me", headers=self.auth(token)).status_code, 401)

    def test_health_data_requires_a_session(self):
        self.assertEqual(self.client.get("/api/patients/1/vitals").status_code, 401)
        self.assertEqual(self.client.get("/api/alerts").status_code, 401)

    def test_patient_cannot_read_alerts_or_acknowledge(self):
        self.assertEqual(self.client.get("/api/alerts", headers=self.auth(self.patient_token)).status_code, 403)
        self.assertEqual(self.client.patch("/api/alerts/1/acknowledge", headers=self.auth(self.patient_token)).status_code, 403)

    def test_patient_cannot_read_another_patient(self):
        response = self.client.get("/api/patients/2/vitals", headers=self.auth(self.patient_token))
        self.assertEqual(response.status_code, 403)

    def test_only_the_patient_can_give_consent(self):
        response = self.client.post(
            "/api/patients/1/consents",
            json={"accepted": True, "purpose": "Tentative de consentement par le medecin."},
            headers=self.auth(self.doctor_token),
        )
        self.assertEqual(response.status_code, 403)

    def test_normal_vital_is_stored_without_alert(self):
        response = self.client.post("/api/patients/1/vitals", json=NORMAL_VITAL, headers=self.auth(self.patient_token))
        self.assertEqual(response.status_code, 201)
        self.assertNotIn("alert", response.json())

    def test_critical_vital_alerts_the_doctor(self):
        response = self.client.post("/api/patients/1/vitals", json=CRITICAL_VITAL, headers=self.auth(self.patient_token))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["alert"]["severity"], "critical")
        alerts = self.client.get("/api/alerts", headers=self.auth(self.doctor_token)).json()
        self.assertGreaterEqual(len(alerts), 1)

    def test_doctor_acknowledges_alert(self):
        created = self.client.post("/api/patients/1/vitals", json=CRITICAL_VITAL, headers=self.auth(self.patient_token)).json()
        response = self.client.patch(f"/api/alerts/{created['alert']['id']}/acknowledge", headers=self.auth(self.doctor_token))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "acknowledged")

    def test_invalid_vital_is_rejected(self):
        invalid = {**NORMAL_VITAL, "systolic": 500}
        response = self.client.post("/api/patients/1/vitals", json=invalid, headers=self.auth(self.patient_token))
        self.assertEqual(response.status_code, 422)

    def test_consultation_requires_consent(self):
        self.client.post(
            "/api/patients/1/consents",
            json={"accepted": False, "purpose": "Retrait du consentement pour le test."},
            headers=self.auth(self.patient_token),
        )
        response = self.client.post("/api/consultations", json={"patient_id": 1}, headers=self.auth(self.doctor_token))
        self.assertEqual(response.status_code, 409)

    def test_patient_sees_the_invitation(self):
        with self.client.websocket_connect("/ws/events") as events:
            events.send_text(json.dumps({"type": "auth", "token": self.patient_token}))
            self.assertEqual(json.loads(events.receive_text())["type"], "auth-ok")
            consultation = self.start_consultation()
            invitation = json.loads(events.receive_text())
        self.assertEqual(invitation["type"], "invitation")
        self.assertEqual(invitation["consultation"]["room"], consultation["room"])
        active = self.client.get("/api/consultations/active", headers=self.auth(self.patient_token)).json()
        self.assertEqual(active["room"], consultation["room"])

    def test_signaling_relays_between_doctor_and_patient(self):
        room = self.start_consultation()["room"]
        doctor_socket, doctor = self.join_room(room, self.doctor_token)
        patient_socket, patient = self.join_room(room, self.patient_token)
        try:
            self.assertEqual(json.loads(doctor.receive_text())["type"], "auth-ok")
            self.assertEqual(json.loads(patient.receive_text())["type"], "auth-ok")
            doctor.send_text('{"type":"offer","sdp":{"type":"offer"}}')
            self.assertEqual(json.loads(patient.receive_text())["type"], "offer")
        finally:
            patient_socket.__exit__(None, None, None)
            doctor_socket.__exit__(None, None, None)

    def test_signaling_rejects_a_missing_token(self):
        room = self.start_consultation()["room"]
        with self.client.websocket_connect(f"/ws/signaling/{room}") as peer:
            peer.send_text(json.dumps({"type": "auth", "token": "invalid"}))
            self.assertEqual(json.loads(peer.receive_text())["type"], "auth-failed")
            with self.assertRaises(WebSocketDisconnect):
                peer.receive_text()

    def test_signaling_rejects_an_unknown_room(self):
        socket, peer = self.join_room("not-a-consultation", self.doctor_token)
        try:
            self.assertEqual(json.loads(peer.receive_text())["type"], "forbidden")
        finally:
            socket.__exit__(None, None, None)

    def test_signaling_room_rejects_a_third_peer(self):
        room = self.start_consultation()["room"]
        sockets = [self.join_room(room, self.doctor_token), self.join_room(room, self.patient_token)]
        try:
            for _, peer in sockets:
                peer.receive_text()
            third_socket, third = self.join_room(room, self.doctor_token)
            sockets.append((third_socket, third))
            self.assertEqual(json.loads(third.receive_text())["type"], "room-full")
        finally:
            for socket, _ in reversed(sockets):
                socket.__exit__(None, None, None)

    def test_signaling_notifies_remaining_peer_when_one_leaves(self):
        room = self.start_consultation()["room"]
        staying_socket, staying = self.join_room(room, self.doctor_token)
        leaving_socket, leaving = self.join_room(room, self.patient_token)
        try:
            staying.receive_text()
            leaving.receive_text()
            leaving_socket.__exit__(None, None, None)
            self.assertEqual(json.loads(staying.receive_text())["type"], "leave")
        finally:
            staying_socket.__exit__(None, None, None)

    def test_doctor_ending_the_consultation_closes_it(self):
        room = self.start_consultation()["room"]
        response = self.client.post(f"/api/consultations/{room}/end", headers=self.auth(self.doctor_token))
        self.assertEqual(response.json()["status"], "ended")
        self.assertIsNone(self.client.get("/api/consultations/active", headers=self.auth(self.patient_token)).json())

    def test_tests_do_not_touch_the_demo_database(self):
        self.assertNotEqual(Path(DATABASE_PATH).name, "telecare.db")


if __name__ == "__main__":
    unittest.main()
