# Homepage, workflow and pathway decisions

## Run and present

Use the installation and account-bootstrap commands in README. Start both servers with `python dev.py`, then open **http://127.0.0.1:5173**. The root now opens the public homepage. No sign-in is needed to explore it. Sign in from the upper-right button; **Join the network** opens the existing account/organization registration. An authenticated participant can return to the homepage from **Explore ChakraSetu** in the workspace header.

The homepage contains the hero network illustration, a dominant interactive workflow, a scenario explorer, the coordination problem, the decision process, five possible outcomes, participant roles, a circularity narrative, and onboarding/footer navigation. It does not expose operational accounts, contacts, batteries, contracts or documents, or publish fabricated impact counters.

The diagram has 24 selectable stages, including all five PBS levels. Tab focuses stages, Enter/Space selects them, and arrow keys move between stages. The contextual panel explains inputs, rules, next actions and connected stages. Zoom and reset control the desktop canvas. Small screens get legible full-size stage buttons and the same contextual details. CSS and scroll controls respect reduced-motion preferences. The highlighted branch follows the engine's current scenario result. Diagram branches explain alternatives; they do not establish a booked route.

Choose one of five scenarios and vary its meaningful inputs. Every calculation calls `POST /public/pathway-explorer`. This endpoint invokes the same pure backend rules as the operational adapter, with isolated scenario inputs. It never reads operational entities, writes battery/decision/audit rows, or impersonates a participant. There is a 90-evaluations-per-minute per-client limit. Scenario prices are configured in `backend/app/explorer_assumptions.json`; they are comparison assumptions, not live quotations and not defaults for actual battery decisions. The interface explains this once next to the controls rather than showing repetitive demo/synthetic banners.

## Use an actual battery record

1. Register known facts, preliminary PBS and optional evidence in Battery Registry. Missing health or history is allowed.
2. The originator's submission remains Pending Review. A network reviewer approves entry separately from any technical/safety qualification.
3. Select the battery. **Pathway decision** automatically evaluates current stored information. The same view is also available under Processing & Downstream → Pathways.
4. Inspect alternatives, failed rules, missing tests, eligible stage facilities and separately eligible carriers. Expand participant exclusions to see stable reason codes.
5. Use **Record current evaluation** to preserve an append-only snapshot. **Recalculate** refreshes the current evidence and commercial inputs. Viewing the current decision always recomputes it; changed capabilities, evidence, windows, policy or quote validity show a stale-history notice. Old snapshots are retained, not overwritten. Cross-user updates appear on refresh/reopen; there is no push-notification service.
6. Use **Add economic inputs** to enter benefits and required cost components. Amounts cover the entire registered quantity in INR. Blank remains unknown; explicit zero requires a documented assumption. This form records estimates with a reference, recording date and seven-day validity.
7. A reviewer can select a currently feasible alternative with a required reason. This creates another decision and audit event, preserving the engine's original recommendation. An override cannot bypass a safety, technical or capability gate. Historical overrides become inactive when their input snapshot changes.
8. Proceed through the existing listing/offer/terms workflow. A recommendation does not itself create a contract, satisfy transfer authority, approve a cost overrun, reserve capacity, change custody or certify disposition.

### Qualified technical evidence

The existing assigned-assessment form now supports structured findings: identified fault, repairability, compatible parts/expertise, post-repair requalification, vehicle-application acceptance, second-life-application acceptance, and remaining useful life. Every field supports Unknown. Submission requires the responsible operator's facility access and physical custody for measured reports; independent acceptance remains required. These fields are carried in the existing report JSON with procedure, measurements, application specification and limitations.

The engine uses only current independently accepted, unrevised reports from presently qualified facilities for application qualification. Owner/BMS-reported individual health measurements can contribute preliminary screening but cannot create an accepted application qualification. Estimated/unreliable health is not used as a measured SoH. Conflicting current accepted health measurements or findings become indeterminate until an explicit report revision resolves them. A critical observation submitted by a technician creates a persistent safety hold and exception even before the report is accepted.

## Authoritative evaluation order

- **Safety and entry:** registration permission, unresolved hazards/handling instructions, collection availability and homogeneous scope. L1/L2 still need the remaining gates. L3 needs appropriate acceptance/assessment scope. L4 blocks ordinary processing recommendations; only a qualified assessment route can be recommended under current controlled-handling instructions and operator approval. L5 or an explicit critical observation disables routine recommendations and dispatch.
- **Technical:** vehicle use requires accepted application evidence; refurbishment requires identified, repairable deficiency, compatible parts/expertise and requalification; second life requires a defined passing application and adequate useful life. Recycling needs an eligible treatment chain but no invented health threshold. Missing information differs from known unsuitability.
- **Network:** separate operation-specific identity, qualification, chemistry, category, condition, handling, service-area, availability and capacity checks for each reachable stage. Carrier qualification is independent from processing qualification. Future product/material legs additionally use the existing downstream carrier category/kind scope. An incomplete chain does not enter ranking.
- **Economics:** only feasible alternatives with complete, current, comparable values rank. Required omitted costs remain unknown. Ties within input uncertainty and the configured tolerance have no single winner. A negative best value is shown as a net cost, not commercial approval.

