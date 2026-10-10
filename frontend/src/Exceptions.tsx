import { useState } from "react";
import type { Action, Actor, ExceptionCase, Network } from "./types";
import { Panel, Badge, Empty, Field, human, date } from "./components";
export function Exceptions({
  cases,
  actor,
  action,
  network,
}: {
  cases: ExceptionCase[];
  actor: Actor;
  action: Action;
  network: Network;
}) {
  const [selected, setSelected] = useState("");
  const [resolution, setResolution] = useState("");
  const [evidence, setEvidence] = useState("");
  const [resume, setResume] = useState(false);
  const c = cases.find((x) => x.id === selected) || cases[0];
  const [decision, setDecision] = useState("QUALIFIED_ASSESSMENT_REQUIRED");
  const [scope, setScope] = useState("CONTROLLED_HANDLING");
  const [qualification, setQualification] = useState("");
  return (
    <div className="split">
      <Panel
        title="Exception queue"
        aside={
          <span className="count">
            {cases.filter((c) => c.status !== "CLOSED").length} open
          </span>
        }
      >
        {cases.length === 0 ? (
          <Empty>No exceptions visible to this actor.</Empty>
        ) : (
          cases.map((x) => (
            <button
              className={"record-row " + (c?.id === x.id ? "selected" : "")}
              key={x.id}
              onClick={() => setSelected(x.id)}
            >
              <span>
                <strong>{human(x.category)}</strong>
                <small>
                  {x.object_type} · {x.object_id.slice(0, 8)} ·{" "}
                  {date(x.created_at)}
                </small>
              </span>
              <Badge value={x.status} />
            </button>
          ))
        )}
      </Panel>
      <Panel title={c ? human(c.category) : "Exception detail"}>
        {c && (
          <>
            <div className="card-line">
              <code>{c.id}</code>
              <Badge value={c.severity} />
            </div>
            <dl className="details">
              <dt>Responsible owner</dt>
              <dd>
                {network.organisations.find((o) => o.id === c.owner_org_id)
                  ?.name || c.owner_org_id}
              </dd>
              <dt>Affected record</dt>
              <dd>
                {c.object_type} · {c.object_id}
              </dd>
              <dt>Due</dt>
              <dd>{date(c.due_at)}</dd>
              <dt>Next action</dt>
              <dd>{c.next_action}</dd>
              <dt>Resolution</dt>
              <dd>{c.resolution || "Pending"}</dd>
            </dl>
            <details>
              <summary>Evidence and review history</summary>
              <pre>{JSON.stringify(c.data, null, 2)}</pre>
            </details>
            {actor.role === "REVIEWER" && c.status !== "CLOSED" && (
              <>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    action("/exceptions/" + c.id + "/resolve", {
                      resolution,
                      evidence,
                      resume,
                    });
                  }}
                >
                  <Field label="Resolution rationale">
                    <textarea
                      required
                      value={resolution}
                      onChange={(e) => setResolution(e.target.value)}
                    />
                  </Field>
                  <Field label="Resolution evidence">
                    <input
                      required
                      value={evidence}
                      onChange={(e) => setEvidence(e.target.value)}
                    />
                  </Field>
                  <div className="checks">
                    <label>
                      <input
                        type="checkbox"
                        checked={resume}
                        onChange={(e) => setResume(e.target.checked)}
                      />{" "}
                      Authorise documented resume for a resolved non-safety
                      discrepancy.
                    </label>
                  </div>
                  <button className="primary">Record resolution</button>
                </form>
                {["SAFETY_FLAG", "SAFETY_REVIEW_REQUIRED"].includes(
                  c.category,
                ) && (
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      action("/exceptions/" + c.id + "/qualified-review", {
                        decision,
                        qualification_evidence: qualification,
                        report: evidence,
                        handling_scope: scope,
                        valid_until: new Date(
                          Date.now() + 86400000,
                        ).toISOString(),
                        conditions: resolution,
                      });
                    }}
                  >
                    <h4>Qualified review record</h4>
                    <Field label="Decision">
                      <select
                        value={decision}
                        onChange={(e) => setDecision(e.target.value)}
                      >
                        {[
                          "INFORMATION_INSUFFICIENT",
                          "QUALIFIED_ASSESSMENT_REQUIRED",
                          "SCOPED_CLEARANCE",
                          "ESCALATE",
                        ].map((x) => (
                          <option key={x}>{x}</option>
                        ))}
                      </select>
                    </Field>
                    <Field label="Qualification evidence">
                      <input
                        required
                        value={qualification}
                        onChange={(e) => setQualification(e.target.value)}
                      />
                    </Field>
                    <Field label="Defined handling scope">
                      <input
                        required
                        value={scope}
                        onChange={(e) => setScope(e.target.value)}
                      />
                    </Field>
                    <p className="notice">
                      Report/evidence and conditions use the fields above.
                      Scoped clearance never means safe. Only a matching
                      controlled-handling receiver and transporter can proceed;
                      otherwise the asset stays held for manual escalation.
                    </p>
                    <button>Append qualified review · retain hold</button>
                  </form>
                )}
              </>
            )}
          </>
        )}
      </Panel>
    </div>
  );
}
