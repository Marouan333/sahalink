# Progress - SahaLink

## Objective

Build and demonstrate a deliberately scoped teleconsultation prototype for the ENSAM mini-project. It supports a patient video consultation, remote vital-sign entry and history, threshold alerts, consent capture, and a doctor dashboard. Only simulated data is used.

## Work plan

- [x] Inspect the assignment PDF and team allocation material.
- [x] Initialize Git and commit the source assignment materials before development.
- [x] Define a responsive clinical web application visual system.
- [x] Build the FastAPI API, SQLite demonstration database, and WebSocket channels.
- [x] Build patient and doctor interfaces with responsive styling.
- [x] Implement simulated vital-sign data, threshold detection, alerts, and consent logging.
- [x] Implement minimal peer-to-peer video and signaling user interface.
- [x] Write architecture, data, security, test, and presentation documentation.
- [x] Execute automated and manual smoke tests.
- [x] Review the user interface at desktop and mobile sizes, then commit the completed prototype.

## Scope decisions

- The prototype uses SQLite by default so it runs locally without infrastructure. `DATABASE_URL` is reserved for a future PostgreSQL deployment.
- Data is synthetic and seeded locally. No real patient data or account credentials are used.
- Video is browser-to-browser WebRTC. The FastAPI WebSocket endpoint relays signaling messages only; media does not transit the application server.
- Authentication is a demonstrator role selector, not production identity verification. Production controls and limits are documented in `docs/security-and-compliance.md`.

## Validation criteria

- Patient can give consent, enter readings, see history, and request a consultation.
- Doctor can see the dashboard, new readings, and abnormal-value alerts.
- API rejects invalid vital-sign values and creates alerts when configured thresholds are crossed.
- An API health check and test script pass from a fresh local start.

## Completed verification

- API unit and integration checks: health endpoint, normal and abnormal vital entries, alert acknowledgement, validation rejection and WebSocket signaling relay.
- Browser smoke test: consent capture and simulated critical-value alert flow.
- Responsive review: patient screen reviewed at 375 px wide; doctor dashboard reviewed at desktop width.
- Browser console: no current JavaScript errors after the final reload.
- Background local server: running at `http://127.0.0.1:8000` after a clean restart with the normal simulated seed reading.

## Gap closure (2026-11-16)

A review against the assignment PDF found five gaps, now closed:

- [x] Cited the WHO Global Observatory for eHealth report explicitly, with its application to the project's scope, in `docs/security-and-compliance.md`.
- [x] Added a BPMN-style patient/doctor pathway diagram with swimlanes and the degraded-case branch: `docs/bpmn-parcours-patient.md`.
- [x] Consolidated a single technical report (`docs/rapport-technique.md`) covering context, modeling, prototype, results, discussion/limits, and security/compliance.
- [x] Replaced qualitative-only validation claims with measured numbers (latency, detection rate, rejection rate) from a reproducible benchmark script: `scripts/benchmark.py`, results folded into `docs/validation.md`.
- [x] Committed the working tree to git (previously only the initial assignment-materials commit existed).

