# SahaLink - Teleconsultation et suivi a distance

Prototype demonstrable for the ENSAM course *Sante digitale et ingenierie des systemes de sante*.

## Features

- Patient and doctor workspaces in one local demonstration interface
- Consent capture with a timestamp and explicit purpose
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

## Demonstration scenario

1. In the patient area, read and accept consent.
2. Add a normal reading, then a critical reading such as SpO2 89%.
3. Switch to the doctor area to see the alert and updated clinical history.
4. Open a second browser window, choose the same video room, and start/join the WebRTC consultation.

## Testing the video call

The WebRTC video room needs a real browser with camera and microphone access, so it cannot be exercised inside an automated or sandboxed tool. To test it yourself:

1. Start the server (see Quick start above) and keep it running.
2. Open two separate browser windows pointed at <http://127.0.0.1:8000> (two different browser profiles, or a normal window plus a private/incognito window, avoids any camera-sharing conflicts between tabs).
3. In window 1: open "Teleconsultation", keep the default room code (`amal-suivi`), click "Activer camera et rejoindre", and allow camera/microphone access when prompted.
4. In window 2: repeat with the same room code.
5. Expected result: each window shows its own small self-preview, and within a couple of seconds the other window's video fills the main frame with the status switching to "Consultation connectee."
6. Test the controls: mute the microphone in one window (the button dims and turns red), toggle the camera off, then click "Terminer" in both windows and confirm the video stops and the status resets to "Consultation terminee."

`localhost` and `127.0.0.1` are treated as secure origins by every major browser, so no extra flags or HTTPS setup are needed for this local test. Only the signaling relay (not the live camera/microphone capture) is covered by the automated test in `tests/test_api.py`; the video call itself is a manual test, as documented in `docs/validation.md`.

## Test

```powershell
python -m unittest discover -s tests -v
```

## Project documentation

- `docs/rapport-technique.md` (consolidated technical report)
- `docs/architecture.md`
- `docs/bpmn-parcours-patient.md` (BPMN patient/doctor pathway, including the degraded case)
- `docs/data-simulation.md`
- `docs/security-and-compliance.md`
- `docs/validation.md` (test protocol and measured results)
- `PRESENTATION.md`

Measured results (latency, detection rate) can be reproduced with:

```powershell
python scripts/benchmark.py
```

