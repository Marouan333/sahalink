"""Teste le parcours complet medecin-patient contre un serveur SahaLink en marche.

Usage: python scripts/smoke_test.py https://adresse-publique-ou-http://127.0.0.1:8000

Attention : le test ajoute un consentement, des mesures, une alerte et une consultation
aux donnees du serveur teste. Relancer avec une base propre avant une demonstration.
Il ne verifie pas la camera : la capture video reste un test manuel.
"""
import asyncio
import json
import secrets
import sys
import urllib.error
import urllib.request

import websockets

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else sys.exit(__doc__)
WS_BASE = BASE.replace("https://", "wss://").replace("http://", "ws://")
PASSWORD = "Demo-2026!"
NORMAL = {"systolic": 122, "diastolic": 76, "heart_rate": 68, "spo2": 98, "temperature": 36.6}
CRITICAL = {"systolic": 188, "diastolic": 122, "heart_rate": 138, "spo2": 89, "temperature": 39.2}
failures = []


def check(label, ok, detail=""):
    print(f"[{'OK' if ok else 'ECHEC'}] {label}{(' : ' + str(detail)) if detail and not ok else ''}")
    if not ok:
        failures.append(label)


def call(method, path, payload=None, token=None):
    headers = {"Content-Type": "application/json", "User-Agent": "sahalink-smoke-test"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read() or b"null")
    except urllib.error.HTTPError as error:
        return error.code, None


async def authenticated_socket(path, token):
    socket = await websockets.connect(WS_BASE + path, origin=BASE, open_timeout=30)
    await socket.send(json.dumps({"type": "auth", "token": token}))
    first = json.loads(await asyncio.wait_for(socket.recv(), 15))
    return socket, first["type"]


async def next_event(socket, wanted, timeout=15):
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        message = json.loads(await asyncio.wait_for(socket.recv(), max(0.1, deadline - asyncio.get_event_loop().time())))
        if message["type"] == wanted:
            return message


