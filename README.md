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

