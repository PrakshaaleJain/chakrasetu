# ChakraSetu — Comprehensive Redesign of Battery Registration, Perceived Battery Safety, Organization Capabilities, and Approval Workflows

## Objective

Modify the existing ChakraSetu codebase to implement a complete, integrated redesign of the battery-registration workflow, organization capability profiles, safety-aware matching, and network-operator approval process.

This is an implementation task. Inspect the existing repository, understand its architecture, and make the changes directly in the working codebase. Do not merely provide recommendations, create mockups, or build a disconnected prototype.

The objective is to make ChakraSetu practical for real-world EV battery circularity, where a workshop or other originator registers a battery using whatever information and measurements are actually available. The system must accommodate incomplete technical information, optional documentation, differing safety-handling capabilities, and multiple downstream pathways.

Preserve the existing architecture, business logic, design system, and working functionality wherever possible. Extend the existing implementation rather than creating a parallel application.

# Part I — Understand the Existing Codebase

Before making changes, inspect:

- The frontend framework, backend framework, database schema, API structure, authentication system, and authorization mechanisms.
- Existing battery-registration forms, battery models, organization profiles, and document-upload functionality.
- Existing registration statuses, operator dashboards, approval workflows, and audit mechanisms.
- Existing marketplace, organization discovery, matching, collection, transport, refurbishment, recycling, and transaction workflows.
- Existing role-based access control, navigation tabs, organization capabilities, and profile-editing interfaces.

Trace the actual data flow from originator submission through approval and downstream matching.

Identify which features already exist and should be extended, which need modification, and which are genuinely missing.

Do not duplicate existing functionality or introduce new abstractions without a concrete need. Do not rewrite unrelated modules, replace the technology stack, or fabricate functionality that the existing infrastructure cannot support.

# Part II — Redesign the Originator's Battery Registration Form

The originator is typically a workshop, collection point, fleet operator, or another organization handling an end-of-first-life or otherwise unwanted battery.

The originator cannot be assumed to possess the complete battery history, original specifications, BMS data, detailed diagnostic measurements, ownership chain, or supporting documents.

The registration form must therefore collect available information without requiring the originator to invent missing data or complete an unnecessarily complex questionnaire.

Organize the form into the following sections.

## Section A: Basic Information

Fields:

1. Registration title — required text.
2. Battery category — required selection: Battery Pack, Module, Cell, Other, Unknown.
3. Vehicle/application type — required selection: Two-wheeler, Three-wheeler, Four-wheeler, Commercial Vehicle, Other, Unknown.
4. Number of batteries — required positive integer.
5. Current location — required, using the existing location mechanism.
6. Battery removal date — optional.
7. Reason for removal — required selection: End of Vehicle Life, Reduced Performance, Fault/Damage, Accident, Upgrade/Replacement, Other, Unknown.
8. Current condition — required selection: Working, Degraded, Faulty, Damaged, Unknown.

Derive the originator organization from the authenticated account wherever possible. Do not ask users to repeatedly enter information already available from their account.

Preserve the existing distinction between an individual battery and a batch of batteries. If a batch contains batteries with materially different specifications or safety conditions, do not silently assign the same measurements or safety assessment to every battery. Extend the existing batch model if necessary.

## Section B: Battery Specifications

Add the following optional fields:

- Manufacturer/brand.
- Battery model.
- Serial number or battery identifier.
- Battery chemistry: LFP, NMC, NCA, LCO, LMO, Lead-acid, Other, Unknown.
- Manufacturing date/year.
- Rated voltage (V).
- Rated capacity (Ah).
- Rated energy (kWh).
- Approximate battery weight (kg).
- Battery age, if known.
- BMS availability: Yes, No, Unknown.
- Other known specifications.

Do not require the originator to know every specification. Do not assume that an unknown chemistry is LFP or that missing measurements indicate normal condition.

Validate numerical fields sensibly, preserve units, and avoid invalid calculations from incompatible or incomplete data.

## Section C: Inspection and Test Results

Introduce a question:

"Have any inspections or tests been conducted on this battery?"

Allow Yes, No, and Unknown.

If applicable, display optional fields for:

