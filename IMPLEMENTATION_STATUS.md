# ChakraSetu implementation status

Current phase: **K — integration verified; source handoff prepared**.

The persistent core demonstration is implemented and passes the checks below. This is a local synthetic hackathon MVP, not a deployed or production-certified system.

## Completed modules and phase checks

| Phase | Modules / result | Checks actually run |
|---|---|---|
| A | FastAPI, configuration, DB, ORM, controlled enums, Pydantic schemas, auth helpers, Vite/React/TS foundation | Foundation health test: 1 passed. Initial pytest import-path failure fixed. |
| B | `seed.py`, `registry_api.py`; organisations/users, identity, facilities, scoped capabilities, transporters and schema version | Seed/reset succeeded; foundation + registry: 2 passed. Final network: 11 synthetic organisations, 11 actors, 8 facilities, 3 carriers, ordinary/unknown/held batteries; closed, expired and exhausted-capacity fixtures. |
| C | `intake_api.py`, `services/intake.py`; drafts, explicit unknowns, flags, provenance, private/versioned evidence, reviewed authority and tracked holds | Intake/commercial subset plus foundation: 4 passed. |
| D | `commercial_api.py`, `services/commercial.py`; listings, exclusions, offers, snapshots, version confirmations, amendments, reschedule/cancellation proposals | Mutual-version and permissions checks passed. |
| E | `services/matching.py`; direct/one-hub candidates, hard gates, reproducible scope, estimate sources, deterministic normalised ranking and visible rejection diagnostics | Routes/quotes suite brought total to 7 passed. Final regression checks incomplete costs, equal-range normalisation and deterministic ordering. |
| F | `logistics_api.py`, `services/logistics.py`; synthetic explicit quotes, expiry/scope, named payer/cap enforcement, overrun exception, new rounds/requote | Above-cap acceptance rejected, old quotes invalidated on amendment, no-acceptance remained separate from sale. |
| G | Atomic SQLite holds/commit/release/expiry; shipment/items, state transitions, two-party physical pickup/hub custody, idempotency, partial quantity custody; `consolidation_api.py` | File-backed concurrent reservation race: one success/one rejection; expiry freed capacity. Approved batch preserves independent per-asset custody. |
| H | `exception_api.py`, synthetic telemetry, configurable thresholds, high-priority holds, scoped qualified reports, manual escalation when specialists unavailable | Scoped review keeps original flags; ordinary recipients excluded. No carrier => retained hold/manual outreach. |
| I | `receiving_api.py`; disputed/reconciled receipt, inspection/price revision, record-only settlement, disposition records and closure gates | Initial missing DISPUTED enum fixed; shipment tests brought total to 9 passed. Final tests preserve old prices, distinguish reported/confirmed settlement, and block premature closure. |
| J | React principal pages, shared TS types, API client, forms/field errors, actor switch, Leaflet/OSM map + textual route details, custody/exception/receiving screens | `npm run typecheck` and `npm run build` passed. Actual frontend HTML/module serving and API proxy verified. |
| K | API/domain/security/race regression tests, real HTTP rehearsal, startup runner, README/demo guide, reproducible reset | `python -m pytest -q`: **24 passed**, one test-client deprecation warning. `python integration_smoke.py`: real FastAPI + Vite/proxy + complete HTTP workflow **passed through CLOSED**. |

## Acceptance coverage

| Required scenario | Verified evidence |
|---|---|
| Intake persists after refresh/restart | POST/GET intake; file-backed DB engine reopen test; real HTTP rehearsal |
| Critical missing data blocks next stage | Missing authority evidence => review; known mass/location/window gates |
| Unknown chemistry never silently matches | Explicit UNKNOWN stored; chemistry/capacity reason codes |
| Safety flags create owned holds | Swelling seed; listing blocked; flags cannot be erased by originator |
| Incompatible receiver exclusion explained | Chemistry, pathway, scope, capacity, registration and time reasons |
| Direct and one-hub plans | Route tests/rehearsal; proxy assumptions and ordered legs |
| Both parties confirm same version | Commercial version tests; reschedule/amendment invalidation |
| Above-cap quote cannot book | Over-budget rejection + owned case; payer-only acceptance |
| No transporter acceptance remains recoverable | No-acceptance case/reopen test; no fictitious shipment |
| Capacity cannot overbook | Two simultaneous SQLite reservations for 60 kg; only one 42 kg hold |
| Pickup changes custody only physically | First party confirmation retains originator; second transfers |
| Telemetry labelled synthetic | SIMULATED source/threshold and alert assertions; no diagnosis |
| Receiving discrepancy prevents closure | Receipt dispute keeps recorded holder and blocks acceptance |
| Receipt alone is incomplete | Closure gate assertions before inspection/settlement/disposition |
| Duplicate actions do not duplicate allocations | Offer/booking/pickup idempotency and custody event counts |

