# ChakraSetu homepage and pathway decision engine — implementation status

Current phase: completed local implementation, verification and source-package handoff. Implemented in the existing React/Vite/TypeScript + FastAPI/Pydantic + SQLite/SQLAlchemy application. No public deployment or browser rendering verification is claimed.

## Baseline and source

Started from clean commit `5518dae`. Read the attached homepage/engine brief and retained it in `docs/homepage-decision-engine-brief.md`. Inspected existing application navigation/authentication, registration/PBS and review rules, facility/operation/carrier qualifications, chain planning, economics, models/migrations, frontend conventions and tests. Baseline: **77 backend tests passed**. Prior registration status is retained in `docs/REGISTRATION_IMPLEMENTATION_HISTORY.md`.

## What changed

| Module | Implementation |
|---|---|
| Public homepage | Existing root now serves a complete public introduction: hero network, dominant workflow/explorer, fragmentation story, engine explanation, circularity outcomes, participant roles, intended impact and existing onboarding/login/footer navigation. |
| Interactive workflow | 24 keyboard/click-selectable SVG stages with branches, details, connected-stage navigation, highlighting, desktop zoom/reset, mobile stage alternative and reduced-motion CSS/scroll handling. |
| Shared authoritative rules | Safety/registration → application evidence → qualified reachable chain → comparable economics. Public scenarios and persisted assets invoke the same pure rule definitions. |
| Technical evidence | Uses only current independently accepted, unrevised qualified assessments for application qualification. Owner measurements are preliminary. Unknown/unreliable/conflicting evidence is explicit; known failure differs from insufficient evidence. |
| Safety precedence | PBS, critical observations and unresolved holds precede prices. L3 acceptance scope checked; L4 ordinary routes held with qualified controlled assessment possible; L5/critical routine dispatch disabled. Technician critical reports create persistent holds/exceptions. |
| Network feasibility | Separate receiver, operation, carrier, capacity, expiry, category, chemistry, condition, handling, geography and window checks at each reachable stage; product/material transport uses downstream scope, not battery-only credentials. |
| Economics | Explicit required components, INR transaction/NPV bases, recurring cash flows, common horizon/rate/perspective, source/date/expiry, uncertainty ranges/ties, missing-cost handling and negative net-cost explanations. Backend resolves current actual offer/quote IDs; clients cannot forge actual-quote provenance. |
| Operational integration | Battery Registry and Processing & Downstream use the same current decision/results view. User estimates are saved; GET recalculates and marks stale history after material changes. Existing chain-plan endpoint includes shared readiness gates. |
| History/overrides | Existing PathwayDecision table stores append-only snapshots, fingerprints, rules, sources and input requests. Owner/reviewer writes, reviewer-only reasoned overrides, hard-gate preservation and inactive historical overrides after changed inputs. |
| Public explorer | Five curated scenarios; typed bounded non-persistent endpoint, rate limit and no operational DB dependency or private IDs. Scenario amounts are isolated configuration, not live prices. |
| Presentation cleanup | Repetitive demo/synthetic/simulated labels removed from interface views and displayed summaries. Database/API provenance and production qualification guards preserved; transit non-diagnosis warning retained. |
| Migration | Additive logical schema 5 uses existing JSON/tables, preserves original history and legacy operating permissions, rejects unsupported versions and is idempotent. |

## Principal files/modules

- Backend: `decision_api.py`, `decision_schemas.py`, `decision_policy.json`, `explorer_assumptions.json`; `services/decision_rules.py`, `decision_evidence.py`, `decision_network.py`, `decision_adapter.py`, `pathway_economics.py`; existing assessment, chain-planner, model, seed and migration integration.
- Frontend: `HomePage.tsx`, `homepage/HeroNetwork.tsx`, `homepage/StorySections.tsx`, `WorkflowDiagram.tsx`, `workflow.ts`, `DecisionPanel.tsx`, `decisionTypes.ts`, `home.css`; existing App/login/Registry/processing integration and presentation-source projection.
- Tests: `backend/tests/test_decision_engine.py` (36 cases including parameterizations), existing migration test version updates, frontend DOM checks and real HTTP rehearsal additions.
- Documentation: `docs/HOMEPAGE_AND_DECISIONS.md`, README, environment example and security notes; original brief and previous status retained.

## Checks executed and actual results