- Inspection date.
- Person conducting the inspection.
- State of Health (SoH, %).
- State of Charge (SoC, %).
- Measured pack voltage (V).
- Measured capacity (Ah).
- Internal resistance/impedance, with units and measurement method where available.
- Cell/module voltage imbalance, with units.
- Temperature observations.
- BMS fault codes.
- Physical inspection findings.
- Charging/discharging test results.
- Other tests conducted.

Where practical, distinguish measured values from BMS-reported values, estimates, and other reported information.

Do not force a workshop to conduct tests it cannot perform. A battery with no diagnostic measurements must still be registrable.

Missing information must remain explicitly missing. Never replace unavailable values with zero or assume that a battery has passed a test merely because no adverse result was entered.

## Section D: Ownership and Handling Information

Keep this section lightweight.

Include:

- Current owner, if different from the originator — optional.
- Current custodian, if different from the originator — optional.
- Availability for collection — required selection: Yes, No, To Be Confirmed.
- Preferred collection timeframe — optional.
- Handling instructions or known hazards — optional multiline text.

Remove excessive upfront transfer-authority requirements, mandatory ownership-chain documentation, and other unnecessary legal paperwork from the initial registration form.

Registration must not be treated as a transfer of ownership or custody.

Retain legitimate authorization and compliance checks at the appropriate later stage when an actual transfer or transaction requires them.

# Part III — Introduce Perceived Battery Safety (PBS)

## 1. Concept

Introduce a field named "Perceived Battery Safety (PBS)" in the battery-registration workflow.

PBS represents the originator's preliminary assessment of the battery's apparent condition and potential safety concerns. It is not a certified safety rating, a measured State of Safety, or a substitute for a professional assessment.

The purpose is to avoid forcing every originator to answer a long list of individual safety questions about swelling, leakage, thermal events, damage, and other observations.

The originator should instead select one clearly described safety level and optionally provide additional comments.

## 2. PBS levels

Implement five levels, ordered from lowest apparent concern to highest concern.

Display the levels as five clearly distinguishable boxes or cards, using a green-to-red progression. Each box must contain its level identifier, descriptive title, concise explanation, and corresponding color. Do not rely on color alone; the labels and descriptions must remain accessible.

### L1 — Low Apparent Concern

Color: Green.

Description: No obvious physical damage or abnormal behavior has been observed during the preliminary inspection, and no known safety concern has been reported.

Interpretation: This indicates low apparent concern based on available observations. It does not certify that the battery is safe.

### L2 — Minor Concerns

Color: Light green.

Description: The battery may be degraded, faulty, or previously repaired, but the originator has not identified an obvious acute safety concern.

Interpretation: The battery may require additional diagnostics or ordinary condition-specific precautions.

### L3 — Elevated Concern or Uncertainty

Color: Yellow.

Description: Concerning observations, unusual behavior, a history of damage, or significant uncertainty about the battery's condition warrants additional assessment or precautions.

Interpretation: Match only with organizations capable of handling the relevant condition and assessment requirements.

### L4 — High Safety Concern

Color: Orange.

Description: Serious damage, suspected internal failure, significant leakage, or other observations suggest that specialist assessment or controlled handling may be necessary.

Interpretation: Restrict ordinary routing. Require an appropriate safety review and a qualified downstream handling route before dispatch.

### L5 — Critical Hazard Suspected

Color: Red.

Description: An active thermal event, smoke, fire, or another observation indicates a potentially immediate or critical hazard.

Interpretation: Disable ordinary marketplace matching and routine dispatch. Escalate to qualified emergency or dangerous-goods personnel for appropriate handling instructions.

These are proposed ChakraSetu operating categories, not a claim that an internationally standardized PBS classification already exists.

Keep the level definitions configurable where practical, so authorized administrators can update the descriptions and handling policies without rewriting the entire matching engine.

## 3. PBS selection behavior

The registration form must:

- Present all five levels clearly.
- Explain that PBS is based on preliminary observations.
- Tell originators to select a higher-concern level when uncertain rather than assuming the battery is safe.
- Allow additional safety observations through an optional free-text field.
- Avoid requiring separate answers to a long list of individual hazard questions.
- Preserve the originator's selection and comments for subsequent review.
- Allow authorized reviewers to record a separate assessment without silently overwriting the original PBS value.