## Integration failures fixed

- Pytest initially could not import `app`: fixed project pythonpath.
- Receipt-dispute state was missing from the battery enum: added centrally and retested.
- First real HTTP rehearsal exposed an authority follow-up left open after reviewed evidence supplied. Closure correctly refused. Intake now closes only mechanically fulfilled missing-data/authority cases with reviewer-evidence references and append-only audit; safety cases do not auto-close. Added regression; second HTTP rehearsal passed.
- Command sessions have isolated localhost networking here. Standalone cross-session curl failed. `integration_smoke.py` starts both servers and the checks in one process group; frontend, backend and proxy then passed. This is an environment limitation, not claimed deployment.

## Decisions, limits and unimplemented extensions

- **Browser visual QA was not available**: no browser screenshots or browser-driven interaction test was performed. Type checks, production build, module serving, HTTP proxy and real API workflow were verified independently.
- Demo login is intentionally simple/exposed and synthetic. Production identity, real legal/registration verification, hardware telemetry and payments are not implemented; money movement and safety certification are explicitly out of MVP scope.
- One named verified carrier quotes the entire direct/one-hub route. Both hub legs have explicit custody milestones; independent carriers/vehicles per leg are not supported.
- Consolidation is an all-party-approved manifest over individually agreed, quoted and booked asset shipments. It does not implement a joint discount/quote allocator or global fleet optimisation, and does not claim unknown savings.
- A new incident during an existing shipment remains held for qualified/manual resolution; autonomous return/redirection is deliberately absent. Creating a replacement controlled shipment after such an incident is not yet a self-service workflow.
- Settlement supports the full agreed amount and reported/payee-confirmed records. Partial instalments, detailed tax/invoice accounting and automatic overdue scheduling are not implemented. Supplemental optional battery passport/BMS/manufacturer/recall fields are not dedicated form fields; users can supply notes/evidence.
- Registry onboarding/review is functional but simplified: no real registry API, document extraction, automated identity deduplication or qualification authenticity verification. Mock statuses are never real certification.
- Schema version 1 is bootstrap-aware; future column migrations require explicit migration work. SQLite locks target one local instance.

Known unresolved test failures in the recorded project run: **none in the executed suite**. One Starlette/httpx test-client deprecation warning remains. This does not imply exhaustive defect freedom.

## Follow-up review (2026-10-10)

- Re-ran `python -m pytest -q` from the supplied source: **24 passed**.
- Added a skip-to-main-content link, explicit primary-navigation labels/current-page semantics, visible keyboard focus styling, and reduced-motion support. The icon-only narrow sidebar now exposes each destination through an accessible name and a native hover title.
- Frontend/browser verification remains pending in this environment: the extracted `node_modules` directory is incomplete (`vite` and TypeScript type definitions are missing), and `npm ci` did not complete here. Consequently, the frontend typecheck/build and `integration_smoke.py` could not be re-verified in this follow-up run. This is an environment/dependency-install limitation, not evidence of a source-code regression.
- Still to do on a machine with dependencies installed: `npm ci`, `npm run typecheck`, `npm run build`, then follow `docs/DEMO_GUIDE.md` in a browser at desktop and mobile widths; check keyboard-only navigation, focus visibility, form error announcements, and OSM tile failure/offline fallback.

Next concrete task: complete the browser-based acceptance pass above; then prioritise the remaining pilot extensions only if needed.
