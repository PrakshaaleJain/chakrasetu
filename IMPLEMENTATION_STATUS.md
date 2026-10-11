# ChakraSetu registration/PBS redesign — implementation status

Current phase: completed local implementation, verified integration, source package handoff. No deployment or browser-rendering verification is claimed.

## Baseline and source

Started from clean commit `d74e79f`. Read the complete attached redesign brief, retained verbatim in `docs/battery-registration-redesign-brief.md`. Inspected intake/schema/models, authentication/resource permissions, documents, organisation scope requests, matching, specialist reviews, commercial/logistics services and frontend integration. Baseline: **48 backend tests passed**. The restored environment had a missing venv executable and truncated cached bytecode; these were repaired before the baseline. Earlier implementation status is retained in `docs/ORGANISATION_UX_HISTORY.md` and `docs/EVOLUTION_HISTORY.md`.

## Completed modules and dependency order

| Phase | Changes | Modules |
|---|---|---|
| Foundation | Reused existing stack, models, authentication, account/role boundaries and original workflow. Shared schema base avoids circular imports. | `base_schemas.py`, existing schemas/auth/db |
| Registration model | Nullable specifications; typed reported inspections, measurement provenance/units/sample scope; owner/custodian declarations; collection availability; additional information; mixed-batch hold. | `schemas.py`, `registration_schemas.py`, `enums.py` |
| Approval and PBS | Private drafts, pending/information/specialist/approved/rejected review history; no self approval; original PBS retained separately; conservative handling requirements; critical reports persist across originator edits; material revisions revoke approval. | `services/registration.py`, `intake_api.py`, `pbs_policy.json`, exception service |
| Documents | Optional generic upload; four files/10 MiB each/25 MiB total; PDF parsing, image validation and safe bounded Office ZIP/XML; private downloads; retry deduplication; audited soft removal. | `services/documents.py`, intake evidence routes, `requirements.txt` |
| Capabilities and matching | Activity-specific declaration/verified scope, structured technical/application selections, PBS limits, damaged/uncertain/dangerous-goods handling, service areas, expiry, per-participant checks, exclusion/information reasons, route invalidation after capability changes. | organisation schemas/API/service, matching/circularity/pathway services, `registration_seed.py` |
| Commercial integrity | Technical discovery can precede transfer documentation; actual commitment/dispatch retains reviewed authority gates. Route snapshots include PBS/application/approval revision. Existing terms, budgets, capacity, custody and receiving behavior remains enforced. | commercial/route/shipment integration |
| Frontend | Lightweight form, progressive diagnostics, five accessible PBS cards, generic optional documents, draft/resubmit, reviewer queue/filter/history, participant explanations, current activity acceptance editors and scope requests. | `Intake`, `Registry`, `RegistrationFields`, `RegistrationReview`, `SafetyScopeEditor`, organisation integration/types/styles |
| Persistence boundary fix | A repeated HTTP rehearsal exposed a request racing the previous quote commit. Database dependencies now finish/commit before a success response; database failures roll back and return a recoverable error. No artificial delay/retry masks this defect. | protected API/auth `Depends(get_db, scope="function")`, `db.py` |
| Migration/docs | Additive schema v4 preserves legacy records and operating permissions without inventing PBS. Updated setup, security and registration guide. | `migrations.py`, `README.md`, `docs/REGISTRATION_GUIDE.md`, `.env.example` |

## Verification actually executed

- `/workspace/scratch/9580be7238f1/.venv/bin/python -m pytest -q backend/tests`: **77 passed**, one pre-existing Starlette/httpx deprecation warning.
- New registration suite includes required-only/no-file/no-test intake, nulls, five PBS levels, contradiction/critical holds, scope/condition limits, L4 controlled specialist routing (including contradictory low PBS with reported damage), private documents, limits/formats/retries/removal, information exchange, resubmission/reassessment, drafts, multi-role/resource protection, policy tightening and failure-before-success database cleanup. Existing tests preserve budget, capacity, custody, receipt/settlement/disposition and circularity behavior.
- `npm test --prefix frontend`: **six DOM assertion groups passed**: role navigation, contacts/privacy, statuses, registration PBS/optional input submission, activity acceptance fields, guarded navigation.
- `npm run build --prefix frontend`: **passed** (TypeScript build and Vite production bundle).
- `frontend/node_modules/.bin/tsc --project frontend/tsconfig.json --noUnusedLocals --noUnusedParameters`: **passed**. No separate frontend lint script exists. `git diff --check` passes; changed Python files were Black-formatted.
- `python integration_smoke.py`: **passed after fixing the commit boundary**, with actual FastAPI, Vite/proxy and cookie authentication. Rehearsal covers PBS intake/operator approval, evidence and authority, direct/one-hub routes, bilateral terms, over-cap rejection, quote/capacity/shipment creation, confirmed physical custody, labelled telemetry, receiving dispute, settlement/disposition closure, second-life deployment/retirement, recycling/refining/manufacturing genealogy, profile persistence and capability review.
- Schema v4 migration executed twice against the existing database: preserved **4 batteries, 1 transaction, 1 shipment, 2 custody events, 37 audit events and 0 accounts**. No data reset or default credential provisioning occurred.

## Corrected failures

Updated historic tests that expected screening alone to approve registrations or schema version 3. Fixed an audit keyword collision, declaration field visibility, conservative damage handling and one incomplete unit-test fixture. A check initially used a nonexistent `tsconfig.app.json`; rerunning against the actual `tsconfig.json` passed. The intermittent real-HTTP quote/booking failure was resolved by completing database dependencies before returning responses; a rollback regression test confirms no successful save response is issued when persistence fails.

## Decisions and limits

- Required initial registration is lightweight; transfer authority is deferred to actual commercial commitment/dispatch. Different reported owners/custodians remain declarations, not automatic organisation ownership/custody changes.
- Unknown condition needs at least L3 handling; reported damage keeps the existing specialist boundary, conservatively requiring L4 handling even if the selected PBS is lower. This is a coordination requirement, not a diagnosis. Original PBS is preserved. L5/explicit critical reports remain held for qualified manual operational instructions; no emergency-response or automatic critical-clearance service is implemented.
- Mixed batches remain registrable but blocked until manually separated into individual/homogeneous registrations. Automatic heterogeneous splitting and per-unit genealogy creation from a batch intake are not added.
- Any approved intake edit or attachment change requires review again. After allocation, the accepted registration is locked and dedicated assessment/receiving evidence workflows remain available. Old documents/events are retained; storage housekeeping is not automated.
- Document validation is not antivirus scanning or authenticity certification. Conservative active-content, archive, XML and PDF restrictions reject some otherwise readable files. Upload progress is per file, not byte percentage.
- PBS configuration is administrator-managed JSON plus optional `PBS_POLICY_PATH` and restart; it may tighten safeguards. No policy-editing admin UI is provided.
- Legacy operating permissions are explicitly marked as migrated. No PBS or formal diagnostic evidence is manufactured. Fictional capability/price/telemetry provenance remains preserved, with example scope labels and production rejection of synthetic operations.
- Browser preview is still blocked by the cloud-browser/runtime networking separation; DOM/build/HTTP checks do not prove browser layout. No public deployment occurred.

Known unresolved code defects: none identified in the completed checks. Next concrete task outside this environment: use README setup on the target machine, complete a visual mobile/desktop walkthrough and, before live operations, establish qualified manual escalation and production document-scanning procedures.