If the originator selects L1 but enters comments describing an active thermal event, the system must not blindly trust the selected level. Detect explicit critical-hazard reports where feasible, flag the inconsistency, and prevent ordinary routing until it is resolved.

Do not assume that an unreported hazard is absent.

PBS must be recorded separately from SoH, SoC, and any formally assessed safety state. Never infer one of these values from another.

## 4. Routing implications

Use the following initial workflow:

- L1: Ordinary matching may proceed after the required registration approval and applicable capability checks.
- L2: Ordinary matching may proceed where the recipient's declared capabilities cover the reported condition.
- L3: Match only to organizations whose capabilities cover the identified uncertainty or concern. Request additional assessment where required.
- L4: Restrict ordinary matching and require operator review before routing to a suitably qualified specialist.
- L5: Disable ordinary marketplace matching and routine dispatch. Enter a controlled safety-escalation workflow.

These are initial operational policies and must not be represented as universally applicable engineering safety thresholds.

A high PBS level must not automatically imply recycling. A battery may require specialist assessment before its final disposition can be determined.

If no suitably qualified organization is available, keep the battery on hold rather than relaxing the safety constraints.

# Part IV — Add the Generic Document Upload Field

Replace categorized document-upload interfaces with one generic upload field.

Field label:

"Upload documents..."

Use this description verbatim:

"You may upload any documents that you consider relevant to this battery registration. These could include a battery datasheet, technical booklet, purchase or ownership records, proof of authorization to transfer the battery, inspection reports, test results, warranty records, or photographs. Please upload only documents that are available to you and that you are permitted to share. Supporting documents are helpful for verification, but you can submit the registration without uploading any files."

Requirements:

- Maximum four files per registration.
- Maximum 10 MB per file.
- Maximum 25 MB total per registration.
- Support PDF, DOCX, XLSX, JPG, PNG, and other appropriate formats supported by the existing application, subject to explicit security restrictions.
- Do not require document-category selection.
- Do not require any document to be uploaded.
- Do not show an error simply because the upload field is empty.
- Show filenames, sizes, upload progress where supported, and removal controls.
- Enforce limits on the backend as well as the frontend.
- Validate file types and contents, and use safe storage and access controls.
- Prevent unauthorized access to documents.
- Associate files with the correct registration and prevent accidental duplication during retries.

An absent authorization document should not automatically invalidate the initial registration. Necessary authorization checks must remain in the appropriate transfer workflow.

# Part V — Add an Additional Information Field

Add an optional multiline text field.

Label: "Additional information"

Description:

"Enter any other information that may help us understand the battery's condition, history, availability, or handling requirements."

This field should allow the originator to record any relevant information that does not fit the structured fields, including unusual behavior, repair history, accident history, missing specifications, or collection constraints.

Use a sensible maximum length consistent with the backend and database.

# Part VI — Redesign Organization Capability Profiles

This is a central part of the redesign. Do not solve battery-safety matching solely through additional questions on the originator's form.

Organization profiles must represent what each organization can actually handle, process, transport, or receive.

Relevant organization types may include:

- Originators and workshops.
- Collectors and collection hubs.
- Transporters.
- Buyers and aggregators.
- Refurbishers and remanufacturers.
- Second-life operators.
- Recyclers and specialist treatment facilities.

Reuse the existing organization and role models. Do not create a separate account for every role.

An organization may hold multiple roles, and its profile must allow the organization to update its capabilities easily.

## 1. Battery acceptance capabilities

Provide relevant profile fields for:

- Accepted battery chemistries.
- Accepted battery categories: packs, modules, cells, and other applicable types.
- Accepted vehicle/application categories.
- Maximum PBS level the organization claims to handle.
- Supported battery conditions, including degraded, faulty, damaged, or uncertain-condition batteries.
- Specialist assessment capability.
- Damaged-battery handling capability.
- Critical-hazard handling capability, where appropriately qualified.
- Relevant transport and dangerous-goods capabilities.
- Permitted collection and service areas.
- Operational capacity, where applicable.
- Other technical restrictions or acceptance conditions.

