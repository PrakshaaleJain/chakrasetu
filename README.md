# ChakraSetu

A local, persistent battery circularity coordination application built with React, TypeScript, Vite, Leaflet/OpenStreetMap, FastAPI, Pydantic, SQLAlchemy and SQLite. All demo participants, verification states, prices, quotes, capacities, evidence and telemetry are synthetic.

## Start the application

Tested with Python 3.12 and Node 24. Use Node 20.19+ and Python 3.12+. Run from the extracted `chakrasetu` directory.

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell instead:
# .\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
npm --prefix frontend ci
cd backend
python -m app.seed
cd ..
python dev.py
```

Open **http://127.0.0.1:5173**. API docs are **http://127.0.0.1:8000/docs**, health is **http://127.0.0.1:8000/health**. If ports are already in use, stop the conflicting service first. The Vite dev proxy sends `/api` requests to the backend; open the app through Vite, not by opening `index.html` from disk.

Alternatively, run these in two terminals with the virtual environment activated:

```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```bash
cd frontend
npm run dev
```

Use the demo actor selector to switch among originators, buyers, transporters, hub, specialist and reviewer. Roles and resource relationships are enforced by the API. Demo bearer tokens are deliberately exposed through `/demo/users` in local demo mode; **this is not production authentication**. Do not publicly expose this demo backend. `DEMO_MODE=false` disables demo discovery and seeded actor authentication; production identity provisioning is outside this MVP.

## Seed, reset and demonstrate

The seed command is idempotent. Data survives restarts in `backend/chakrasetu.db`. Uploaded files are stored under `backend/uploads`. Dates are generated relative to reset time so the demo stays reproducible.

The following command explicitly deletes the demo database contents and rebuilds synthetic fixtures:

```bash
cd backend
python -m app.seed --reset
```

To exercise the real running HTTP backend (not a mock), with `dev.py` running in another terminal:

```bash
cd backend
python demo.py
```

The script creates a fresh battery, demonstrates missing authority evidence, reviews evidence, selects and confirms an offer, generates direct/one-hub routes, rejects a quote above cap, accepts another quote, reserves/books, confirms pickup as both parties, emits a labelled synthetic alert, disputes and reconciles receipt, records inspection/settlement/disposition, and closes. It checks each response and exits on failure. Running it changes the local synthetic demo database; it does not transfer money or contact anyone.

For a self-contained real-server check that starts/stops both servers, run `python integration_smoke.py` from the project root (with ports 8000/5173 free). It performs the same rehearsal and persists synthetic results.

For the interactive rehearsal, follow [docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md).

## Tests and build

```bash
cd backend
python -m pytest -q
cd ../frontend
npm run typecheck
npm run build
```

The API suite uses isolated databases. It includes a file-backed, two-thread SQLite reservation race and expiry test; persisted data is reread after closing/reopening the engine. No test resets the running demonstration database. A Starlette/httpx deprecation warning is currently emitted by the test client; it does not affect passing results. Actual results and remaining limitations are in [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md).

## What is implemented

- Persistent intake, eleven YES/NO/UNKNOWN incident flags, unknown mass/chemistry, declaration, transfer authority, reviewed/versioned evidence, controlled draft edits and provenance.
- Synthetic organisation/facility/capability/transporter registries. Identity, facility registration, verified capability and available capacity are distinct; scoped verification decisions are audited.
- Safety/review holds and owned exception queues. Qualified reports retain original flags and constrain movement to matching controlled-handling participants. No DIY handling instructions or safety certification.
- Listings, explained eligible/excluded buyers, conditional offers, seller selection, immutable terms history and mutual version confirmation. Cap changes, inspection-price revisions and pickup-window changes create new versions.
- Deterministic direct/one-hub routes, ordered legs, source/completeness of estimates, scope snapshots, weights/components and rejected candidates. Maps have textual alternatives.
- Explicit transporter responses, distinguishing decline/silence, quote validity/scope, payer acceptance, budget enforcement, recoverable quote-round exceptions, requoting and cancellation proposals.
- SQLite `BEGIN IMMEDIATE` capacity reservation/booking, expiry, release, per-asset allocation checks and idempotency records.
- Explicit shipment transitions, two-party physical pickup and hub handovers, custody history, partial quantity custody segments, disputed receipt and authorised reconciliation.
- Compatible consolidation manifests for individually agreed/quoted/booked one-hub asset shipments. All affected sellers, receivers, hub and carrier approve before pickup. Per-asset capacity/custody/receipt stays intact; no unapproved cost change or invented saving.
- Synthetic threshold alerts and holds on reported incidents; reviewer next actions. Alerts do not prove damage.
- Receiving inspection, conditional price revisions, record-only payment reported/payee-confirmed settlement, distinct disposition outcomes and closure gates.

## Estimate, safety and commercial boundaries

Routes use Haversine distance multiplied by 1.3 and travel time at 30 km/h, plus configured hub dwell. These are **proxies**, not verified road distance or real ETAs. Rate cards are configured **synthetic estimates**; only an explicitly submitted, current, all-inclusive quote accepted by the named payer can support booking. Missing cost/mass is never zero. A hub quote covers both legs with the same named carrier; inbound and outbound custody are still separate.

A scoped qualified report is not a declaration that the battery is safe. Reports have scope, conditions, reviewer, qualification evidence and expiry. Ordinary participants remain excluded. If no suitable specialist matches, the case stays held for manual outreach. A new transit/inspection safety incident invalidates previous clearance; controlled redirection of an already moving shipment remains a manual exception decision, rather than an automatic reroute.

Settlement is a ledger of declarations and confirmations, **not proof that ChakraSetu moved money**. Receipt is not processing completion. `SENT_FOR_RECYCLING` cannot close a shipment as recycled. Closure requires complete physical receipt, inspection acceptance, current mutual terms, payee-confirmed settlement, final evidenced disposition and no linked open exception.

## Configuration and schema

Environment variables: `DATABASE_URL`, `UPLOAD_DIR`, `DEMO_MODE`, `TELEMETRY_THRESHOLDS`, `CAPACITY_HOLD_MINUTES`. See `.env.example`. Default CORS is limited to localhost Vite development origins. All timestamps are UTC; the UI displays IST. Money is integer paise in INR. Capacity uses total mass per asset record, not mass per item.

`schema_version` records version 1. Bootstrap creates missing tables and refuses unknown schema versions. Future field changes need an explicit migration or a deliberate demo reset; `create_all` does not migrate existing columns. SQLite serialises writes for this single-instance demo; multi-instance deployment needs stronger reservation locking, real identity, document governance and operational review.

## Project layout

```text
backend/app/          ORM, schemas, auth, API routers
backend/app/services/ deterministic screening, commercial, routing, logistics and custody rules
backend/tests/        API/domain regression and concurrency tests
backend/demo.py       real-HTTP rehearsal
frontend/src/         typed client, role-aware pages, forms, maps and timelines
docs/                 source specification and demonstration guide
IMPLEMENTATION_STATUS.md verified results, decisions and gaps
```

See the status file for precise exclusions. Browser rendering has not been visually verified in this environment; frontend type checks/build and real HTTP integration are separate verified checks.
