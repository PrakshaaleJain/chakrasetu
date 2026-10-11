# ChakraSetu: Build a Premium Interactive Homepage, Supply-Chain Flowchart, and Rule-Based Battery Pathway Recommendation Engine

## 1. Overall objective

Transform the existing ChakraSetu application into a polished, production-quality platform with two integrated capabilities:

1. A visually exceptional, public-facing homepage that explains the product, tells its sustainability story, and presents an interactive, comprehensive flowchart of how EV batteries move through the circular supply chain.
2. A working, explainable, rule-based decision engine that evaluates registered EV batteries and recommends the most technically feasible and economically justified downstream pathway using information entered by originators, inspection results, organization capabilities, and available commercial data.

This is an implementation task. Inspect the current repository, understand the existing architecture, and make the changes directly in the codebase. Do not stop after proposing a design, producing a mockup, or writing a specification.

The homepage must feel like a premium product launch experience and an interactive hackathon presentation combined. It must be compelling enough to demonstrate the problem, the ChakraSetu solution, the workflow, the decision logic, and the sustainability impact during a live presentation.

The flowchart must be one of the defining visual elements of the website. It must occupy a substantial portion of the page, be detailed and interactive, and explain the actual supply-chain workflow. Do not place a small flowchart in a corner beneath generic marketing content.

The system should not merely look intelligent. Its pathway recommendations must be based on explicit, inspectable rules, measurable inputs, declared organizational capabilities, and available economic data. Do not use an LLM or an opaque machine-learning model as the source of truth for pathway decisions.

## 2. First inspect the existing ChakraSetu implementation

Before making changes, inspect:

- Frontend framework and routing structure.
- Backend framework, APIs, and database schema.
- Authentication and organization-account architecture.
- Existing registration, approval, PBS classification, and review workflows.
- Organization profiles, roles, and capability information.
- Existing buyer, refurbisher, recycler, transporter, and second-life operator representations.
- Battery matching, collection, transport, transaction, and downstream-processing functionality.
- Existing styles, component library, icon library, animation libraries, and responsive layout conventions.
- Any existing homepage, public routes, dashboard, or marketing components.

Reuse and extend the existing infrastructure. Preserve working functionality, permissions, data relationships, and application navigation.

Do not introduce a separate database for the homepage's demonstration flowchart if it can be implemented using the existing data model. Do not replace the project's technology stack or add large dependencies without a strong technical justification.

If the previous registration and PBS redesign has already been implemented, integrate with it. Do not create duplicate registration forms, duplicate organization models, or competing decision engines.

If some previously specified features are not implemented yet, identify the dependency and implement the necessary parts consistently with the existing architecture.

# PART A — HOMEPAGE EXPERIENCE

## 3. Design direction: a sustainability platform, not an internal dashboard

The homepage should communicate ChakraSetu as an enabling infrastructure layer for EV battery circularity.

The primary story is:

A battery reaches the end of its original use, or develops a problem. A workshop or other originator registers it. Its available specifications and inspection findings are recorded. ChakraSetu evaluates the feasible pathways, identifies suitable organizations, compares available economic options, and coordinates movement toward continued use, refurbishment, second-life applications, or recycling.

The resulting chain connects otherwise fragmented workshops, buyers, refurbishers, transporters, second-life operators, and recycling facilities.

The visual experience should feel contemporary, precise, sustainable, and credible. It should not look like a conventional enterprise dashboard, a generic admin panel, an AI-generated landing-page template, or an internal process-optimization engine.

Use a restrained, distinctive visual identity. Extend the existing ChakraSetu logo, colors, typography, and design system where available. If the visual system is underdeveloped, establish a coherent palette, typography hierarchy, spacing system, surfaces, iconography, and motion language.

Avoid excessive gradients, glowing cards, random floating shapes, repetitive glassmorphism, decorative AI imagery, and generic stock photography.

Use meaningful visual metaphors associated with circularity: connected organizations, battery states, material recovery, transport routes, and the movement of resources through a network. Prefer purposeful, custom-built SVG illustrations and animated diagrams over decorative imagery that does not explain the product.

The result should be a visually memorable product experience suitable for a hackathon demonstration.

## 4. Homepage structure

Create a scrollable homepage with the following major sections.

### Section 1: Hero

The opening viewport should immediately communicate the problem ChakraSetu solves.

Include:

- The ChakraSetu brand and existing logo, if available.
- A compelling headline about connecting EV batteries to their next best use.
- A concise description of the platform.
- A prominent call to action to explore the circularity workflow.
- A second call to action leading to the existing registration or onboarding experience, subject to the existing authentication model.
- A visual representation of a battery moving between different downstream pathways.

Possible messaging direction:

"Every EV battery deserves a smarter next destination."

Supporting message:

"ChakraSetu connects battery originators, transporters, refurbishers, second-life operators, and recyclers through inspection-driven decisions and capability-based matching."

Do not reproduce this copy mechanically if the existing brand already has stronger messaging. Preserve the underlying message.