`backend/app/decision_policy.json` centralizes the ruleset identifier, initial 80%/60% screening bands and economic tie tolerance. `DECISION_POLICY_PATH` can point to administrator-controlled replacement JSON. Restart after editing. Invalid band order/range is rejected. Bands are screening aids; accepted application requirements determine suitability, and low SoH does not force recycling. Existing `PBS_POLICY_PATH` can tighten handling floors independently. The public policy endpoint supplies the same descriptions/bands/components to the interface.

## Financial sources and calculation

Two perspectives are supported and never silently mixed:

- **WHOLE_PATHWAY:** terminal sale/use value or discounted application benefits minus explicit downstream costs. Intermediate purchase transfers are excluded. A buyer's purchase offer cannot stand in for downstream terminal revenue.
- **ORIGINATOR_TRANSACTION:** the originator's current buyer purchase offer or documented transaction benefit, minus the costs borne in that comparison. Costs borne by someone else must be explicitly recorded as not applicable/zero with a reference; the engine does not infer an allocation from a technical capability.

For net transactions, all inputs use year zero. For NPV, benefits and costs have a year and optional `repeat_through_year`, with a positive common horizon and explicit annual discount rate. Recurring amounts are discounted once in each year of that interval. Different horizons, bases, rates or perspectives are not ranked together.

A `FinancialValue` records integer paise, source, reference, timezone-aware recording/expiry dates, cash-flow year and optional uncertainty. Allowed asserted sources are owner estimates, organization-provided estimates and restricted administrative assumptions. Users cannot submit an `ACTUAL_QUOTE` flag themselves. The backend resolves an existing `offer_id` or `transport_quote_id`, verifies asset/path/facility/terms/validity/current carrier scope, and inserts its actual amount and provenance. Existing purchase offers are accepted only for an originator net transaction; an intake-leg quote cannot pretend to cover every future product/material movement in a whole-chain comparison. Estimate and actual-quote sources remain distinguishable.

Required components are exposed by the policy API and defined centrally in `decision_schemas.COMPONENTS`. Refurbishment includes diagnostics, parts, labor, requalification, transport, warranty and risk. Second life includes assessment, repurposing, integration, installation, maintenance, warranty/risk and end-of-service treatment. Recycling includes collection, transport, packaging, handling, processing and other costs. No automatic market prices, incentive claims or live routing service are used.

The owner form supports upfront costs and terminal benefits. The API additionally supports recurring/intermediate dated cash flows and explicit uncertainty. There is no automated third-party quote feed or scientific remaining-life/degradation model; those inputs require documented qualified assessments/estimates. This engine coordinates decisions; it does not diagnose batteries or certify safety.

## APIs, persistence and security

- Public: `GET /public/pathway-policy`, `POST /public/pathway-explorer` (non-persistent).
- Authorized battery parties: `GET/POST /circularity/batteries/{id}/recommendation`, `GET /circularity/batteries/{id}/recommendation-history`.
- Operational reviewers: `POST /circularity/decisions/{id}/override` with pathway and reason.
- Existing chain-plan APIs `/circularity/batteries/{id}/pathways` remain compatible and now include the shared evaluation. Their economic recommendation cannot promote a chain excluded by the new authoritative readiness gates.

The existing `PathwayDecision` table stores inputs, sources, rule outcomes, configuration, fingerprint and history; its ORM rows now reject updates/deletes. Existing audits accompany writes/overrides. Ordinary decision responses omit raw private snapshots; reviewers can inspect them. Registration, session cookies/CSRF, resource checks, transfer-authority evidence, versioned terms and transactional booking controls remain in force.

Schema version 5 is an additive logical version: no prior table or column is dropped or rewritten. New assessment findings and decision snapshots use existing JSON fields/tables. Migration is idempotent and preserves legacy operating permissions, without inventing a missing historical PBS or assessment.

Repeated synthetic/demo/simulated banners are removed from the UI. A presentation projection omits internal synthetic flags from displayed debug/evidence summaries and uses neutral source labels. Database/API provenance, the production guard against example credentials, and the telemetry non-diagnosis warning are retained. The source file and original evidence are not altered by that presentation change.

## Verification boundary

Backend tests cover safety precedence, configurable bands, missing/unreliable health, application evidence, report conflict/revision, independent downstream transport scope, current qualifications, complete/incomplete finances, NPV/recurring flows, comparable perspectives, uncertainty ties, actual offer/quote resolution, private access, history invalidation, append-only records, safe reviewer overrides and non-persistent public scenarios.

Executable DOM tests cover the homepage, node selection and keyboard navigation, zoom/reset, mobile alternative structure, reduced-motion CSS, scenario API calls, navigation, no private prefetch and recoverable failure states. The real HTTP rehearsal starts FastAPI and Vite against an isolated temporary database and checks the public endpoints plus the established commercial/custody and five-stage circular workflows.

These are not browser screenshots or pixel/layout checks. This environment's cloud browser cannot reach the runtime's local servers; no hosted deployment is claimed. On the target machine, verify desktop/mobile presentation, focus visibility and reduced motion in an actual browser. The original manual critical-hazard escalation, manual heterogeneous-batch separation and production document-scanning limits remain as documented in REGISTRATION_GUIDE.md.