async def main():
    status, page = None, None
    try:
        with urllib.request.urlopen(BASE + "/", timeout=30) as response:
            status, page = response.status, response.read()
    except Exception as error:
        sys.exit(f"Serveur injoignable : {error}")
    check("La page d'accueil affiche le formulaire de connexion", status == 200 and b"login-form" in page)
    check("Sante du service", call("GET", "/api/health")[0] == 200)

    check("Mauvais mot de passe refuse", call("POST", "/api/auth/login", {"username": "dr.benali", "password": "x"})[0] == 401)
    check("Routes de sante fermees sans session", call("GET", "/api/alerts")[0] == 401)
    doctor = call("POST", "/api/auth/login", {"username": "dr.benali", "password": PASSWORD})[1]["token"]
    patient = call("POST", "/api/auth/login", {"username": "amal", "password": PASSWORD})[1]["token"]
    check("Le patient ne peut pas lire les alertes", call("GET", "/api/alerts", token=patient)[0] == 403)
    check("Le patient ne peut pas lire un autre dossier", call("GET", "/api/patients/2/vitals", token=patient)[0] == 403)
    check("Le medecin ne peut pas donner le consentement", call("POST", "/api/patients/1/consents", {"accepted": True, "purpose": "Tentative du medecin"}, doctor)[0] == 403)

    doctor_events, doctor_state = await authenticated_socket("/ws/events", doctor)
    patient_events, patient_state = await authenticated_socket("/ws/events", patient)
    check("Canaux d'evenements authentifies", doctor_state == patient_state == "auth-ok")
    try:
        await websockets.connect(WS_BASE + "/ws/events", origin="https://evil.example.com", open_timeout=15)
        check("Origine etrangere refusee sur les WebSockets", False)
    except Exception:
        check("Origine etrangere refusee sur les WebSockets", True)

    call("POST", "/api/patients/1/consents", {"accepted": False, "purpose": "Retrait du consentement pour le test"}, patient)
    withdrawn_event = await next_event(doctor_events, "consent")
    check("Le medecin voit le retrait du consentement en direct", withdrawn_event["accepted"] is False)
    check("Demarrage refuse sans consentement (409)", call("POST", "/api/consultations", {"patient_id": 1}, doctor)[0] == 409)
    call("POST", "/api/patients/1/consents", {"accepted": True, "purpose": "Teleconsultation pedagogique et suivi des constantes simulees."}, patient)
    consent_event = await next_event(doctor_events, "consent")
    check("Le medecin voit le consentement en direct", consent_event["accepted"] is True)

    call("POST", "/api/patients/1/vitals", {**NORMAL, "source": "manual"}, patient)
    check("Le medecin voit la mesure normale en direct", (await next_event(doctor_events, "vital"))["type"] == "vital")
    check("Valeur impossible rejetee (422)", call("POST", "/api/patients/1/vitals", {**NORMAL, "systolic": 500}, patient)[0] == 422)
    created = call("POST", "/api/patients/1/vitals", {**CRITICAL, "source": "manual"}, patient)[1]
    alert_event = await next_event(doctor_events, "alert")
    check("Alerte critique recue par le medecin en direct", alert_event["alert"]["severity"] == "critical")
    check("Le medecin acquitte l'alerte", call("PATCH", f"/api/alerts/{created['alert']['id']}/acknowledge", token=doctor)[0] == 200)

    consultation = call("POST", "/api/consultations", {"patient_id": 1}, doctor)[1]
    invitation = await next_event(patient_events, "invitation")
    check("Le patient recoit l'invitation en direct", invitation["consultation"]["room"] == consultation["room"])
    room = consultation["room"]

    doctor_room, doctor_room_state = await authenticated_socket(f"/ws/signaling/{room}", doctor)
    patient_room, patient_room_state = await authenticated_socket(f"/ws/signaling/{room}", patient)
    check("Les deux participants entrent dans la salle", doctor_room_state == patient_room_state == "auth-ok")
    await doctor_room.send(json.dumps({"type": "offer", "sdp": "test"}))
    check("La signalisation est relayee du medecin au patient", (await next_event(patient_room, "offer"))["sdp"] == "test")
    third, third_state = await authenticated_socket(f"/ws/signaling/{room}", doctor)
    check("Un troisieme participant est refuse", third_state == "room-full")
    stranger_token = call("POST", "/api/auth/login", {"username": "amal", "password": PASSWORD})[1]["token"]
    call("POST", "/api/auth/logout", {}, stranger_token)
    revoked, revoked_state = await authenticated_socket(f"/ws/signaling/{room}", stranger_token)
    check("Un jeton revoque est refuse", revoked_state == "auth-failed")

    check("Le medecin termine la consultation", call("POST", f"/api/consultations/{room}/end", token=doctor)[0] == 200)
    ended = await next_event(patient_events, "consultation-ended")
    check("Le patient est prevenu de la fin", ended["room"] == room)
    check("Plus aucune consultation active", call("GET", "/api/consultations/active", token=patient)[1] is None)

    # Registration and a second patient (leaves one small test account in the database).
    suffix = secrets.token_hex(3)
    form = {"username": f"smoke.{suffix}", "display_name": f"Smoke Test {suffix.upper()}", "password": "Smoke-2026!", "birth_year": 1990, "care_plan": "Test automatique"}
    check("Inscription avec role medecin ignore", call("POST", "/api/auth/register", {**form, "username": f"x.{suffix}", "role": "doctor"})[1]["user"]["role"] == "patient")
    status, registered = call("POST", "/api/auth/register", form)
    check("Inscription patient (201)", status == 201 and registered["user"]["role"] == "patient")
    check("Identifiant deja pris refuse (409)", call("POST", "/api/auth/register", form)[0] == 409)
    check("Nom avec balisage refuse (422)", call("POST", "/api/auth/register", {**form, "username": f"y.{suffix}", "display_name": "<script>x</script>"})[0] == 422)
    new_token, new_id = registered["token"], registered["user"]["patient_id"]
    check("Le patient ne peut pas lister les patients", call("GET", "/api/patients", token=new_token)[0] == 403)
    listed = call("GET", "/api/patients", token=doctor)[1]
    check("Le medecin voit le nouveau patient dans la liste", any(item["id"] == new_id for item in listed))
    check("Tableau de bord d'un patient precis", call("GET", f"/api/dashboard?patient_id={new_id}", token=doctor)[1]["patient"]["id"] == new_id)
    check("Demarrage refuse pour le nouveau patient sans consentement (409)", call("POST", "/api/consultations", {"patient_id": new_id}, doctor)[0] == 409)
    call("POST", f"/api/patients/{new_id}/consents", {"accepted": True, "purpose": "Test automatique"}, new_token)
    new_events, new_state = await authenticated_socket("/ws/events", new_token)
    second = call("POST", "/api/consultations", {"patient_id": new_id}, doctor)[1]
    check("Le nouveau patient recoit l'invitation", (await next_event(new_events, "invitation"))["consultation"]["room"] == second["room"])
    check("Le medecin termine la consultation du nouveau patient", call("POST", f"/api/consultations/{second['room']}/end", token=doctor)[0] == 200)
    await new_events.close()
    call("POST", "/api/auth/logout", {}, new_token)

    for socket in (doctor_events, patient_events, doctor_room, patient_room, third, revoked):
        await socket.close()
    for token in (doctor, patient):
        call("POST", "/api/auth/logout", {}, token)

    print(f"\n{'Tout est OK.' if not failures else str(len(failures)) + ' verification(s) en echec : ' + '; '.join(failures)}")
    sys.exit(1 if failures else 0)


asyncio.run(main())