Animate the hero visual with purposeful, subtle motion. For example, a battery may move through a connected network, with possible paths branching toward continued use, refurbishment, second-life applications, and material recovery.

Animations must reinforce the supply-chain narrative rather than act as unrelated decoration.

The hero should not occupy the entire site. It should establish the brand and direct attention to the much more substantial interactive flowchart immediately below it.

### Section 2: Interactive Supply-Chain Flowchart

This is the most important section of the homepage.

It must be visually dominant, expansive, and detailed enough to explain the complete ChakraSetu workflow during a presentation.

Make it a major full-width section with substantial vertical space. At suitable desktop sizes, the flowchart should be broad and legible, with connected nodes, branches, labels, and animated transitions.

The user must be able to interact with individual steps and understand what happens, why it happens, what information is required, and what rules govern each transition.

Do not simply draw a decorative flowchart using static boxes and arrows.

Implement a real interactive diagram using SVG, HTML, the existing diagramming library, or another appropriate approach compatible with the codebase.

Every major node should be clickable or keyboard-accessible. Selecting a node should reveal useful information through an adjacent information panel, side drawer, or a well-designed contextual detail area.

Include practical diagram navigation, such as zoom controls, reset view, and a way to return to the entire workflow. On smaller screens, reorganize the flowchart into a legible responsive experience rather than shrinking the entire desktop diagram until its text becomes unreadable.

Use animated connectors to show the direction of flow. When a node is selected, highlight its relevant incoming and outgoing connections. Keep animations smooth, purposeful, and accessible.

The diagram must represent the actual implemented workflow. Its nodes, decision branches, and labels must remain consistent with the backend rules described later in this prompt.

### Section 3: Why ChakraSetu

Explain the real-world fragmentation the platform addresses.

Cover:

- Workshops may possess batteries without having complete technical histories.
- Battery inspection capabilities vary between workshops.
- Suitable buyers and downstream processors may be difficult to identify.
- Different organizations can handle different battery chemistries and conditions.
- Batteries need different pathways depending on technical feasibility, safety, repairability, and economics.
- Transport and downstream processing must fit the battery's condition and the recipient's capabilities.
- Information and coordination gaps can cause reusable resources to be lost to inefficient or inappropriate disposal pathways.

Present the problem as a connected system rather than a disconnected collection of feature cards.

Do not invent market statistics, company partnerships, battery volumes, carbon savings, or user testimonials.

### Section 4: How the decision engine works

Explain the distinction between:

1. Information supplied by the originator.
2. Diagnostic evidence obtained through inspection.
3. Perceived Battery Safety (PBS).
4. Pathway eligibility rules.
5. Organization capability matching.
6. Economic pathway comparison.
7. Final recommendation and coordination.

This section should explain why ChakraSetu does not blindly send every battery below a single SoH threshold to recycling.

Illustrate the principle that safety and technical eligibility are evaluated before economics.

Make it easy to understand how the platform reaches a recommendation and why a particular route is selected.

### Section 5: Circularity outcomes

Present the major outcomes that ChakraSetu can facilitate:

- Continued automotive use, where suitable.
- Refurbishment and requalification.
- Second-life applications, such as stationary storage.
- Recycling and material recovery.
- Specialist assessment and controlled handling when the condition is uncertain or hazardous.

Explain that these pathways are alternatives selected according to battery condition and feasible downstream processes.

Do not imply that reuse is always better than recycling. A safe, technically suitable and economically justified recycling pathway can be preferable to an unviable reuse pathway. An unsafe battery must not be directed to reuse simply because the economics appear attractive.

### Section 6: Network participants

Explain how different participants collaborate through ChakraSetu.

Show:

- Originators and workshops.
- Buyers and aggregators.
- Transporters.
- Refurbishers and remanufacturers.
- Second-life operators.
- Recyclers and specialist treatment facilities.
- Network operators and managers.

Explain that each organization can have multiple roles and that its profile declares the chemistries, battery conditions, activities, geographical areas, and handling requirements it supports.

Show how the platform matches batteries to capable organizations rather than treating every buyer or transporter as interchangeable.

Link to the existing onboarding or profile experience where appropriate.

### Section 7: Sustainability and circular impact

Build a visual narrative explaining how ChakraSetu can support circularity.

Illustrate the material and value chain:

EV battery → inspection → continued use or repair where feasible → second-life application where justified → material recovery through recycling when required.

Explain the intended benefits:

- Better identification of batteries suitable for further use.
- Less dependence on incomplete or informal information.
- Improved matching between battery condition and downstream capabilities.
- More effective coordination between workshops and specialized organizations.
- Better visibility into the movement and eventual disposition of batteries.
- Support for recovery of useful materials and avoidance of inappropriate routing.

Do not claim that a specific quantity of emissions, money, or battery waste has already been saved unless the repository contains verified evidence for those claims.

If actual impact data is available, present it with an explanation of its source and calculation method. Otherwise, describe potential benefits rather than fabricating numbers.

### Section 8: Call to action and footer

Close the page with a clear invitation to participate in the network.