Use multi-select fields and structured attributes where appropriate, rather than forcing all capabilities into a single text field.

Not every organization type requires every capability field. Show fields relevant to the organization's roles.

## 2. Role-specific capabilities

Capabilities must be specific to the activity being performed.

For example:

- A transporter may be capable of transporting certain battery chemistries and damaged batteries under specified conditions, without being qualified to repair them.
- A refurbisher may be capable of testing and repairing selected battery types but unable to receive batteries presenting critical hazards.
- A recycler may be capable of processing batteries after compliant receipt but may not have collection or emergency-response capability.
- A buyer may accept a battery only when an appropriately qualified transporter and downstream handler are available.

Do not interpret an organization's maximum PBS level as universal permission to perform every activity involving that level.

## 3. Declared versus verified capabilities

Distinguish between:

- Capabilities declared by the organization.
- Capabilities verified by ChakraSetu or an authorized reviewer.
- Expired, unverified, or otherwise unavailable credentials.
- Restrictions associated with particular activities or battery conditions.

Where legal authorization or specialist qualification is required, do not treat a self-declared capability as proof of authorization.

Allow organizations to update their capabilities through their existing profile interface without unnecessary administrative intervention. Record changes and apply them to future matching decisions.

If a capability changes materially, reassess affected pending matches and prevent the use of expired or invalid qualifications where they are required.

# Part VII — Implement Capability-Based Battery Matching

Extend the existing matching engine rather than creating a duplicate marketplace.

The matching process should evaluate:

1. Battery chemistry.
2. Battery category and relevant vehicle/application type.
3. PBS level and reported condition.
4. Any explicitly identified hazards or handling restrictions.
5. Organization capabilities for the specific activity.
6. Required authorization and qualification status.
7. Geographic coverage and logistics feasibility.
8. Relevant processing capability and capacity.
9. Commercial and operational suitability.

Exclude an organization from a particular match if it lacks a required capability or authorization.

Do not assume that an organization can handle every battery with a PBS level below its declared maximum if its chemistry, condition, activity, or handling constraints do not match.

For multi-stage workflows, evaluate each participant independently. For example, a battery may require a qualified transporter to take it to a specialist assessment facility before a refurbisher or recycler can accept it.

The system should distinguish:

- Technically and operationally eligible organizations.
- Organizations requiring additional information.
- Organizations excluded because of a specific unmet requirement.

Provide understandable exclusion reasons where appropriate. Examples include incompatible chemistry, unsupported battery condition, insufficient handling capability, expired qualification, or unavailable service area.

Among eligible organizations, rank candidates using appropriate existing criteria, such as distance, cost, processing capacity, and pathway suitability.

Do not allow commercial ranking to override a required safety constraint.

If no eligible match exists, communicate that fact clearly and keep the battery available for reassessment rather than routing it to an unsuitable organization.

# Part VIII — Separate Registration Approval from Specialist Safety Review

Preserve the requirement that every new battery registration is initially reviewed by an authorized network operator or manager.

However, distinguish this ordinary registration approval from a specialist safety review.

The purpose is to avoid unnecessarily delaying ordinary registrations while ensuring that high-concern batteries receive appropriate attention.

## 1. Registration lifecycle

Reuse existing status models where possible. Support these logical states:

- Draft, if drafts already exist.
- Pending Review.
- Additional Information Requested.
- Under Specialist Assessment.
- Approved.
- Rejected.

Do not introduce duplicate or conflicting statuses if equivalent states already exist.

## 2. Originator submission

On submission:

- Validate genuinely required fields.
- Validate upload limits and file security.
- Save the battery information, PBS selection, comments, and attachments.
- Record the submitting user, organization, and timestamps.
- Set the registration status to Pending Review.
- Show a clear confirmation that the registration awaits network-operator approval.

Do not expose pending registrations as approved resources for ordinary downstream matching.

## 3. Network-operator review

Provide an appropriate review interface using the existing dashboard and permissions.

Authorized reviewers should be able to:

