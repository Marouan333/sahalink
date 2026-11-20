# SahaLink - Teleconsultation et suivi a distance

Prototype demonstrable for the ENSAM course *Sante digitale et ingenierie des systemes de sante*.

## Features

- Login with role-based access: the doctor and the patient each see only their own workspace, and the API enforces the same rules
- Consent capture with a timestamp and explicit purpose; a teleconsultation cannot start without it
- Doctor-initiated teleconsultation: the patient receives a live invitation and joins with one click
- Entry and longitudinal display of simulated vital signs
- Configurable clinical alert rules for blood pressure, heart rate, oxygen saturation, and temperature
- Real-time alert delivery with WebSockets
- WebRTC video room and signaling endpoint for a two-browser demo
- French clinical interface designed for desktop and mobile

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000>. The API documentation is available at <http://127.0.0.1:8000/docs>.

## Demo accounts

Both accounts are fictitious and seeded automatically on first start. The login page has a "Utiliser" shortcut for each.

| Role | Username | Password |
|---|---|---|
| Doctor | `dr.benali` | `Demo-2026!` |
| Patient | `amal` | `Demo-2026!` |

## Testing the full workflow

Each browser tab keeps its own session, so the doctor and the patient can be logged in side by side in two tabs or windows of the same browser. The video call needs a real camera and microphone, so run it in a normal browser rather than an automated or sandboxed one.

1. Start the server (see Quick start above) and keep it running.
2. Window 1: open <http://127.0.0.1:8000> and log in as the patient (`amal`).
3. Window 2: open the same address and log in as the doctor (`dr.benali`).
4. Doctor: click "Demarrer une consultation". It is refused with "Le patient n'a pas encore donne son consentement" because the patient has not consented yet.
5. Patient: in "Mon suivi", tick the consent box and click "Enregistrer mon accord". The doctor's dashboard now shows the consent as "Confirme".
6. Patient: send a normal reading, then click "Simuler une alerte" and send the critical reading. The doctor receives the alert live (toast, bell counter, alert card) and acknowledges it.
7. Doctor: click "Demarrer une consultation" and allow the camera. The patient's window immediately shows "Dr. Benali vous invite en teleconsultation".
8. Patient: click "Rejoindre" and allow the camera. Within a few seconds each window shows the other participant full-size and its own image in the corner, with the status "Consultation connectee".
9. Try the controls: mute the microphone, turn the camera off (the other side is told), or switch camera from the list.
10. Doctor: click "Terminer". The patient is told "Le medecin a termine la consultation" and both cameras turn off.

Camera selection: phone-as-webcam drivers such as Camo, Iriun, DroidCam or OBS register as extra cameras and show a black frame or a logo when their phone app is not connected. The app therefore ranks physical webcams first, checks each candidate for a real (non-black) image before using it, and remembers the camera that worked. The "Camera" list in the consultation panel marks virtual cameras and switches camera live during a call. If one side sees a black image, the status line says whether the problem is the local camera or the other participant's.

`localhost` and `127.0.0.1` are treated as secure origins by every major browser, so no extra flags or HTTPS setup are needed for this local test. The automated tests in `tests/test_api.py` cover login, permissions, consent, invitations and the authenticated signaling relay; the live camera and microphone capture remains a manual test, as documented in `docs/validation.md`.

## Deployment

The app needs a long-running server (WebSockets carry alerts, invitations and call signaling), so it suits Railway, Render or a VM rather than serverless platforms. The `Procfile` starts it with `uvicorn` on `$PORT` behind the host's HTTPS proxy. HTTPS is required for camera access on any address other than `localhost`.

- Data lives in SQLite (`telecare.db`) and is re-seeded with the two demo accounts on start. On hosts with an ephemeral disk the data resets on every redeploy, which suits a demonstration.
- Video calls use public STUN servers by default. Participants behind strict NATs (some mobile networks) may need a TURN relay: set the `ICE_SERVERS` environment variable to a JSON list, for example `[{"urls":"turn:turn.example.org:3478","username":"user","credential":"secret"}]`.
- For a quick test from this PC, expose the local server with `cloudflared tunnel --url http://127.0.0.1:8000`, which prints a temporary public HTTPS address.

## Test

```powershell
python -m unittest discover -s tests -v
```

To check a running server (local or public) end to end, including login, permissions, consent, live alerts, invitation and call signaling:

```powershell
python scripts/smoke_test.py http://127.0.0.1:8000
```

The smoke test adds data to that server (a consent, readings, an alert, a consultation), so restart from a clean database before a demonstration (stop the server, delete `telecare.db`, start it again).

## Project documentation

- `docs/rapport-technique.md` (consolidated technical report)
- `docs/architecture.md`
- `docs/bpmn-parcours-patient.md` (BPMN patient/doctor pathway, including the degraded case)
- `docs/data-simulation.md`
- `docs/security-and-compliance.md`
- `docs/validation.md` (test protocol and measured results)
- `docs/test-utilisabilite.md` (SUS usability protocol, to run with testers; scores computed by `scripts/sus_score.py`)
- `PRESENTATION.md` (slide plan, demo script, likely questions)

Measured results (latency, detection rate) can be reproduced with:

```powershell
python scripts/benchmark.py
```