- `/workspace/scratch/9580be7238f1/.venv/bin/python -m pytest backend/tests -q`: baseline **77 passed**. Final complete regression **113 passed**, including the completed-asset guard, with one pre-existing Starlette/httpx deprecation warning.
- Focused final engine suite: **36 passed**, including actual offer/quote resolution and expiry, conflicting accepted reports/revision, technician critical-hazard hold, controlled L4 specialist-only route, completed-asset unavailability and forbidden access.
- `npm test --prefix frontend`: **9 DOM assertion groups passed**, including homepage scenarios/backend calls, keyboard/zoom/reset, mobile alternative structure, reduced-motion CSS, no private prefetch and unavailable-engine recovery. These are not rendered browser tests.
- `npm run build --prefix frontend`: **passed**, including normal TypeScript checks and Vite production build. Main bundle approximately 393 kB (117 kB gzip), map and icons separated. Existing npm environment-config warning is non-failing.
- `frontend/node_modules/.bin/tsc --project frontend/tsconfig.json --noUnusedLocals --noUnusedParameters`: initial additional check found one unused homepage import; it was removed. Subsequent check passed.
- `/workspace/scratch/9580be7238f1/.venv/bin/python integration_smoke.py`: **passed** with real FastAPI/Vite, public policy/explorer via proxy, real-cookie private decisions/persistence/history/isolation, existing intake/commercial/over-budget/booking/custody/receipt/settlement/disposition workflow, five-stage transformation genealogy and organization onboarding/permissions. Uses an isolated temporary database and ephemeral credentials; servers stop after rehearsal.
- Migration run twice on existing working database: **schema 5; counts preserved** — 4 batteries, 1 transaction, 1 shipment, 2 custody events, 37 audits, 0 accounts and 0 historical pathway decisions. No reset or account provisioning performed against the working database.
- `git diff --check`: passed before final packaging. Changed Python formatted with Black and principal new frontend files with existing Prettier.

## Defects discovered and fixed

- Historic planner recommendation needed explicit compatibility with migrated legacy operating permissions; no missing PBS was invented.
- A current battery-capable carrier did not imply material/product qualification; all later transport legs now use the separate downstream scope checks.
- Two valid accepted reports could contradict each other; conflicts now remain indeterminate until a recorded revision resolves them.
- Critical observations in technician reports now create persistent safety holds rather than remaining only narrative evidence.
- Old recommendations/overrides could outlive changed inputs; GET recalculates, marks history stale and deactivates old overrides.
- A closed battery must not be offered as available inventory for another processing recommendation; a later cycle uses its linked downstream item.
- Tests were corrected where a remaining qualified assessment route was a valid fallback or malformed costs correctly failed schema validation before route-scope checking.
- Formatter whitespace changed literal CSS checks; tests now check the responsive/reduced-motion declarations without assuming formatting.

## Limits and decisions

- Browser/runtime networking separation prevents a cloud-browser visual walkthrough. DOM, build and HTTP checks do not establish pixel layout; no deployment occurred. Target-machine desktop/mobile and reduced-motion visual review is still needed.
- Recommendations establish qualified planning alternatives, not contracts or completion. Future outputs use source input mass as a conservative planning allowance, not a measured yield/product weight; added components and actual output composition/specification can invalidate the projection. Output-specific receiving/transport checks are repeated at actual handoffs.
- Technical/application measurements and prices must be supplied. There is no scientific battery-diagnosis/degradation predictor, market-price feed, automatic incentive lookup or automatic report authenticity verification. Missing inputs remain missing.
- NPV API supports recurring/intermediate flows and uncertainty; the simplified owner form handles upfront costs and a terminal benefit, with seven-day estimate validity. It does not infer financial payer allocation from a participant's technical capability.
- Current results recalculate on access/action/refresh. No background worker, websocket push or automatic contractual rerouting is introduced.
- Screening policy is administrator-managed JSON plus optional path/restart, not an admin policy editor. Public scenario prices are isolated configurable assumptions and never operational defaults.
- Original manual critical-hazard escalation, heterogeneous-batch splitting and production document-scanning limitations remain. Repetitive UI labels were removed at the user's request; internal provenance and qualification safeguards were not deleted.

Known unresolved code defects: none identified in completed checks. Next concrete task: run README setup on the presentation machine, complete visual desktop/mobile QA, and supply actual application evidence and valid commercial inputs for operational recommendations.
