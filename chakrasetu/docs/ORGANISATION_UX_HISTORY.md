# ChakraSetu organisation UX implementation status

Current phase: verified local implementation and source handoff. Existing architecture, records and core domain services are preserved. Browser visual/interaction verification is blocked by this environment; no public deployment is claimed.

## Baseline and source

Started from clean commit `a22bae1`. Read the entire 656-line attached UX brief, retained as `docs/organisation-ux-brief.txt`. Inspected accounts/membership, models/migration, domain permissions, directory projections, page navigation, forms, seed provenance and tests. Baseline: **41 backend tests passed**, frontend type check/build passed. The restored venv had a missing Python executable symlink; it was repaired to installed Python 3.12 before testing. Previous evolution details are retained in `docs/EVOLUTION_HISTORY.md`.

## Completed phases

| Phase | Implementation | Verification |
|---|---|---|
| 1. Audit | Existing workflow and UI wording/permission gaps recorded; no rebuild | Baseline 41 tests, type check/build |
| 2. Organisation accounts | Unique canonical organisation-account binding; duplicate registration guard; combined assigned roles; legacy identities retained; new capability/role grants target the primary account | Account-count, multiple-role, cross-organisation and v2 migration tests |
| 3. Navigation and permissions | Central `navigation.ts` labels/icons/groups/permissions; combined role menus and specialist tabs; guarded hash-page access; server role/resource checks remain authoritative | DOM navigation/route-guard assertions; real-auth regression tests |
| 4. Profiles and capabilities | Profile/facility edits, reviewed official-name changes, validated/re-encoded logos, declared versus approved scopes, persistent requests, information exchange, approve/reject/suspend/removal/withdrawal, decision history and audited grants | Seven new profile/security/migration tests; real HTTP request lifecycle |
| 5. Participant Network | One organisation card each, summaries/detail profiles, search/type/location/approved capability filters, logo/avatar, eye contact reveal, separate server contact projection and access audit | Directory uniqueness/filter/privacy API checks; DOM reveal/conceal and denied-access checks |
| 6. UX writing | Removed persistent banners and repetitive prototype wording; readable statuses/action labels; ordinary participant names/descriptions; internal provenance retained; telemetry explicitly simulated; reviewer qualifications moved into My Organisation | Source text scan; DOM badge/banner assertions; build |
| 7. Verification | Backend regressions, frontend DOM/type/build, real HTTP circular and organisation rehearsals; migration/seed preservation; setup/security/user guide | Results below |

## Verification results

- Full backend suite: **48 passed**, one existing Starlette/httpx test-client deprecation warning. This includes the 41 preserved checks and seven new organisation/privacy/capability/logo/migration/identity tests. Targeted organisation suite also passes after final audit-history changes.
- Frontend `npm --prefix frontend run typecheck`, additional `tsc --noUnusedLocals`, `npm --prefix frontend test` and production build pass. The executable DOM checks cover four assertion groups: combined navigation, contact reveal/privacy, readable status and guarded direct-page access/banner removal.
- `python integration_smoke.py` passes with real FastAPI + Vite/proxy and real cookie authentication: original transaction closure, diagnostic/refurbishment/integration, customer deployment/service/retirement, recycling/refining/manufacturing, five-job trace, then profile persistence, private contacts, one-card directory and pending → information → approved combined roles. Temporary DB/uploads/password are isolated and cleaned up.
- Ruff formatting/import checks and `git diff --check` pass. Final build splits map/icons into separate chunks; largest application chunk is approximately 331 kB.
- Existing working-database migration plus seed preserves battery, transaction, shipment and account counts (4/1/1/0); no reset or account provisioning was run against it.
- Actual browser attempt: application started successfully via `python dev.py`, but the cloud browser returned `ERR_CONNECTION_REFUSED` for localhost. Local Chromium installation returned invalid/truncated archives. Browser interaction/layout is **not verified**. DOM tests are not presented as browser rendering tests.

Failures encountered and fixed: missing venv executable; stale migration assertion expecting v2; seed presence check still looking for v2 after writing v3 (caught by real-server rehearsal); unused navigation icon imports; an automatic label conversion briefly imported `human` into its own module; formatting command initially used paths relative to the wrong directory. All were corrected and relevant checks rerun. A temporary >500 kB bundle warning was addressed by splitting map/icons; an empty React chunk was removed. npm emits an environment HTTP-proxy configuration warning; it does not prevent install/build. No executed check is silently claimed successful.

## Migration and integrity decisions

Schema **v3** adds `organisation_accounts` and `capability_requests` without deleting or duplicating batteries, transactions, custody events or processing records. Repeated migration is safe. Legacy accounts/memberships remain valid for historical tests/rehearsals; passwords and identities are not merged. New registrations have one canonical organisation account. Primary binding is deterministic for existing accounts; historic technician credentials remain compatible. The normal interface has no role/organisation selector. The ordinary interface exposes legacy membership administration only under platform administration; server-side organisation administrators can still reduce/deactivate existing assignments without expanding roles.

Ordinary profile edits do not start verification. Requested scope is separate from operational scope. Pending/rejected/withdrawn requests cannot overwrite approval; review expiry/reference is required for technical/identity approval. Suspend/remove disables the scoped qualification and preserves history. Removing the final legacy account role is blocked until organisation administration is assigned. Combined business permissions still require resource ownership, qualification, safety and capacity. Reviewer scope and production rejection of fictional accounts are preserved.

Seeded scopes appear as **Example scope**, not independently approved real-world evidence. Data provenance, fictional flags and rate sources remain internal. Missing contacts/logos/prices are not invented. Settlement still records reports/confirmations and moves no money.

## Deployment and remaining limitations

- Real-browser keyboard/layout/mobile/map QA is outstanding; follow `docs/ORGANISATION_GUIDE.md` locally. No public deployment or production-security certification is included.
- New registrations are organisation accounts; legacy per-person accounts are deliberately not destructively consolidated. An operator should review canonical binding before retiring legacy credentials in a real migration.
- Contact visibility distinguishes private from authenticated business visibility. PUBLIC business contacts still require sign-in; anonymous directory/contact browsing is not implemented. No personal contacts are exposed.
- Logos require durable `UPLOAD_DIR` plus the database for persistence across redeployments. Supported formats are PNG/JPEG/WebP only. Old replaced/removed files remain inaccessible through the API but retention cleanup is not automated.
- The 48-hour review response is a demonstration target, not an automatic approval deadline or delivered notification. No email/SMS infrastructure or actual outbound contact is claimed.
- Operational reviewers retain explicit GLOBAL_OPERATIONS scope; fine-grained assignment and deployment controls remain as documented in SECURITY.md. Capability approval records documentary scope, not battery safety certification or proof of external permit authenticity.
- Earlier domain limits (conditional pathway templates, whole-item transformations, downstream direct routes, manual safety escalation and record-only settlement) remain documented in EVOLUTION_HISTORY.md and README; this UX upgrade does not pretend to implement those extensions.

Known unresolved automated-test failures: none. Next concrete task: verify the supplied browser walkthrough on the target presentation machine, then configure durable database/upload storage for the selected hosting environment.