Use the existing registration, login, or organization onboarding routes.

The footer should include the brand, relevant navigation, and any real contact or legal links that already exist. Do not invent official partnerships, accreditations, or institutional affiliations.

# PART B — DETAILED INTERACTIVE FLOWCHART

## 5. Required end-to-end supply-chain flow

Implement the following logical process diagram. Adapt labels to the existing product where appropriate, but preserve the actual decision stages.

### Stage 1: Battery enters the network

Originator: workshop, fleet operator, collection point, or other eligible organization.

Actions:

- Create a battery registration.
- Identify the battery or batch.
- Enter the available specifications.
- Report its current condition and reason for removal.
- Enter any available inspection and diagnostic measurements.
- Select the Perceived Battery Safety level.
- Upload optional supporting documents.
- Add any other useful information.

The flowchart must explicitly show that complete historical or technical information is not required when it is genuinely unavailable.

### Stage 2: Submission and registration review

The originator submits the registration.

The system validates genuinely required fields, file restrictions, and permissions.

The registration enters Pending Review.

The network operator or manager reviews the registration. Ordinary registration approval is distinct from specialist safety assessment and formal technical qualification.

Possible outcomes:

- Approved for participation in the coordination workflow.
- Additional information requested.
- Referred for specialist assessment.
- Rejected, with a recorded reason.

Do not show pending registrations as approved resources available for ordinary downstream matching.

### Stage 3: Initial condition and safety assessment

Once appropriate for evaluation, the system considers the available evidence:

- PBS level.
- Physical condition and reported hazards.
- SoH and other diagnostic data where available.
- Chemistry and battery category.
- Inspection results.
- Missing or unreliable information.
- Any contradictory observations.

The system must not invent missing measurements.

Show a branch for insufficient evidence. It should lead to a request for appropriate additional tests or specialist assessment, rather than an automatic rejection or fabricated prediction.

### Stage 4: Safety-routing decision

The flowchart must show the five PBS levels.

L1 — Low apparent concern: ordinary matching may proceed when all other requirements are met.

L2 — Minor concerns: ordinary matching may proceed when the recipient's capabilities cover the reported condition.

L3 — Elevated concern or uncertainty: restrict matching to appropriately capable organizations and request further assessment when needed.

L4 — High safety concern: restrict ordinary routing and require network-operator review before dispatch to an appropriate specialist.

L5 — Critical hazard suspected: disable ordinary marketplace matching and routine dispatch. Escalate to qualified emergency or dangerous-goods personnel for appropriate handling instructions.

Explicitly state in the relevant node details that PBS is an originator-reported preliminary assessment, not a safety certification.

The selected level must not be the sole determinant of suitability. Explicit reports of critical hazards must take precedence over an inconsistent low-concern selection.

### Stage 5: Technical pathway eligibility

For batteries that can proceed to pathway evaluation, assess:

- Continued automotive use.
- Refurbishment or remanufacturing.
- Second-life applications.
- Recycling and material recovery.
- Specialist assessment or additional diagnostic testing.

The rules engine must consider the availability and reliability of measurements, the relevant application's requirements, battery condition, and repairability.

Use an explicit SoH screening policy, with the initial configurable defaults described in Part C. Do not make it a universal substitute for detailed qualification.

A battery may remain in the decision process with incomplete measurements, but its recommendation must reflect the resulting uncertainty.

### Stage 6: Organization capability matching

Identify candidate organizations for the specific activity.

Check:

- Battery chemistry.
- Battery category.
- Reported condition.
- PBS level and safety-handling requirements.
- Role-specific capabilities.
- Required qualifications and authorizations.
- Service area and logistics.
- Available operational capacity.

The transporter's capabilities must be assessed separately from the recipient's processing capabilities.

For a multi-stage route, the system must check whether the entire proposed chain is viable: for example, collection, appropriate transport, specialist assessment, and downstream processing.

A suitable recycler that cannot safely receive the battery directly is not automatically a feasible immediate destination.

If no suitable participant or safe route is available, the battery remains on hold pending further assessment or a feasible route.

### Stage 7: Economic pathway comparison

After safety and technical eligibility are established, compare the feasible pathways economically.

Show the relevant income, costs, assumptions, and uncertainty.

Possible inputs include:

- Purchase or recovery offers.
- Repair and refurbishment cost estimates.
- Diagnostic and requalification costs.
- Collection and transportation costs.
- Second-life integration and installation costs.
- Expected service life and useful performance.
- Warranty, maintenance, and risk allowances.
- Processing or treatment charges.
- Recycling value or recovery offers.
- Any applicable incentives that have been verified and are relevant to the transaction.

Only use actual available offers, organization-provided charges, recorded measurements, and explicitly configured assumptions. Do not silently invent prices or simulate real market data as if it were verified.

If economic information is insufficient, show which inputs are missing and request quotes or mark the economic result as provisional.

### Stage 8: Recommendation

The system produces:

- Recommended feasible pathway.
- Other feasible alternatives.
- Estimated net economic outcome where sufficient data exists.
- Main factors affecting the recommendation.
- Rules passed and rules failed.
- Measurements and information used.
- Missing information that could change the result.
- Applicable safety or technical restrictions.
- Suggested next action.

The selected route must be explainable. A reviewer and originator must be able to understand why it was selected.

### Stage 9: Coordination and downstream disposition

Once the pathway is accepted and all required checks are completed:

- Coordinate collection and transport where applicable.
- Confirm the downstream recipient.
- Preserve transaction and transfer authorization requirements.
- Track relevant handoffs and status changes.
- Record the eventual disposition when it becomes available.

Possible final outcomes include continued use, successful refurbishment, second-life deployment, or recycling and material recovery.

Where appropriate, make the resulting information available for traceability and future circularity reporting.

Do not claim that physical transfers or material recovery have occurred merely because a recommendation was generated.

## 6. Interactive diagram behavior

The flowchart must support actual interaction, not just decorative animation.

Implement:

- Clickable, keyboard-accessible stages.
- Contextual descriptions for every important step.
- Animated connectors between stages.
- Conditional branches for safety levels and pathway decisions.
- Highlighting of the relevant path when a node or scenario is selected.
- A clear indication of which stages are automated and which require human action.
- Zoom, reset, and navigation controls when using a large diagram canvas.
- Responsive layout for desktop, tablet, and mobile.
- A clearly visible way to explore the rules behind each decision.

Provide an interactive pathway explorer within or immediately alongside the flowchart.

The visitor should be able to choose an illustrative battery scenario and observe how changing its available information alters the feasible routes.

For example:

- A battery with suitable health measurements and no reported safety concern.
- A degraded but potentially repairable battery.
- A battery with missing diagnostic information.
- A battery presenting a high safety concern.

These example scenarios must be explicitly labelled as illustrative. They must not be saved into production records or presented as actual customer data.

When a scenario is selected, highlight the corresponding branch and explain the relevant conditions, required checks, and possible outcomes.

The flowchart should be visually impressive without becoming unreadable. If the complete diagram is too large for a single viewport, use a full-width interactive canvas with navigation and contextual details, supported by scroll-based sections that explain the same process in sequence.

## 7. Visual quality and motion

Make the flowchart a visual centerpiece.

Use clear typography, balanced spacing, meaningful colors, and visually distinct node types for:

- Human actors.
- Data-entry and inspection steps.
- Automated eligibility rules.
- Safety gates.
- Economic comparisons.
- Organization matching.
- Downstream pathways.
- Approval and exception handling.

Animate path transitions and connections to explain the system's behavior.

Use subtle scroll-reveal animations where appropriate. Avoid animations that prevent users from reading text or following the process.

Respect reduced-motion preferences and ensure that animations do not interfere with keyboard access or touch interactions.

Do not use a giant static screenshot of a flowchart. The actual nodes, connectors, state changes, and detail panels must be implemented as working interface components.

# PART C — IMPLEMENT THE RULE-BASED PATHWAY RECOMMENDATION ENGINE

## 8. Core architecture

Implement an explicit deterministic rules engine within the existing application.

The engine must use structured inputs and configured rules rather than relying on an LLM or opaque machine-learning classifier to choose a battery's disposition.

The rules engine should have four logically separate stages:

1. Safety and mandatory compliance gates.
2. Technical pathway eligibility.
3. Organization and logistics feasibility.
4. Economic comparison of the remaining feasible pathways.

The order is mandatory. Economic attractiveness must never override a failed safety gate, required authorization, or technical disqualification.

The engine should return a structured result that can be displayed consistently in the battery record, operator dashboard, matching interface, and interactive homepage demonstration.

Keep the decision rules centralized, versioned, testable, and configurable rather than scattering inconsistent thresholds across frontend components.

Use the existing backend language and architecture. Do not implement one set of decision rules in frontend JavaScript and a different set in the backend.

The backend must be authoritative. The homepage should call the real decision engine where appropriate or use the same deterministic rule implementation with a clearly separate, non-persistent demonstration scenario. Do not maintain a second, inconsistent copy of the rules for marketing purposes.

## 9. Input data and evidence quality

The decision engine may use:

### Battery data

- Battery category.
- Vehicle/application type.
- Chemistry.
- Manufacturer and model, where known.
- Age and manufacturing date, where known.
- Rated voltage, capacity, and energy.
- SoH and SoC, where available.
- Measured capacity.
- Pack and module/cell voltages.
- Internal resistance or impedance.
- Cell/module imbalance.
- Temperature observations.
- BMS fault codes.
- Physical inspection findings.
- Repairability assessment.
- Accident, fire, flood, or other history, if reported.
- PBS and additional safety observations.
- Available test reports and supporting documentation.

### Organization data

- Accepted battery chemistries and categories.
- Maximum declared PBS level, subject to role and qualification checks.
- Accepted conditions.
- Testing, repair, repurposing, processing, or recycling capabilities.
- Specialist handling capabilities.
- Collection and transport capabilities.
- Service area.
- Operational capacity.
- Required authorizations and qualification status.
- Available prices, fees, and offers.

