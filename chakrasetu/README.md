# ChakraSetu

A persistent battery circularity coordination application: React/TypeScript/Vite/Leaflet, FastAPI/Pydantic and SQLite/SQLAlchemy. It includes organisation accounts with combined approved roles, the original intake/commercial/logistics workflow and linked assessment, transformation, second-life and recovered-material workflows. Demo organisations, qualifications, capacities and telemetry are fictional. Their provenance is retained internally; the interface distinguishes example scopes, requested scopes, reviewed scopes, estimated costs and recorded quotes.

## Install and run locally

Use Python 3.12+ and Node 20.19+. Open a terminal in the extracted `chakrasetu` folder:

```bash
python -m venv .venv
```

Activate the environment. Linux/macOS:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Then install, initialize and explicitly provision local demo accounts:

```bash
python -m pip install -r backend/requirements.txt
npm --prefix frontend ci
cd backend
python -m app.seed
python -m app.auth_bootstrap --demo
cd ..
python dev.py
```

The root URL opens the public homepage and interactive pathway explorer. Use **Sign in** to open the operational workspace. The demo bootstrap prompts for **your chosen password of at least 12 characters**. It creates no public default password. Open **http://127.0.0.1:5173**, sign in as `originator@demo.chakrasetu.local` with the password you supplied. To use another fictional participant, sign out and sign in to that account; each organisation account can use its approved roles together, without a role selector. Historic individual accounts remain compatible for the existing rehearsals. `buyer` can use refurbishment and diagnostic workflows from the same login. Refresh retains your session and persisted records.

Demo account email prefixes: `originator`, `originator2`, `buyer`, `technician`, `secondlife`, `customer`, `recycler`, `processor`, `refiner`, `manufacturer`, `transporter`, `transporter2`, `hub`, `specialist`, `specialtrans`, `reviewer`. All end with `@demo.chakrasetu.local`. `reviewer` has operational review scope, **not platform account-administrator powers**.

API docs: **http://127.0.0.1:8000/docs**. Health: **http://127.0.0.1:8000/health**. The frontend proxies `/api` to FastAPI. Do not open `index.html` directly. If either port is busy, stop its conflicting process before starting. `Ctrl+C` stops both development servers.

Two-terminal alternative (with environment activated):

