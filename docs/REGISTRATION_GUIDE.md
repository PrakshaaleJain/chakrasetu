# Battery registration and PBS workflow

## Originator

Open **Battery Registry → Register battery**. Add a title, battery category, application, positive quantity, current address/coordinates, removal reason and current condition. Unknown is an explicit choice. Choose a PBS card based on preliminary observations; no selection is inferred from health measurements. Optional specifications and diagnostics remain blank/null when unavailable. Test information records source, units and sample scope; it does not become a qualified assessment.

Use **Save draft** for an incomplete private record. **Submit for network-operator review** creates Pending Review. Registration does not transfer legal ownership or physical custody. A different reported owner/custodian is text until the transfer workflow establishes the relevant parties. Mixed batches can be registered, but must be separated into individual or homogeneous registrations before matching. Sample readings never apply to every unit.

Attachments are optional. Use **Upload documents...** without choosing a document category. Up to four active files, 10 MiB per file and 25 MiB total are allowed. PDF, DOCX, XLSX, PNG, JPEG and UTF-8 text are supported subject to security restrictions. Filenames and size are shown; uploads show per-file progress, not a fabricated byte percentage. Removal retains metadata and audit history; removed files are no longer downloadable. Identical retries return the existing attachment.

The registry displays approval state, review notes, original PBS, separately recorded reviewer PBS, nullable inspection readings, handling concern and history. Revise/resubmit the same identifier when information is requested. Any intake edit or attachment change to an approved registration triggers review again. Approved listings resume after review; attachments and intake changes are locked after commercial allocation, where assessment/receiving evidence has its own workflow.

An approved registration can discover technically eligible participants before transfer documents are available. Actual offers, commercial commitment, route planning and dispatch still require confirmed authority and reviewed transfer evidence. Upload such evidence in the same generic field; the network operator classifies it during review. Then use **Confirm transfer authority against reviewed evidence**. If you upload after listing, obtain renewed registration approval before proceeding.

## Network operator

Use the existing **Battery Registry** queue, filter by registration state and select a record. Open submitted information and download authorized attachments. Record approval, rejection, an information request or specialist escalation with a reason. A reviewer cannot approve their own organisation's registration. Originators and transporters cannot approve registrations.

Ordinary registration review is separate from specialist safety review. L1/L2 can enter ordinary coordination after approval and capability checks. Unknown condition conservatively requires at least L3 handling capability even if the originator picked L1; the original selection remains unchanged. Reported damage preserves the specialist boundary with an L4 handling requirement even when owner PBS is lower. L3 requires verified uncertainty/assessment handling for the activity. L4 requires a current scoped qualified report and controlled specialist handling. L5 and explicit critical-hazard reports disable routine matching and dispatch. High concern never automatically selects recycling.

Operator-requested specialist assessment cannot be cleared by a subsequent ordinary approval alone. Qualified reports are recorded through **Exceptions & Reviews**. Each receiver, hub, transporter and operation is checked independently. If no qualified participant is available, retain the hold and manual escalation task. Critical reports are sticky across originator edits; this application does not automate emergency response or establish that an active hazard has ended.

## Organisation capabilities

Use **My Organisation** to maintain each existing activity's acceptance declaration: chemistry, category, condition, application, maximum PBS, uncertainty handling, damaged handling, service areas and activity-specific qualifications. Transport/dangerous-goods declarations do not grant repair or processing permission. A reduced declaration takes effect immediately. Self declarations never broaden verified permissions.

Request reviewed scope expansion through **Roles & Capabilities**. The same organisation account keeps its multiple roles. A network operator reviews the requested scope, reference and expiry. Facility identity, activity qualification and available capacity remain separate checks. Changes expire affected pending route plans and create reassessment tasks; accepted commercial terms are retained. Every booking/pickup rechecks current constraints.

## Policy and limits

`backend/app/pbs_policy.json` contains descriptions and conservative handling floors. An administrator managing the server can change this JSON and restart; `PBS_POLICY_PATH` can point to another local configuration file. Five ordered levels are required. Configuration may tighten, but cannot weaken, the L4/L5 safeguards. There is no public policy-editing endpoint.

PDFs are parsed and active actions/embedded content rejected. Images are decoded and bounded. Office ZIP/XML content is bounded; macros, embedded objects, encrypted entries, external relationships, unsafe fields/formulas, malformed XML and non-UTF-8 XML are rejected. Downloads are private attachments. These checks are not antivirus scanning or document authenticity verification; malware scanning/content-disarm infrastructure is outside this local implementation.

Legacy approved operating states are retained through an audited schema-v4 migration; no PBS is invented for historic records. Their original handling rules continue until revised. Fictional seed scopes remain labelled as example scopes, with synthetic provenance. Manual resolution of emergency cases, heterogeneous asset splitting automation, byte-level upload percentages and a policy-editing admin UI are not provided.