### Economic data

- Actual offers from eligible downstream organizations.
- Transport charges.
- Testing and assessment charges.
- Repair and refurbishment estimates.
- Repurposing and integration costs.
- Processing fees.
- Recycling offers or recovery values.
- Applicable maintenance, warranty, and risk allowances.
- Expected application life and value when sufficiently supported.

Record the source and date of material measurements, prices, quotes, and assumptions where possible.

Every input must have an explicit state such as measured, reported, estimated, unavailable, or not applicable when that distinction is relevant.

Do not interpret a missing value as a zero, a normal result, or a successful test.

## 10. Rule 1: Safety and critical-hazard gates

Implement a prioritized safety gate.

### L1 and L2

Ordinary pathway evaluation can proceed when the available evidence is adequate and all other applicable checks pass.

These levels do not constitute formal safety certification.

### L3

Evaluate the identified uncertainty and reported condition. Restrict matching to organizations capable of performing the required assessment or handling the relevant condition.

### L4

Restrict ordinary marketplace matching. Require the appropriate operator review and qualified specialist route before dispatch.

### L5

Disable ordinary marketplace matching and routine dispatch. Require controlled escalation to qualified personnel for appropriate instructions.

### Contradictory evidence

Where a low PBS level conflicts with explicitly reported serious hazards, the serious hazard report must trigger the appropriate review.

Where the safety condition is unknown or critical information is unavailable, do not assign an implicit safe classification.

A safety gate must produce an explicit result, such as:

- Eligible for ordinary pathway evaluation.
- Restricted to specified capable participants.
- Requires specialist assessment.
- Hold for safety clarification.

The system must not automatically interpret every flagged battery as a recycling candidate.

Store a reason for every restriction or escalation.

## 11. Rule 2: Technical pathway eligibility

The initial configuration may use the following SoH screening bands as preliminary defaults:

- SoH ≥ 80%: assess continued automotive use or refurbishment, subject to application requirements and all other checks.
- 60% ≤ SoH < 80%: assess refurbishment, second-life applications, and possible module-level recovery.
- SoH < 60%: assess repairability, module/cell recovery, second-life suitability, and recycling with particular attention to application-specific requirements.
- SoH unavailable or unreliable: do not make an SoH-based decision. Request suitable testing or use other valid evidence while clearly identifying the limitation.

These are configurable screening parameters, not universal scientific boundaries, mandatory standards, or automatic disposal rules.

The system must never implement a rule such as:

"SoH below 60% → automatically recycle."

Similarly, a high SoH must not override evidence of serious damage or an otherwise failed safety requirement.

### Continued automotive use

Consider the route only when:

- The safety gate permits evaluation.
- Relevant vehicle and application requirements can be met.
- The available technical evidence supports the decision.
- Required inspection, repair, or validation steps can be completed.

### Refurbishment

Consider refurbishment when:

- A fault or deficiency is sufficiently identified.
- Repair is technically plausible.
- Suitable parts, expertise, and facilities are available.
- The resulting battery can be requalified.
- The post-repair costs and risks can be assessed.

Refurbishment should not be treated as successful merely because a part can be replaced.

### Second-life use

Consider second-life use when:

- The safety requirements for the intended application can be met.
- The battery can meet the application's energy, power, efficiency, and reliability requirements.
- Remaining useful life is expected to be adequate.
- Required testing and integration are feasible.
- A suitable operator is available.

Do not automatically equate 80% SoH with suitability for automotive use or a lower SoH with suitability for stationary storage.

### Recycling

Consider recycling when reuse and refurbishment are unsafe, infeasible, unavailable, or unjustified under the applicable constraints and economics.

The precise final route must depend on the available evidence and permissible treatment options.

### Insufficient evidence

If a necessary measurement is unavailable, distinguish:

- Pathways that can still be assessed.
- Pathways that require additional measurements.
- Pathways that are excluded because of a known constraint.

Return an indeterminate or conditional result when the available information cannot justify a reliable recommendation.

Where possible, recommend the next useful inspection or measurement, rather than requiring every possible test on every battery.

## 12. Rule 3: Organization and logistics feasibility

For each pathway, identify whether a feasible downstream chain exists.

Examples:

- Continued automotive use requires an eligible vehicle/application and appropriate technical validation.
- Refurbishment requires a capable refurbisher, compatible parts where needed, and post-repair qualification.
- Second-life use requires a capable operator, appropriate application requirements, and necessary integration.
- Recycling requires an eligible recycler and an appropriate handling and transport arrangement.

Evaluate transport independently from destination processing.

A downstream organization's capability to process a battery does not prove that a transporter can move it under the circumstances involved.

Enforce role-specific capabilities and any required qualifications or authorizations.

Exclude routes that violate required safety, legal, or capability constraints. Record the exact reason.

If no feasible downstream route is available, report that outcome explicitly.

# PART D — ECONOMIC PATHWAY COMPARISON

## 13. Design an actual economic decision mechanism

This is a core product requirement.

