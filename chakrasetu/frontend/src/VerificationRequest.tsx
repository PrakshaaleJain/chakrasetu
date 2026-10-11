import { displayJSON } from "./components";
import { useState, useEffect } from "react";
import { useResource } from "./api";
import type { Action } from "./types";
import type {
  OrganisationProfile,
  VerificationRequest,
} from "./organisationTypes";
import { Badge, Field, human, date } from "./components";
export function VerificationRequestRow({
  request: r,
  reviewer,
  own,
  action,
}: {
  request: VerificationRequest;
  reviewer: boolean;
  own: boolean;
  action: Action;
}) {
  const [response, setResponse] = useState(""),
    [reason, setReason] = useState(""),
    [evidence, setEvidence] = useState(""),
    [expiry, setExpiry] = useState(""),
    [decision, setDecision] = useState(
      r.status === "APPROVED" ? "SUSPENDED" : "INFORMATION_REQUESTED",
    ),
    [expanded, setExpanded] = useState(false);
  useEffect(() => {
    if (r.status === "APPROVED") setDecision("SUSPENDED");
  }, [r.status]);
  const { data: reviewedOrganisation } =
    useResource<OrganisationProfile | null>(
      reviewer ? "/organisation-profiles/" + r.organisation_id : null,
      0,
      null,
    );
  return (
    <article className="evidence" id={"request-" + r.id}>
      <div className="card-line">
        <strong>
          {human(
            String(
              r.requested_scope.role ||
                r.requested_scope.operation ||
                r.requested_scope.pathway ||
                r.kind,
            ),
          )}{" "}
          · {human(r.action)}
        </strong>
        <Badge value={r.status} />
      </div>
      <p>
        {r.requested_scope.description || "No additional description provided."}
      </p>
      <small>Updated {date(r.updated_at)}</small>
      {r.data.history.at(-1)?.reason && <p>{r.data.history.at(-1)?.reason}</p>}
      <button className="text-button" onClick={() => setExpanded(!expanded)}>
        {expanded ? "Hide" : "View"} Request & Review History
      </button>
      {expanded && (
        <>
          <pre>{displayJSON(r.requested_scope, null, 2)}</pre>
          {r.data.history.map((h, i) => (
            <p key={i}>
              <strong>{human(h.action)}</strong> · {date(h.timestamp)}
              {h.reason && " · " + h.reason}
              {h.message && " · " + h.message}
            </p>
          ))}
        </>
      )}
      {own && r.status === "INFORMATION_REQUESTED" && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            action(`/capability-requests/${r.id}/respond`, {
              message: response,
            });
          }}
        >
          <Field label="Response to the reviewer">
            <textarea
              required
              minLength={3}
              value={response}
              onChange={(e) => setResponse(e.target.value)}
            />
          </Field>
          <button>Send Additional Information</button>
        </form>
      )}
      {own && ["PENDING", "INFORMATION_REQUESTED"].includes(r.status) && (
        <button
          onClick={() => action(`/capability-requests/${r.id}/withdraw`, {})}
        >
          Withdraw Request
        </button>
      )}
      {reviewer &&
        !own &&
        ["PENDING", "INFORMATION_REQUESTED", "APPROVED"].includes(r.status) && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              action(`/capability-requests/${r.id}/review`, {
                decision,
                reason,
                evidence,
                valid_until: expiry ? new Date(expiry).toISOString() : null,
              });
            }}
          >
            <p>
              Review {reviewedOrganisation?.display_name || "the organisation"}
              {r.facility_id
                ? " · " +
                  (reviewedOrganisation?.facilities.find(
                    (f) => f.id === r.facility_id,
                  )?.name || "assigned facility")
                : ""}
              . Approval records the assessed scope; it does not certify battery
              safety.
            </p>
            <div className="form-grid">
              <Field label="Review decision">
                <select
                  value={decision}
                  onChange={(e) => setDecision(e.target.value)}
                >
                  {(r.status === "APPROVED"
                    ? ["SUSPENDED"]
                    : r.action === "REMOVE"
                      ? ["INFORMATION_REQUESTED", "REMOVED", "REJECTED"]
                      : ["INFORMATION_REQUESTED", "APPROVED", "REJECTED"]
                  ).map((x) => (
                    <option value={x} key={x}>
                      {human(x)}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Qualification valid until">
                <input
                  type="datetime-local"
                  value={expiry}
                  onChange={(e) => setExpiry(e.target.value)}
                  required={decision === "APPROVED" && r.kind !== "ROLE"}
                />
              </Field>
            </div>
            <Field label="Decision reason or information needed">
              <textarea
                required
                minLength={3}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
            </Field>
            <Field label="Review reference · required for scope approval">
              <input
                value={evidence}
                onChange={(e) => setEvidence(e.target.value)}
                required={decision === "APPROVED" && r.kind !== "ROLE"}
              />
            </Field>
            <button>Record Review Decision</button>
          </form>
        )}
    </article>
  );
}