```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```bash
cd frontend
npm run dev
```

## Real accounts and first administrator

Run the one-time bootstrap locally in `backend`:

```bash
python -m app.auth_bootstrap --admin
```

Supply your own administrator email and password when prompted. A second first-admin bootstrap is refused. Sign in with these credentials. **Account & access** lets the platform administrator activate registered accounts, revoke access, issue recovery tokens and manage membership in the selected organization. The platform-reviewed membership form assigns a person to an organization after recording identity and consent review evidence. Organization administrators can change existing local memberships, but cannot grant platform administration or network-review authority. Initial membership is platform-mediated after identity and consent review; invitation automation is not implemented.

Registration creates a pending account and unverified organization. It does not grant network verification or operational review privileges. Activation is a separate administrator action. After activation, the person can use their assigned `ORIGINATOR` role. Facility/operation qualification remains a separate evidence review.

Password recovery has **no email service**: request recovery in the login screen, contact the administrator, then use the privately delivered 30-minute one-use token. The administrator issues it from Account & access after verifying the account holder. Tokens are shown once, stored hashed, never put in audit logs, and a reset revokes all sessions. Password change also revokes all sessions.

See [docs/SECURITY.md](docs/SECURITY.md) for the permission matrix and deployment boundaries.

## Workflows

The existing pages cover screening, private evidence, listings/offers, mutually confirmed versioned terms, direct/one-hub planning, transporter quotes, cap enforcement, reservation/booking, two-party custody, exceptions, receiving inspection, settlement and disposition.

**Circular supply chain** adds:

- **Pathways:** qualified multi-stage second-life and material-recovery candidates, excluded stages, evidence snapshots, conditions, explicit whole-pathway economic inputs and cost per battery. Missing inputs stay unknown. Recommendations do not reserve capacity or prove execution.
- **Assessments:** assignment, technician measurements including null values, procedure/equipment references, scoped outcomes and limitations, independent documentary review and linked immutable revisions. An accepted report does not clear a safety incident.
- **Operations:** link an existing physically held battery, select multiple inputs, create a job, collect every owner's explicit approval of operation/output-title terms, allocate atomically, report multiple measured outputs and documented process loss, then independently review acceptance. No ordinary processing of held batteries.
- **Products & materials:** separate identifiers/specifications, genealogy with blended-input labels, acceptance, customer deployment, service, retirement, incident holds and two-party take-back terms. Deployment requires recorded receipt by the verified customer.
- **Downstream handoffs:** qualified offtake/product-sale terms, current version confirmation by both parties, carrier-submitted quotes, named payer/cap, capacity checks, two-party physical pickup, arrival/receipt, discrepancies, record-only settlement and closure. Downstream shipments use direct routes; battery routes retain direct/one-hub support.
- **My Organisation:** profile, safe logo uploads, facilities, role/capability requests, review status and account security. Scoped requests do not require documents at submission; approval of technical/identity scopes requires an authorised review reference and expiry. Advanced downstream product/material scope review is available here only to reviewers.

A transformation consumes whole linked inputs. Split outputs and blended inputs are supported. Partial lot consumption and added non-battery integration components are not modelled; added mass must not be invented to reconcile a job. Recorded outputs plus documented loss must equal recorded input mass within 1 gram. This is an accounting check, not proof of composition or measurement accuracy.

## Tests and repeatable demonstration

```bash
cd backend
python -m pytest -q
cd ../frontend
npm run typecheck
npm test
npm run build
cd ..
python integration_smoke.py
```

The last command starts real FastAPI and Vite servers, verifies module serving/proxy access and uses real cookie logins through a full circular HTTP workflow: intake → first shipment → assessment → refurbishment → second-life integration → customer deployment/service/retirement → recycling → refining → manufacturing. It checks five processing links back to the original battery, then verifies organisation profile persistence, private-contact isolation, a one-card directory and capability requests from pending through additional information to approval. It uses a temporary isolated database, temporary uploads and an ephemeral random password, then stops its servers. It does not alter your working database, send messages or transfer money. It checks HTTP integration; it does **not** run browser visual or interaction tests.

For an existing locally provisioned demo server:

```bash
cd backend
python demo.py
```

This prompts for your chosen demo password and exercises the original workflow. For the complete circular rehearsal, explicitly export `CHAKRA_DEMO_PASSWORD` to your chosen demo password in your local shell, then run `python circular_demo.py`. Never commit this value. These manual rehearsals create synthetic records in the running demo database.

## Persistence and migration

`backend/chakrasetu.db` stores records across restarts; `backend/uploads` stores evidence and re-encoded organisation logos. Back up both together while the app is stopped. Startup migrates v1/v2/v3 to v4 by adding normalized tables and a unique organisation-account binding; it preserves original columns/records. Old bearer tokens are never accepted, including after migration. Provision accounts explicitly. Migration is idempotent and rejects unknown schema versions.

`python -m app.seed` initializes fictional network data idempotently. Existing dates are retained rather than silently refreshed. To explicitly delete all records/accounts and rebuild seed data:

```bash
cd backend
python -m app.seed --reset
python -m app.auth_bootstrap --demo
```

Do not reset a database whose records you want to retain. A reset also removes the administrator account; bootstrap it again only if intended.

## Configuration and boundaries

See `.env.example`; variables must be exported because `.env` files are not auto-loaded. Development origins are restricted to the configured loopback Vite origins. Local development uses HTTP cookies on loopback. For any public environment, use `APP_ENV=production`, HTTPS, explicit `ALLOWED_ORIGINS`, private database/upload storage and an appropriate serving/reverse-proxy setup. Secure cookies and rejection of fictional accounts are enabled in production mode. This repository supplies a local launcher, not a production hosting configuration or deployment certification.

Passwords use Argon2id, sessions expire after eight hours, logout/deactivation/membership changes revoke access, mutations require session-bound CSRF tokens, and authentication endpoints have persistent per-address and per-address/email limits. Database sessions store token hashes. See SECURITY.md for operational scope and limitations.

Money is integer paise in INR; settlement records declarations and confirmations and moves no money. Route distance is Haversine × 1.3 and travel time is a configured proxy, not verified road distance/live ETA. Original rate cards and all default network capacities are synthetic. Full-pathway economics accept explicitly labelled owner estimates or synthetic inputs, not invented market prices or claimed complete-chain quotations. Actual handoff quotes are submitted by authenticated carriers and retain their history.

No safety certification, battery diagnosis from software, live hardware, external permit checks, paid APIs or banking integrations are included. Browser visual QA remains unverified in this environment. Detailed verified checks, decisions and remaining requirements are in [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md).


## Organisation profiles and capability review

Open **My Organisation** to edit ordinary profile information, choose business-contact visibility, upload a PNG/JPEG/WebP logo, add a facility or submit a role/capability request. Logos are limited to 2 MB and 16 million input pixels, re-encoded as a metadata-free PNG of at most 512 pixels per side, and stored using generated filenames. Official-name changes go through an identity-review request; descriptive edits save directly. Passwords and sessions never appear in directory/profile responses.

One new registration creates one organisation and one canonical account binding. Normalised duplicate official names are rejected with an account-recovery instruction. Legacy accounts, memberships and historical transaction links are preserved; they are not destructively merged. Migration binds an existing primary account deterministically. Organisation administrators cannot expand their own operational roles through the legacy membership API: submit a request instead. A capability approval can grant its corresponding operational role to the primary organisation account, while the facility qualification, safety, resource ownership and capacity checks remain separate gates.

In **Participant Network**, search organisations by name, type, region/facility or approved capability. Each organisation appears once. Open its profile and use **Show contact details** to request permitted business contacts from the server. Private contacts remain restricted to the owner and explicitly scoped reviewers. Public business contacts still require sign-in in this version; anonymous directory browsing is not implemented. No contact values are prefetched into the cards or legacy network endpoint.

Reviewer accounts open **My Organisation → Capability Review Queue** to request more information, approve/reject, suspend or record requested removal. The organisation can respond in the same request or withdraw an open request. Decisions and approved scopes retain audit/history records. The stated 48-hour response is a demonstration service target, with no automatic approval or email delivery.

For persistent logos after redeployment, configure `UPLOAD_DIR` to a durable directory/volume and `DATABASE_URL` to the persistent database path. Back up both while stopped. Example Linux shell settings (replace the paths with your actual durable paths):

```bash
export UPLOAD_DIR=/srv/chakrasetu/uploads
export DATABASE_URL=sqlite:////srv/chakrasetu/chakrasetu.db
```

Windows PowerShell uses `$env:UPLOAD_DIR="C:/ChakraSetuData/uploads"` and `$env:DATABASE_URL="sqlite:///C:/ChakraSetuData/chakrasetu.db"`. The `.env.example` file is a reference; it is not loaded automatically. Old replaced/removed logo files are retained as inaccessible orphans for safe recovery; operational file-retention cleanup is not automated.

`npm --prefix frontend test` runs DOM interaction tests for combined-role navigation, route guards, contact reveal/conceal and readable status labels. These checks do not measure real browser layout. In this environment the cloud browser could not reach localhost, and the Chromium download returned an invalid archive; browser visual/interaction QA remains unverified. Follow [docs/ORGANISATION_GUIDE.md](docs/ORGANISATION_GUIDE.md) in your local browser before a live presentation.


## Registration redesign (schema v5)

Battery Registry now supports private drafts, a lightweight registration form, optional measured/reported diagnostics, five PBS cards, optional generic documents, operator approval and separate specialist review. Unknown technical values remain unknown. Approved technical discovery precedes transaction-specific transfer authority; L4/L5 safeguards and current activity qualifications remain enforced. See [the registration guide](docs/REGISTRATION_GUIDE.md) for the complete user/reviewer sequence, limits, policy configuration and legacy migration behavior.

My Organisation provides activity-specific acceptance declarations and reviewed scope requests. Narrowed availability cannot widen prior qualification. Pending plans expire when a scope changes and booking rechecks live permissions/capacity. Existing custody, terms, offers, receiving and circular transformations remain integrated.

New server dependency: `pypdf` parses PDF attachments. Re-run `python -m pip install -r backend/requirements.txt` when upgrading. Startup performs the additive v4 migration automatically; back up the database and uploads together first. The migration does not reset registrations, transactions or history.

## Public homepage and pathway decisions

The homepage now includes a large interactive supply-chain flowchart and a non-persistent scenario explorer driven by the same backend rules as operational battery decisions. Battery Registry and Processing & Downstream → Pathways show current evidence, safety/technical gates, qualified chains, comparable financial calculations and append-only decision history.

See [docs/HOMEPAGE_AND_DECISIONS.md](docs/HOMEPAGE_AND_DECISIONS.md) for the presentation walkthrough, financial-input contracts, configuration, API permissions, migration and remaining limits. Configure optional `DECISION_POLICY_PATH` for versioned SoH screening bands; public scenario assumptions are isolated in `backend/app/explorer_assumptions.json`. Restart after configuration changes.