ChakraSetu must not merely recommend a route based on SoH or show a few generic estimates. It should determine which feasible pathway has the strongest economic case using actual available commercial information and transparently stated assumptions.

The system must first establish which routes are permissible and technically feasible. It should then compare the economics of those routes.

Do not run an economic ranking before applying the safety and technical gates.

## 14. Pathway-specific economic models

For every feasible pathway, calculate a consistent economic measure. Use net present value where the necessary projected cash flows are available. For short-term transactions, an estimated net transaction value may be sufficient.

### A. Continued automotive use

Where an eligible application exists, estimate the value of continued service against a clearly defined alternative, such as replacement or an alternative supply option.

Include relevant diagnostic, repair, requalification, transportation, and expected maintenance costs.

Do not compare an automotive resale price to a second-life lifetime revenue figure without normalizing the economic basis and time horizon.

### B. Refurbishment

A simplified initial model may be:

Refurbishment net value = expected post-refurbishment sale or use value − diagnostics − repair parts − labor − requalification − transport − expected warranty/maintenance costs − applicable risk allowance.

Use actual offers or explicit estimates for expected value. Where uncertainty is material, display a range or mark the result provisional.

### C. Second-life application

A simplified initial model may be:

Second-life net value = present value of expected application value or revenues − assessment/testing − transport − repurposing and integration − installation − maintenance − warranty/risk allowance − expected end-of-service treatment costs.

Use application-specific operating assumptions and expected remaining useful life where available.

Do not assume a second-life battery generates a positive economic return merely because some capacity remains.

### D. Recycling

A simplified initial model may be:

Recycling net value = actual recycling offer or verified net material recovery value − collection − transport − packaging and required handling − treatment/processing charges − other applicable costs.

Distinguish an actual recycler's offer from a speculative estimate of recovered material value.

Do not invent material recovery prices or unverified incentives.

## 15. Common comparison rules

The economic comparison must:

- Use the same currency and a documented accounting basis.
- Distinguish revenue, purchase value, costs, and incentives.
- Avoid double-counting costs.
- Use comparable time horizons where appropriate.
- Record whether values are actual quotations, organization-provided estimates, or configurable assumptions.
- Account for the cost of essential testing and qualification.
- Include the relevant logistics and handling costs.
- Account for degradation, maintenance, warranty, and end-of-service costs when relevant.
- Exclude pathways that failed mandatory safety or eligibility checks.

For any route \(j\), the engine may calculate:

\[
V_j = \text{Present value of expected benefits}_j
      - \text{Present value of expected costs}_j
\]

For a one-time transaction with no meaningful future cash flows, use the comparable net transaction value instead of forcing an unnecessary NPV calculation.

Use a configurable cost and revenue model. Do not hard-code market prices or present arbitrary economic coefficients as universally accurate.

## 16. Where prices and estimates come from

Inspect the existing organization and transaction models first.

Where available, use:

- Buyer purchase offers.
- Refurbisher repair quotes and expected purchase/resale values.
- Second-life operator offers and application-specific estimates.
- Recycler offers and charges.
- Transporter rates.
- Assessment and testing costs.
- Relevant transaction history where it is reliable and permitted for the use.
- Authorized, documented administrative assumptions.

If existing profiles do not store the required commercial information, extend them only as necessary.

Provide an appropriate way to record or retrieve quotes, prices, fees, and their validity periods. Reuse an existing quotation or offer mechanism if one exists.

Do not assume that a buyer's technical capability automatically implies a known purchase price.

If economic data is missing, return a result such as:

"Economic recommendation unavailable: transport costs and downstream offers are missing."

Where technically appropriate, the system may still identify feasible pathways and display partial cost information.

It must not invent a precise financial recommendation simply to ensure that every battery receives one.

If some values are estimates, label the outcome provisional and show the assumptions that could change the ranking.

## 17. Final recommendation and alternatives

Return a structured decision object that supports the UI and audit trail.

It should include, where applicable:

- Selected recommended pathway.
- Feasibility status.
- Other eligible pathways.
- Excluded pathways.
- Economic value or range for each comparable eligible route.
- Currency, comparison basis, and time horizon.
- Source of material financial inputs.
- Rules evaluated and their results.
- Main factors supporting the recommendation.
- Missing information affecting the result.
- Safety restrictions and qualification requirements.
- Required additional tests.
- Date of calculation and ruleset version.
- Whether the result is final, conditional, or provisional.

Provide a clear explanation such as:

"Refurbishment is currently preferred because a repairable fault has been identified, a capable refurbisher is available, and the available quote indicates a higher estimated net value than the eligible alternatives. This recommendation depends on successful post-repair testing."

This example is illustrative. The actual explanation must be generated from the rules evaluated and the data available for the specific battery.

Do not generate generic explanations that are disconnected from the actual decision.

If two or more routes are economically similar within the uncertainty of their estimates, say so rather than presenting a false level of precision.

# PART E — INTEGRATE THE ENGINE INTO THE APPLICATION

## 18. Registration integration