- View the registration and available supporting information.
- Review PBS and the originator's comments.
- Inspect uploaded documents when authorized.
- Check data completeness and plausibility.
- Review the eligibility of the registration for coordination.
- Approve or reject the registration.
- Request additional information.
- Escalate a case for specialist safety assessment.
- Record a reason for each significant review decision.

Require a reason for rejection and a clear explanation when requesting additional information.

Record reviewer identity, timestamps, actions, and relevant notes using the existing audit infrastructure.

## 4. Specialist escalation

Use targeted escalation rather than treating every registration as a specialist safety case.

- L1 and L2 registrations may proceed through ordinary operator approval when there are no contradictory observations or other material concerns.
- L3 registrations should receive the level of review appropriate to the identified uncertainty and proposed destination.
- L4 registrations must be restricted to appropriate specialist routes and receive operator review before routing.
- L5 registrations must be removed from ordinary marketplace matching and escalated for controlled handling.

The operator's ordinary registration review should remain lightweight when the submitted information is sufficient and no exceptional concern exists.

Do not automatically route a high-concern battery to recycling without assessment. The appropriate next step may be isolation, specialist inspection, controlled transport, or another legally compliant treatment pathway.

## 5. Originator follow-up

Allow originators to:

- View their registration statuses.
- Read review notes and information requests.
- Edit registrations when requested.
- Add or replace attachments within the upload limits.
- Resubmit registrations without creating duplicate records.

Preserve registration identifiers and previously entered information.

Define what happens when material information changes after approval. Significant changes to safety observations, PBS, technical condition, ownership, or availability must trigger appropriate reassessment.

Do not silently retain an approval if a material change invalidates the original decision.

# Part IX — Maintain Separate Technical and Safety Concepts

Do not conflate PBS with battery health or final pathway suitability.

The following concepts must remain distinct:

- PBS: the originator's preliminary perception of safety.
- SoH: estimated or measured remaining battery health.
- SoC: charge state.
- Diagnostic results: actual measurements and test findings.
- Organization capabilities: what a particular participant can perform or handle.
- Registration approval: authorization to enter ChakraSetu's coordination workflow.
- Technical qualification: whether a battery meets a particular application's requirements.
- Transfer authorization: whether the relevant transfer can lawfully proceed.
- Final disposition: the selected downstream pathway.

Do not implement a universal rule such as "L4 means recycle" or "SoH below 60% always means recycling."

Any SoH thresholds used by the existing pathway-selection logic must remain configurable and appropriately qualified. The battery's final disposition should depend on safety, diagnostic evidence, application requirements, repairability, economic viability, and applicable regulations.

This task does not require inventing a new battery-health algorithm. Focus on making the registration, capabilities, safety classification, and approval workflows work together.

# Part X — Navigation, Roles, and Organization Accounts

Review the existing navigation and organization dashboard.

Do not expose every tab or workflow to every user regardless of relevance.

- Use the existing role- and capability-based navigation rules.
- Display only relevant functions to each organization and its authorized users.
- Ensure that organizations holding multiple roles can access the relevant functionality without creating multiple organization accounts.
- Permit organizations to update their capabilities and operational details through a straightforward profile interface.
- Preserve appropriate access for authorized network operators and managers.
- Enforce all visibility and permission restrictions on the backend, not just in the frontend.

An organization should not be able to access another organization's private registrations, documents, internal notes, or restricted transaction information without authorization.

# Part XI — Security, Data Integrity, and Backend Enforcement

Inspect the existing data model before making schema changes.

Implement only necessary migrations and preserve existing data.

Requirements:

- Make genuinely optional fields nullable throughout the frontend, backend, validation layer, and database.
- Do not populate missing technical data with fabricated defaults.
- Enforce file-count and size limits server-side.
- Secure document storage and access.
- Validate every status transition.
- Prevent originators from approving their own registrations.
- Prevent unauthorized organizations from accessing or modifying restricted records.
- Ensure only approved registrations are available for ordinary downstream matching.
- Keep a reliable audit trail for registration changes, PBS changes, approval decisions, capability changes, and relevant review actions.
- Handle duplicate submissions and attachment retries safely.
- Ensure that material changes to an approved record trigger the appropriate reassessment.
- Preserve necessary transaction-specific authorization and regulatory checks.

Do not weaken existing security or compliance controls simply to make the form shorter.

