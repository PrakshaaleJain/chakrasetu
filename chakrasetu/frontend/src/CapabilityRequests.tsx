import { MultiChoices, SafetyScopeEditor } from "./SafetyScopeEditor";
import {
  blankSafety,
  chemistryOptions,
  categoryOptions,
  conditionOptions,
} from "./registrationTypes";
import type { SafetyScope } from "./registrationTypes";
import { VerificationRequestRow } from "./VerificationRequest";
import { useState } from "react";
import { useResource } from "./api";
import type { Actor, Action } from "./types";
import type {
  OrganisationProfile,
  VerificationRequest,
  CapabilitySummary,
} from "./organisationTypes";
import { Panel, Badge, Field, Empty, human, date } from "./components";
import { hasRole } from "./navigation";
const OPERATIONS = [
  "ASSESSMENT",
  "REFURBISHMENT",
  "REPURPOSING",
  "INTEGRATION",
  "DISMANTLING",
  "RECYCLING",
  "PROCESSING",
  "REFINING",
  "MANUFACTURING",
];
const ROLES = [
  "ORIGINATOR",
  "TRANSPORTER",
  "TECHNICIAN",
  "REFURBISHER",
  "SECOND_LIFE",
  "RECYCLER",
  "PROCESSOR",
  "REFINER",
  "MANUFACTURER",
  "CUSTOMER",
  "BUYER",
  "HUB",
];
const PATHWAYS = [
  "REPAIR_REFURBISHMENT",
  "SECOND_LIFE_ASSESSMENT",
  "RECYCLING",
  "QUALIFIED_REVIEW",
];
const split = (s: string) =>
  s
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean);
export function CapabilityRequests({
  actor,
  profile,
  version,
  action,
}: {
  actor: Actor;
  profile: OrganisationProfile;
  version: number;
  action: Action;
}) {
  const [safety, setSafety] = useState<SafetyScope>({ ...blankSafety });
  const [show, setShow] = useState(false),
    [kind, setKind] = useState("ROLE"),
    [requestAction, setRequestAction] = useState("ADD"),
    [target, setTarget] = useState(""),
    [facility, setFacility] = useState(""),
    [operation, setOperation] = useState(OPERATIONS[0]),
    [pathway, setPathway] = useState(PATHWAYS[0]),
    [role, setRole] = useState(ROLES[0]),
    [capacity, setCapacity] = useState(""),
    [chem, setChem] = useState(""),
    [formats, setFormats] = useState(""),
    [conditions, setConditions] = useState(""),
    [categories, setCategories] = useState(""),
    [handling, setHandling] = useState("ORDINARY"),
    [lat, setLat] = useState(""),
    [lng, setLng] = useState(""),
    [radius, setRadius] = useState(""),
    [description, setDescription] = useState(""),
    [officialName, setOfficialName] = useState(""),
    [confirmation, setConfirmation] = useState("");
  const { data: requests, error } = useResource<VerificationRequest[]>(
    "/capability-requests",
    version,
    [],
  );
  function edit(c: CapabilitySummary, actionName: string) {
    setShow(true);
    setKind(c.kind);
    setTarget(c.id);
    setFacility(c.facility_id || "");
    setRequestAction(actionName);
    setOperation(c.kind === "OPERATION" ? c.name : OPERATIONS[0]);
    setPathway(c.kind === "PATHWAY" ? c.name : PATHWAYS[0]);
    setSafety({
      ...blankSafety,
      ...c.scope.declared_safety,
      ...c.scope.verified_safety,
    });
    setCapacity(c.scope.capacity_kg == null ? "" : String(c.scope.capacity_kg));
    setChem(c.scope.chemistries.join(","));
    setFormats(c.scope.formats.join(","));
    setConditions(c.scope.conditions?.join(",") || "");
    setLat(c.scope.center ? String(c.scope.center[0]) : "");
    setLng(c.scope.center ? String(c.scope.center[1]) : "");
    setRadius(c.scope.radius_km == null ? "" : String(c.scope.radius_km));
    setCategories(c.scope.material_categories.join(","));
    setHandling(c.scope.handling_scope || "ORDINARY");
    setDescription("");
  }
  return (
    <>
      <Panel
        title="Roles & Capabilities"
        aside={
          <button
            onClick={() => {
              setShow(!show);
              setTarget("");
              setRequestAction("ADD");
            }}
          >
            Add a Capability or Role
          </button>
        }
      >
        <p>
          Request an operational role or facility scope here. Existing approvals
          stay in place until a review decision is recorded.
        </p>
        <div className="actions">
          {profile.roles.map((r) => (
            <span key={r}>
              <Badge value={r} />
              <button
                className="text-button"
                onClick={() => {
                  setShow(true);
                  setKind("ROLE");
                  setRole(r);
                  setRequestAction("REMOVE");
                  setTarget("");
                }}
              >
                Request removal
              </button>
            </span>
          ))}
        </div>
        {profile.capabilities.map((c) => (
          <div className="evidence" key={c.id}>
            <div className="card-line">
              <strong>{human(c.name)}</strong>
              <Badge value={c.status} />
            </div>
            <p>
              {profile.facilities.find((f) => f.id === c.facility_id)?.name ||
                "Organisation-wide"}{" "}
              · {c.scope.chemistries.join(", ")}{" "}
              {c.scope.material_categories.join(", ")}
            </p>
            <small>
              Capacity {c.scope.capacity_kg ?? "Unknown"} kg · Updated{" "}
              {date(c.updated_at)}
            </small>
            <div className="actions">
              <button onClick={() => edit(c, "MODIFY")}>
                Edit Capability Details
              </button>
              <button onClick={() => edit(c, "MODIFY")}>
                Request Verification
              </button>
              <button onClick={() => edit(c, "REMOVE")}>Request Removal</button>
            </div>
          </div>
        ))}
        {!profile.capabilities.length && (
          <Empty>No capabilities have been added yet.</Empty>
        )}
      </Panel>
      {show && (
        <Panel
          title={
            requestAction === "REMOVE"
              ? "Request Capability Removal"
              : "Capability Verification Request"
          }
        >
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              const result = await action("/capability-requests", {
                kind,
                action: requestAction,
                target_id: target || null,
                facility_id: facility || null,
                requested_scope: {
                  safety: ["OPERATION", "PATHWAY", "TRANSPORT"].includes(kind)
                    ? safety
                    : null,
                  role: kind === "ROLE" ? role : null,
                  operation: kind === "OPERATION" ? operation : null,
                  pathway: kind === "PATHWAY" ? pathway : null,
                  capacity_kg: capacity === "" ? null : Number(capacity),
                  chemistries: split(chem),
                  formats: split(formats),
                  conditions: split(conditions),
                  material_categories: split(categories),
                  handling_scope: handling,
                  center:
                    kind === "TRANSPORT" && lat !== "" && lng !== ""
                      ? [Number(lat), Number(lng)]
                      : null,
                  radius_km: radius === "" ? null : Number(radius),
                  description,
                  official_name:
                    kind === "IDENTITY" && officialName ? officialName : null,
                },
              });
              if (result) {
                setConfirmation(result.message);
                setShow(false);
              }
            }}
          >
            <div className="form-grid">
              <Field label="Request type">
                <select
                  value={kind}
                  disabled={!!target}
                  onChange={(e) => setKind(e.target.value)}
                >
                  {[
                    "ROLE",
                    "OPERATION",
                    "PATHWAY",
                    "TRANSPORT",
                    "IDENTITY",
                    "FACILITY",
                  ].map((x) => (
                    <option value={x} key={x}>
                      {human(x)}
                    </option>
                  ))}
                </select>
              </Field>
              {["OPERATION", "PATHWAY", "FACILITY"].includes(kind) && (
                <Field label="Applicable facility">
                  <select
                    required
                    value={facility}
                    onChange={(e) => setFacility(e.target.value)}
                  >
                    <option value="">Choose your facility</option>
                    {profile.facilities.map((f) => (
                      <option key={f.id} value={f.id}>
                        {f.name}
                      </option>
                    ))}
                  </select>
                </Field>
              )}
              {kind === "IDENTITY" && (
                <Field label="Requested official organisation name">
                  <input
                    value={officialName}
                    minLength={2}
                    maxLength={200}
                    onChange={(e) => setOfficialName(e.target.value)}
                    placeholder={profile.name}
                  />
                </Field>
              )}
              {kind === "ROLE" && (
                <Field label="Operational role">
                  <select
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                  >
                    {ROLES.map((x) => (
                      <option key={x} value={x}>
                        {human(x)}
                      </option>
                    ))}
                  </select>
                </Field>
              )}
              {kind === "OPERATION" && (
                <Field label="Operation">
                  <select
                    value={operation}
                    disabled={!!target}
                    onChange={(e) => setOperation(e.target.value)}
                  >
                    {OPERATIONS.map((x) => (
                      <option value={x} key={x}>
                        {human(x)}
                      </option>
                    ))}
                  </select>
                </Field>
              )}
              {kind === "PATHWAY" && (
                <Field label="Battery pathway">
                  <select
                    value={pathway}
                    disabled={!!target}
                    onChange={(e) => setPathway(e.target.value)}
                  >
                    {PATHWAYS.map((x) => (
                      <option value={x} key={x}>
                        {human(x)}
                      </option>
                    ))}
                  </select>
                </Field>
              )}
              {["OPERATION", "PATHWAY", "TRANSPORT"].includes(kind) && (
                <>
                  <Field label="Requested capacity · kg">
                    <input
                      type="number"
                      min="0.001"
                      step="any"
                      value={capacity}
                      onChange={(e) => setCapacity(e.target.value)}
                      required={kind !== "OPERATION"}
                    />
                  </Field>
                  <MultiChoices
                    label="Accepted battery chemistries"
                    options={chemistryOptions}
                    value={split(chem)}
                    onChange={(v) => setChem(v.join(","))}
                  />
                  <MultiChoices
                    label="Accepted battery categories"
                    options={categoryOptions}
                    value={split(formats)}
                    onChange={(v) => setFormats(v.join(","))}
                  />
                  <MultiChoices
                    label="Supported battery conditions"
                    options={conditionOptions}
                    value={split(conditions)}
                    onChange={(v) => setConditions(v.join(","))}
                  />
                  <SafetyScopeEditor
                    kind={kind}
                    scope={safety}
                    onChange={setSafety}
                  />
                  <Field label="Material categories · comma separated">
                    <input
                      value={categories}
                      onChange={(e) => setCategories(e.target.value)}
                      placeholder="BLACK_MASS, COPPER"
                    />
                  </Field>
                </>
              )}
              {["PATHWAY", "TRANSPORT"].includes(kind) && (
                <Field label="Handling scope">
                  <select
                    value={handling}
                    onChange={(e) => setHandling(e.target.value)}
                  >
                    <option value="ORDINARY">Ordinary handling</option>
                    <option value="CONTROLLED_HANDLING">
                      Controlled handling
                    </option>
                  </select>
                </Field>
              )}
              {kind === "TRANSPORT" && (
                <>
                  <Field label="Coverage centre latitude">
                    <input
                      type="number"
                      required
                      step="any"
                      min="-90"
                      max="90"
                      value={lat}
                      onChange={(e) => setLat(e.target.value)}
                    />
                  </Field>
                  <Field label="Coverage centre longitude">
                    <input
                      type="number"
                      required
                      step="any"
                      min="-180"
                      max="180"
                      value={lng}
                      onChange={(e) => setLng(e.target.value)}
                    />
                  </Field>
                  <Field label="Coverage radius · km">
                    <input
                      type="number"
                      required
                      value={radius}
                      onChange={(e) => setRadius(e.target.value)}
                    />
                  </Field>
                </>
              )}
            </div>
            <Field label="Requested scope and relevant information">
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                maxLength={4000}
              />
            </Field>
            <p className="muted">
              No document upload is required to submit. ChakraSetu will request
              supporting information if needed. The 48-hour response target does
              not mean automatic approval.
            </p>
            <div className="actions">
              <button className="primary">Submit Request</button>
              <button type="button" onClick={() => setShow(false)}>
                Cancel
              </button>
            </div>
          </form>
        </Panel>
      )}
      {confirmation && (
        <p className="success-banner" role="status">
          {confirmation}
        </p>
      )}
      <Panel
        title={
          hasRole(actor, "REVIEWER")
            ? "Capability Review Queue"
            : "Verification Requests"
        }
      >
        {error && <p role="alert">{error}</p>}
        {requests.map((r) => (
          <VerificationRequestRow
            key={r.id}
            request={r}
            reviewer={hasRole(actor, "REVIEWER")}
            own={r.organisation_id === actor.organisation_id}
            action={action}
          />
        ))}
        {!requests.length && (
          <Empty>No verification requests have been submitted yet.</Empty>
        )}
      </Panel>
    </>
  );
}