After a battery registration is submitted and is eligible for evaluation, the system should use the available fields to begin the decision process.

Respect the existing operator-approval requirement.

The platform may perform preliminary validations or calculate a provisional result while a registration is pending, but a provisional result must not silently grant approved marketplace status.

Once the required approval and data conditions are satisfied, the engine should evaluate feasible pathways and eligible organizations.

The user must be able to update missing information and rerun the evaluation when appropriate.

Changes to important inputs, prices, quotes, PBS, or organization capabilities must trigger recalculation when they affect the existing recommendation.

Store enough information to explain how the previous recommendation was generated. Do not simply overwrite all prior decision results without an appropriate audit or versioning strategy.

## 19. Decision interface for originators and operators

Create a well-designed results interface for authorized users showing:

- Recommended pathway.
- Current evaluation state.
- Feasible alternatives.
- Main reasons for the recommendation.
- Safety restrictions.
- Economic comparison.
- Missing information.
- Additional tests or quotations that would improve the recommendation.
- Eligible downstream organizations.
- Relevant transport and processing constraints.

Use clear terminology. Do not expose raw internal rule-engine JSON to ordinary users.

Authorized network operators should be able to inspect rule outcomes, missing evidence, the data used for calculations, and relevant decision history.

If a reviewer overrides a recommendation, record the override, user, reason, and time. Do not silently alter the engine's original output.

An LLM may help summarize a rule result in user-friendly language if the existing architecture supports it, but it must not invent data, change rule outcomes, bypass gates, or determine the pathway.

# PART F — HOMEPAGE DEMONSTRATION MODE

## 20. Connect the visual flowchart to the real decision logic

The homepage must demonstrate that ChakraSetu is an operating concept with a defined decision process, not merely a supply-chain illustration.

Implement an interactive pathway explorer using a small, curated set of clearly labelled illustrative scenarios.

The visitor should be able to select a scenario or adjust selected inputs, such as:

- SoH.
- PBS level.
- Whether an identified fault is repairable.
- Whether the required measurements are available.
- Whether a suitable refurbisher or second-life operator exists.
- Whether relevant quotations and logistics costs are available.

Only expose inputs that are meaningful to the selected scenario. Avoid building a second complicated battery-registration form into the homepage.

When the user changes inputs:

1. Evaluate the safety restrictions.
2. Evaluate technical pathway eligibility.
3. Evaluate organization and logistics feasibility.
4. Compare economic outcomes when sufficient data is available.
5. Update the highlighted flowchart branch.
6. Display the resulting eligible pathways, exclusions, and explanation.

Use the actual backend decision engine where appropriate, or an isolated demonstration adapter that invokes the same deterministic rule definitions.

Demonstration inputs must never create or modify production battery records.

Label illustrative prices, sample measurements, and hypothetical organization offers explicitly. Do not present them as verified live marketplace data.

If the homepage cannot safely access the backend decision service anonymously, implement the demonstration using local illustrative inputs and the same rule specification, or provide a non-persistent demonstration endpoint with suitable controls.

The homepage must not expose confidential organization profiles, private battery registrations, transaction information, or uploaded documents.

# PART G — SUSTAINABILITY AND CIRCULARITY REPORTING

## 21. Make the sustainability story credible

The homepage should explain the expected sustainability benefits of better routing and circularity.

Where actual data exists, build meaningful reporting for outcomes such as:

- Batteries continued in use.
- Batteries successfully refurbished.
- Batteries deployed in second-life applications.
- Batteries sent to recycling.
- Batteries awaiting assessment or disposition.
- Confirmed quantities processed, where the relevant data is recorded.

Distinguish registrations, recommendations, approved routes, completed handoffs, and confirmed final outcomes.

Do not count a battery as refurbished merely because refurbishment was recommended. Do not count recycling as completed merely because a recycler was selected.

If environmental calculations are introduced, define the baseline, assumptions, units, and calculation methodology. Avoid claiming that a given pathway always reduces emissions without a defensible basis.

Do not fabricate impact counters to improve the appearance of the landing page.

Where real operational data is not yet available, use an explanatory illustration and label it clearly rather than displaying fake live metrics.

# PART H — QUALITY, ACCESSIBILITY, AND PERFORMANCE

## 22. Visual and interaction requirements

The final homepage should have:

- A coherent visual identity.
- Strong typographic hierarchy.
- A compelling initial viewport.
- A prominent interactive supply-chain flowchart.
- Clear visual distinctions between actors, automated rules, human approvals, and pathway outcomes.
- Smooth transitions and purposeful animation.
- Well-designed hover, focus, selection, loading, and error states.
- Responsive layouts and mobile-appropriate flowchart interaction.
- Accessible colors and text contrast.
- Keyboard-accessible diagram nodes and controls.
- Reduced-motion support.
- Clear loading and failure states when backend functionality is unavailable.

Use the current animation framework or CSS/SVG transitions where sufficient. Do not add unnecessary libraries or animations that negatively affect performance.

The flowchart must remain understandable without animation, and all important content must remain available to users who disable motion.