# Part XII — User Experience Requirements

Use the existing design system and visual conventions.

The originator experience should be straightforward:

1. Enter basic information.
2. Enter whatever battery specifications are available.
3. Provide any existing inspection and test results.
4. Select a PBS level and optionally describe observations.
5. Enter available ownership and handling information.
6. Upload up to four optional supporting files.
7. Add any other information in the free-text field.
8. Submit for network-operator review.

Use progressive disclosure so that diagnostic fields are shown when relevant without overwhelming users who have little technical information.

Display the PBS levels as clearly labelled, colored cards or boxes with accessible text descriptions. Include a non-color indicator of the selected level.

Provide useful validation messages, save drafts where supported, preserve data when validation fails, and prevent accidental double submission.

Make the interface responsive on mobile and desktop.

Do not add mandatory document categories, repetitive attestations, or unnecessary safety questionnaires.

# Part XIII — Testing and Acceptance Criteria

Implement or update automated tests covering at least the following.

### Registration

1. A registration containing only the required basic fields can be submitted.
2. Missing optional technical information does not block submission.
3. A registration without any uploaded files is accepted.
4. A registration without diagnostic tests is accepted.
5. Additional information can be stored and retrieved correctly.
6. Optional fields remain null when unavailable.

### Uploads

7. Up to four permitted files can be attached.
8. A fifth file is rejected.
9. A file exceeding 10 MB is rejected.
10. Total attachment size exceeding 25 MB is rejected.
11. Unsupported or malicious files are rejected safely.
12. Unauthorized users cannot access private attachments.

### PBS

13. All five PBS levels can be selected and persisted.
14. The selected level and its description are displayed correctly.
15. PBS is stored separately from SoH, SoC, and diagnostic results.
16. Contradictory critical-hazard reports cannot silently pass through ordinary matching.
17. High PBS levels do not automatically imply recycling.
18. Unknown battery condition is not automatically treated as L1.

### Organization capabilities and matching

19. Organizations can maintain multiple roles without duplicate organization accounts.
20. Role-specific capability fields are available where relevant.
21. Eligible organizations can be identified using chemistry, battery type, PBS, condition, and required capabilities.
22. Ineligible organizations are excluded from the relevant match.
23. Missing or expired required qualifications prevent the corresponding restricted activity.
24. A transporter, refurbisher, and recycler are evaluated according to their distinct capabilities.
25. No suitable match results in a clear hold or reassessment state rather than unsafe fallback routing.

### Approval and permissions

26. New registrations enter Pending Review.
27. Only authorized operators can approve or reject.
28. Pending and rejected registrations do not appear as approved resources.
29. L4 and L5 registrations follow the appropriate restricted workflow.
30. Authorized reviewers can request information and record review reasons.
31. Originators can revise and resubmit registrations when permitted.
32. Material changes to approved registrations trigger the intended reassessment.
33. Existing transfer authorization checks remain effective.
34. Role-based navigation and backend access restrictions work correctly.

Run the available automated tests, build, lint, and type-check commands. Fix regressions introduced by the changes.

Do not claim that tests passed unless they were actually executed and passed.

# Part XIV — Implementation and Final Report

Implement the changes directly in the existing codebase.

Do not stop after generating a plan, writing documentation, or creating a visual mockup.

When complete, provide a concise but precise implementation report covering:

- Registration form changes.
- PBS classification and routing behavior.
- Organization capability-profile changes.
- Matching-engine changes.
- Approval and specialist-escalation workflows.
- Database migrations and API changes.
- Security and authorization changes.
- Tests and build commands executed, with actual results.
- Remaining limitations or decisions requiring clarification.

If a requirement conflicts with the existing architecture, inspect the relevant code and implement the closest safe, consistent solution. Identify genuinely blocked requirements rather than silently omitting them.

The final implementation should provide an integrated workflow in which the originator can register a battery using incomplete but available information, select a preliminary safety level, optionally upload supporting documents, and submit for approval. ChakraSetu should then use the registration status, PBS level, organization capabilities, and applicable constraints to determine which downstream organizations can appropriately participate, while reserving specialist escalation for cases that genuinely require it.