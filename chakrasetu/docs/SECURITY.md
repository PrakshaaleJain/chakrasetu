# Authentication and permission matrix

Every operational API depends on authenticated session validation. Only health, account registration/login/reset request/reset and OpenAPI documentation are public. The previous `/demo/users` endpoint is removed; bearer demo tokens never authenticate. Original regression tests use isolated dependency overrides, while account, boundary and circularity tests use the actual cookie/session/CSRF implementation.

| Role | Access and actions | Additional resource constraint |
|---|---|---|
| Platform administrator | Account activation/deactivation, recovery issuance, membership assignment, configuration/evidence administration when separately assigned reviewer role | Explicit Account flag created by one-time CLI bootstrap; audited; never granted by organization role APIs |
| Network reviewer (`REVIEWER`) | Operational evidence, exceptions, qualification and completion review | Explicit `GLOBAL_OPERATIONS` review scope, assigned by platform administrator or explicit development provisioning; excludes account administration |
| Organization administrator (`ORG_ADMIN`) | Own profile/contact/logo/facility edits and capability/role requests; existing membership reduction/deactivation | Selected organization only; no platform role escalation; initial joining another organization needs platform identity/consent review |
| Originator (`ORIGINATOR`) | Intake, evidence upload, listing, commercial confirmation, input-owner processing/title approval | Own organization/assets/contract participation |
| Diagnostic technician (`TECHNICIAN`) | Assigned assessment submission and immutable revisions | Assigned facility belongs to selected organization; physical custody before measured submission; no offer/terms writes |
| Refurbisher (`REFURBISHER`) | Refurbishment/repurposing jobs, receiving and commercial terms | Own qualified facility and physically held inputs; every owner approves output-title terms |
| Second-life operator (`SECOND_LIFE`) | Repurposing/integration, product acceptance, take-back proposal/confirmation | Own qualified facility, applicable specifications and actual physical custody |
| Recycler (`RECYCLER`) | Dismantling/recycling, authorized batches and measured outputs | Own qualified facility; unrelated jobs/batches inaccessible for mutation |
| Processor/refiner (`PROCESSOR`, `REFINER`) | Material processing/refining jobs and offtake | Verified operation/material scope; own facility/received lots |
| Manufacturer (`MANUFACTURER`) | Received material acceptance, manufacturing outputs and offtake | Own qualified facility and accepted inputs |
| Deployment customer (`CUSTOMER`) | Receiving, application-specific acceptance, installation/service/retirement and take-back confirmation | Current physical custody; deployment at its own verified organization |
| Carrier (`TRANSPORTER`) | Eligible operational quote requests, own quotes, assigned shipment pickup/arrival | Own verified profile and current scope/capacity/coverage; no assessment, asset identity or commercial-term edits |
| Downstream buyer (`BUYER`) | Discovery, own offers, version confirmation, receiving/settlement | Contract party or qualified receiving organization; no technician/process permission unless separately assigned |
| Hub (`HUB`) | Approved dwell/forwarding, two-party hub custody | Assigned hub and manifest; no battery/assessment identity edits |

A user has multiple Membership rows, each with explicitly assigned roles. A session retains a legacy membership/role marker for backward compatibility, while all approved roles in that active organisation membership are checked together; changing an identifier cannot select another person's membership. Organization inactivity, membership inactivity, role removal, account inactivity, expiry or revocation causes rejection. Legacy `BUYER` compatibility is used for commercial/receiving pages for the explicit downstream operational roles. Transformation permissions separately check operation-specific assigned roles, facility ownership, custody and qualification. Holding ORG_ADMIN alone does not confer process, transport or platform-wide powers.

Operational network reviewers have a deliberately platform-wide documentary scope in this local implementation, rather than per-case assignments. This broad access is explicit and audited, and cannot be granted by an organization administrator. Fine-grained regional/assigned-case scope is not implemented.

## Mechanism

Argon2id uses memory=64 MiB, three iterations, four lanes, randomized salt; hashes are upgraded on successful login when parameters change. Random session tokens are stored as SHA-256 digests, expire after eight hours, and are held in HttpOnly SameSite=Lax cookies. `APP_ENV=production` adds Secure. The browser stores no bearer token or password in localStorage. A separate readable session-bound CSRF cookie supplies `X-CSRF-Token`; all protected mutations validate its hash against the session. Origins on mutations are checked against configured CORS origins. JSON validation and CORS/origin restrictions protect pre-login account actions; command-line clients without Origin can use these endpoints.

Persistent authentication limits: 10 attempts per IP/email and 60 per IP in 15 minutes. Forwarded IP headers are not trusted. A reverse proxy requires its own appropriately configured outer rate limit to avoid grouping all clients under the proxy address. Expired attempt/session rows are retained; housekeeping scheduling is not included.