## 23. Maintain consistency across the product

The homepage, registration form, PBS display, decision engine, capability profiles, operator dashboard, and matching interface must share the same terminology and rule definitions.

For example:

- Use the same five PBS levels everywhere.
- Use consistent labels for pathway states.
- Ensure the homepage's decision demonstration does not contradict the actual backend logic.
- Keep profile capability requirements consistent with matching rules.
- Ensure economic explanations reflect the actual comparison that was performed.

Avoid maintaining separate hard-coded decision policies within individual UI components.

# PART I — TESTING AND ACCEPTANCE CRITERIA

## 24. Required automated tests

Implement or update tests covering at least the following.

### Homepage

1. The public homepage loads without authentication where the existing application permits public routes.
2. Existing login, onboarding, and dashboard navigation continue to work.
3. The flowchart displays all major stages and branches.
4. Important nodes can be selected and explored.
5. Diagram interactions work with keyboard navigation.
6. The flowchart remains usable on smaller screens.
7. Reduced-motion preferences are respected.
8. The homepage does not expose private battery or organization information.

### Safety and technical rules

9. L1 and L2 batteries proceed to ordinary eligibility checks when all other requirements are satisfied.
10. L3 respects the relevant capability and assessment constraints.
11. L4 follows the required restricted-review workflow.
12. L5 does not enter ordinary marketplace matching or routine dispatch.
13. Contradictory critical-hazard observations prevent unsafe ordinary routing.
14. Missing SoH does not get silently replaced with zero or assumed normal.
15. SoH screening thresholds are configurable.
16. A low SoH does not automatically force recycling.
17. A high SoH does not override critical safety concerns.
18. An insufficient-evidence result is distinct from a negative pathway result.

### Organization matching

19. Chemistry, category, PBS, reported condition, and required capabilities are evaluated.
20. Transport and processing capabilities are independently assessed.
21. Required missing or expired qualifications prevent the corresponding restricted activity.
22. No suitable organization leads to a clear hold or reassessment outcome.

### Economic engine

23. Only feasible pathways are economically ranked.
24. Safety restrictions override economic attractiveness.
25. Net values are computed from the configured inputs and correct cost/revenue components.
26. Missing prices do not produce fabricated financial recommendations.
27. Estimated and actual quotations remain distinguishable.
28. Comparisons use a consistent financial basis.
29. Material input changes trigger recalculation when required.
30. Recommendations include the rules, assumptions, and missing evidence that materially affect the result.
31. Illustrative homepage scenarios do not modify production data.

### Integration and permissions

32. Registration approval remains distinct from technical qualification.
33. Pending registrations do not appear as approved downstream resources.
34. Unauthorized users cannot access or modify restricted registrations or decision results.
35. The backend enforces the authoritative rules.
36. Existing transfer and transaction authorization controls remain effective.
37. Recommendation overrides are recorded in the audit trail.

Run relevant tests, builds, lint checks, and type checks. Correct regressions introduced by the implementation.

Do not report a successful build or passing tests unless the commands were actually executed and passed.

# PART J — IMPLEMENTATION INSTRUCTIONS

## 25. Build it, do not merely describe it

Implement the complete change in the existing repository.

Proceed in a controlled order:

1. Inspect the codebase and map the current architecture.
2. Identify the existing home route and design system.
3. Identify or implement the centralized rule engine.
4. Integrate the decision engine with battery registration and organization capabilities.
5. Implement the actual pathway-feasibility and economic-comparison logic.
6. Build the interactive homepage and complete supply-chain flowchart.
7. Connect the homepage demonstration to the same decision logic.
8. Integrate the results with the existing dashboard and matching workflow.
9. Add tests and validate the complete flow.
10. Run the application and inspect the result where the environment permits.

Do not stop after the frontend is complete. The interactive demonstration must reflect real rule outcomes, and the operational application must use the same rules.

Do not create a disconnected prototype filled with fictional prices, fake customers, fabricated sustainability metrics, or hard-coded recommendations presented as live results.

Use clearly labelled sample scenarios where actual data is unavailable.

When complete, provide an implementation report that states:

- What homepage sections were implemented.
- How the interactive flowchart works.
- How the real recommendation engine is invoked.
- Which safety, technical, capability, and economic rules were implemented.
- Where prices, quotes, costs, and assumptions originate.
- What changes were made to the database, APIs, and authorization rules.
- Which tests, builds, and type checks actually passed.
- Any limitations that remain.

## Final definition of success

A visitor should be able to scroll through the ChakraSetu homepage, understand the problem and the platform, explore the entire EV battery circularity supply chain through a large and interactive flowchart, and experiment with representative battery scenarios to see how the decision rules change the feasible route.

An actual originator should be able to register a battery with incomplete but available information. ChakraSetu should then evaluate safety constraints, technical suitability, downstream organizational capabilities, and economic feasibility using explicit rules and real available inputs.

The final result should look like a polished, compelling product suitable for a hackathon presentation while behaving like a coherent application that can evolve into real operational infrastructure.