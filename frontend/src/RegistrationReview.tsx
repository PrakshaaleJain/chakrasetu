import { useState } from "react";
import type { Action, Actor, Battery, Candidate } from "./types";
import { useResource } from "./api";
import { hasRole } from "./navigation";
import { Badge, Field, date, human } from "./components";
export function RegistrationReviewPanel({
  asset,
  actor,
  action,
  version,
}: {
  asset: Battery;
  actor: Actor;
  action: Action;
  version: number;
}) {
  const [decision, setDecision] = useState("INFORMATION_REQUESTED"),
    [reason, setReason] = useState(""),
    [reviewPBS, setReviewPBS] = useState("");
  const r = asset.data.registration;
  const { data: matches, error } = useResource<{
    registration_reasons: { code: string; message: string }[];
    hold: boolean;
    candidates: Candidate[];
  } | null>(
    r?.status === "APPROVED"
      ? `/batteries/${asset.id}/eligible-participants`
      : null,
    version,
    null,
  );
  if (!r)
    return (
      <p className="notice">
        Legacy intake. Revise and submit to enter the registration review
        workflow.
      </p>
    );
  return (
    <section>
      <h3>
        Registration review <Badge value={r.status} />
      </h3>
      <p>
        {r.last_reason ||
          "This registration awaits a network-operator decision."}
      </p>
      <dl className="details">
        <dt>Originator PBS</dt>
        <dd>
          {asset.data.pbs || "Not recorded (legacy)"} ·{" "}
          {asset.data.pbs_comments || "No additional observations reported"}
        </dd>
        <dt>Conservative handling requirement</dt>
        <dd>
          {asset.handling_concern?.required_pbs_capability ||
            "Not derived (legacy)"}{" "}
          · system rule; the original PBS remains unchanged.
        </dd>
        <dt>Reviewer assessment</dt>
        <dd>{r.reviewer_pbs || "No separate PBS assessment recorded"}</dd>
        <dt>Additional information</dt>
        <dd>{asset.data.additional_information || "Not supplied"}</dd>
        <dt>Inspection/test information</dt>
        <dd>
          {asset.data.inspection?.conducted || "Unknown"} ·{" "}
          {human(asset.data.inspection?.source || "UNKNOWN")} ·{" "}
          {human(asset.data.inspection?.scope || "UNKNOWN")}
        </dd>
        <dt>SoH / SoC</dt>
        <dd>
          {asset.data.inspection?.soh_percent ?? "Unknown"} /{" "}
          {asset.data.inspection?.soc_percent ?? "Unknown"} % · owner-reported,
          unverified
        </dd>
      </dl>
      <details>
        <summary>Submitted registration and inspection details</summary>
        <pre>
          {JSON.stringify(
            Object.fromEntries(
              Object.entries(asset.data).filter(
                ([k]) =>
                  ![
                    "registration",
                    "screening",
                    "submission_fingerprint",
                  ].includes(k),
              ),
            ),
            null,
            2,
          )}
        </pre>
      </details>
      {hasRole(actor, "REVIEWER") &&
        actor.organisation_id !== asset.originator_org_id &&
        [
          "PENDING_REVIEW",
          "INFORMATION_REQUESTED",
          "SPECIALIST_ASSESSMENT",
        ].includes(r.status) && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              action(`/batteries/${asset.id}/registration-review`, {
                decision,
                reason,
                reviewer_pbs: reviewPBS || null,
              });
            }}
          >
            <Field label="Registration decision">
              <select
                value={decision}
                onChange={(e) => setDecision(e.target.value)}
              >
                {[
                  "APPROVED",
                  "INFORMATION_REQUESTED",
                  "SPECIALIST_ASSESSMENT",
                  "REJECTED",
                ].map((x) => (
                  <option key={x}>{x}</option>
                ))}
              </select>
            </Field>
            <Field label="Separate reviewer PBS assessment · optional">
              <select
                value={reviewPBS}
                onChange={(e) => setReviewPBS(e.target.value)}
              >
                <option value="">No separate assessment</option>
                {["L1", "L2", "L3", "L4", "L5"].map((x) => (
                  <option key={x}>{x}</option>
                ))}
              </select>
            </Field>
            <Field label="Decision reason / information required">
              <textarea
                required
                minLength={3}
                maxLength={4000}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
            </Field>
            <button>Record registration decision</button>
          </form>
        )}
      <details>
        <summary>Review and submission history</summary>
        {r.history.map((h: Record<string, string>, i: number) => (
          <p key={i}>
            {human(h.action || h.decision)} · {date(h.timestamp)} ·{" "}
            {h.reason || ""}
          </p>
        ))}
      </details>
      {error && <p role="alert">{error}</p>}
      {matches && (
        <>
          <h4>Participant eligibility</h4>
          {matches.registration_reasons.map((x) => (
            <p className="notice" key={x.code}>
              {x.message}
            </p>
          ))}
          {!matches.candidates.some((x) => x.eligible) && (
            <p className="notice">
              No currently eligible participant. Keep this registration
              available for assessment; constraints will not be relaxed.
            </p>
          )}
          {matches.candidates.map((c, i) => (
            <div className="evidence" key={i}>
              <strong>
                {c.facility.name} · {human(c.pathway)}
              </strong>
              <Badge value={c.eligible ? "ELIGIBLE" : c.status || "EXCLUDED"} />
              {c.reasons.map((x, j) => (
                <p key={j}>{x.message}</p>
              ))}
            </div>
          ))}
        </>
      )}
    </section>
  );
}
export function EvidenceReview({
  id,
  kind,
  action,
}: {
  id: string;
  kind: string;
  action: Action;
}) {
  const [classification, setClassification] = useState(kind),
    [reason, setReason] = useState(""),
    [evidence, setEvidence] = useState("");
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        action(`/evidence/${id}/review`, {
          status: "VERIFIED",
          kind: classification,
          reason,
          evidence,
        });
      }}
    >
      <Field label="Review classification (operator only)">
        <select
          value={classification}
          onChange={(e) => setClassification(e.target.value)}
        >
          {[
            "OTHER",
            "TRANSFER_AUTHORITY",
            "PHOTO",
            "SERVICE_REPORT",
            "TEST_REPORT",
            "INVOICE",
          ].map((x) => (
            <option key={x}>{x}</option>
          ))}
        </select>
      </Field>
      <Field label="Document review rationale">
        <input
          required
          minLength={3}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
        />
      </Field>
      <Field label="Review evidence/reference">
        <input
          required
          value={evidence}
          onChange={(e) => setEvidence(e.target.value)}
        />
      </Field>
      <button>Record document review</button>
    </form>
  );
}