Account deactivation, logout, password changes/reset and membership changes invalidate sessions. Recovery tokens expire after 30 minutes, are single-use under a SQLite write lock, hashed at rest and not audited verbatim. Recovery delivery is manual and requires administrator identity review. No account-confirmation or password-reset email is falsely claimed delivered.

ORM access is parameterized. Uploaded evidence remains private, bounded to four active attachments, 10 MiB each and 25 MiB total, with parsed PDF, decoded PNG/JPEG, bounded safe DOCX/XLSX and UTF-8 text validation; historical custody/audit/job links are append-only. Corrections create revisions/events. Security headers prevent framing/sniffing and disable response caching. Registration/validation errors do not expose passwords or stack traces. No production default password exists.

## Remaining deployment work

The runnable deliverable is local. HTTPS serving, frontend security headers/CSP at the host, encrypted backups, monitoring, email delivery/verified-email onboarding, MFA, automated invitation acceptance, malware scanning and external qualification/permit authenticity checks require deployment-specific work. Do not call this a certified production security system. SQLite write serialization and rate-limit storage target a single application instance.


## Organisation UX v3

The additive v3 tables are `organisation_accounts` (unique organisation and account bindings) and `capability_requests` (controlled request kind/action/status, requested scope and decision history). New duplicate organisation registrations are rejected by normalised official-name checks under a write lock. Migration preserves legacy users/accounts; it does not merge credentials or grant one legacy user another legacy user's roles. Primary bindings are deterministic and new role grants target that account. Cross-organisation context switching remains a protected compatibility API, with no ordinary role-switching UI.

Profile and facility-description writes check the owning organisation. Identity names and operational scope expansion require reviewer decisions. Role/capability submission cannot grant REVIEWER, ORG_ADMIN or platform flags. Organisation-level legacy membership updates cannot expand assigned roles. Operation and transport approvals may grant the matching operational role to the primary account; eligibility still requires each relevant identity, facility, scope, validity, custody, safety and capacity gate. Suspend/remove decisions disable the scoped qualification without deleting historic records. Request history plus append-only AuditEvents records decisions and information exchanges.

Directory and legacy network endpoints use explicit projections. Contact fields are omitted from their payloads. The separate contact endpoint enforces PRIVATE (own organisation or explicit global reviewer) versus PARTICIPANTS/PUBLIC (authenticated participants); accesses are audited without recording contact values. There is no anonymous public contact endpoint and no personal-contact directory.

Logo writes are owning-organisation only. PNG/JPEG/WebP content is actually decoded and re-encoded, bounded to 2 MiB and 16 million pixels, with metadata removed and random generated filenames. SVG/executable/malformed content is rejected. File paths are never taken from uploaded filenames. Logo responses require authentication. Persistent hosting must retain `UPLOAD_DIR`; an ephemeral deployment filesystem will lose logos despite database persistence. Removed/replaced files are inaccessible through the API but kept for later retention management.


## Registration v4

Registration approval is separate from operational handling state, transfer authority, diagnostics and physical custody. Protected review requires explicit network-review scope and rejects self approval. PBS is preserved as an owner report; conservative handling requirements and reviewer assessment are separate. Critical reports persist across originator edits and cannot be released by routine approval/scoped-clearance actions. Non-approved registrations and missing/expired activity qualifications cannot support booking. Generic uploads do not self-verify transfer authority. Resource ownership and private downloads are enforced server-side. Removing/changing evidence or revising an approved intake requires reassessment.

Document checks reduce active-content exposure; they are not an antivirus or authenticity service. Critical-hazard resolution remains a qualified manual operational process; no emergency response is synthesized.

Database dependencies use function scope so commit/rollback completes before the response is sent. A downstream quote cannot be reported as saved before it is committed. SQLAlchemy failures return a recoverable failure after rollback; no stack trace or SQL parameters are included in the user response.

## Public decision explorer and private histories

The public explorer processes bounded typed inputs and curated assumptions without a database dependency or persistent writes. It exposes no participant/asset identifiers or contacts and enforces a 90-request/minute per-client limit. The origin middleware and security headers continue to apply.

Operational results use resource access checks; only the owner organization or operational reviewer may record financial comparisons, and administrative assumptions additionally require platform administration. Actual offer/quote amounts are looked up server-side and validated against the asset, pathway, facility, current terms and qualification. Ordinary responses omit raw input snapshots. Overrides are reviewer-only, reasoned, append-only and cannot waive hard gates; changed inputs deactivate historical overrides. Decision ORM rows reject update/delete just as custody/audit rows do.

Schema version 5 stores additions in existing JSON records without losing history. UI removal of repeated example-data labels does not remove internal provenance or allow example qualifications in production mode.
