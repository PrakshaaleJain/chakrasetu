import { hasRole } from "./navigation";
import { useState } from "react";
import type { Actor, Action, Shipment, Network } from "./types";
import { api, useResource } from "./api";
import { Badge, Panel, Field, Empty, human, date } from "./components";
const NEXT: Record<string, string[]> = {
  BOOKED: ["PICKUP_SCHEDULED", "CANCELLED"],
  PICKUP_SCHEDULED: ["PICKED_UP", "PICKUP_FAILED", "EXCEPTION_HOLD"],
  PICKUP_FAILED: ["PICKUP_SCHEDULED", "CANCELLED"],
  PICKED_UP: ["IN_TRANSIT", "EXCEPTION_HOLD"],
  IN_TRANSIT: ["ARRIVED_PENDING_RECEIPT", "EXCEPTION_HOLD"],
  ARRIVED_PENDING_RECEIPT: ["RECEIVED", "RECEIPT_DISPUTED", "EXCEPTION_HOLD"],
  RECEIVED: ["DISPOSITION_PENDING", "CLOSED"],
  DISPOSITION_PENDING: ["CLOSED"],
};
export function Shipments({
  shipments,
  actor,
  action,
  version,
  network,
}: {
  shipments: Shipment[];
  actor: Actor;
  action: Action;
  version: number;
  network: Network;
}) {
  const [batchEconomics, setBatchEconomics] = useState<unknown | null>(null);
  const [batchIds, setBatchIds] = useState<string[]>([]);
  const [selected, setSelected] = useState("");
  const [target, setTarget] = useState("");
  const [evidence, setEvidence] = useState("");
  const [notes, setNotes] = useState("");
  const [physical, setPhysical] = useState(false);
  const [matches, setMatches] = useState(true);
  const [receipt, setReceipt] = useState("ACCEPTED");
  const [value, setValue] = useState("8");
  const [telemetry, setTelemetry] = useState("ROUTE_DEVIATION");
  const { data: batches } = useResource<any[]>("/consolidations", version, []);
  const base = shipments.find((s) => s.id === selected) || shipments[0];
  const { data: detail } = useResource<Shipment | null>(
    base ? "/shipments/" + base.id : null,
    version,
    null,
  );
  const s = detail && detail.id === base?.id ? { ...base, ...detail } : base;
  const name = (id: string) =>
    network.organisations.find((o) => o.id === id)?.name || id;
  const choices = s ? NEXT[s.state] || [] : [];
  const next = choices.includes(target) ? target : choices[0] || "";
  if (!s)
    return (
      <Panel title="Shipment workflow">
        <Empty>
          No booked shipments. Accept a valid quote, reserve capacity, then
          create a shipment in Routes & quotes.
        </Empty>
      </Panel>
    );
  return (
    <>
      <details className="panel">
        <summary>
          Compatible consolidation manifests · preserve per-asset custody
        </summary>
        <p className="muted">
          Select at least two booked one-hub shipments with the same receiver
          and transporter. Every affected party must approve before pickup.
        </p>
        {shipments
          .filter((x) => x.route.hub_id && x.state === "BOOKED")
          .map((x) => (
            <label className="checks" key={x.id}>
              <span>
                <input
                  type="checkbox"
                  checked={batchIds.includes(x.id)}
                  onChange={(e) =>
                    setBatchIds(
                      e.target.checked
                        ? [...batchIds, x.id]
                        : batchIds.filter((id) => id !== x.id),
                    )
                  }
                />{" "}
                {x.asset.internal_id}
              </span>
            </label>
          ))}
        <button
          disabled={batchIds.length < 2}
          onClick={() =>
            action("/consolidations", {
              shipment_ids: batchIds,
              evidence: evidence || "Compatible batch proposal",
              reason: notes || "Compatible hub consolidation proposal",
            })
          }
        >
          Propose compatible manifest
        </button>
        {batches.map((b) => (
          <div className="evidence" key={b.id}>
            <strong>
              Manifest {b.id.slice(0, 8)} · {b.data.total_mass_kg} kg
            </strong>
            <Badge value={b.status} />
            <button
              onClick={async () => {
                try {
                  setBatchEconomics(
                    await api("/consolidations/" + b.id + "/economics"),
                  );
                } catch (e) {
                  setBatchEconomics({ error: (e as Error).message });
                }
              }}
            >
              Compare committed transport cost per battery
            </button>
            <small>{b.data.notice}</small>
            <small>
              Approvals: {b.approvals.join(", ") || "none"}. Savings comparison
              incomplete; no saving claimed.
            </small>
            {b.status !== "APPROVED" &&
              b.data.required_org_ids.includes(actor.organisation_id) && (
                <button
                  onClick={() => action("/consolidations/" + b.id + "/approve")}
                >
                  Approve manifest as this organisation
                </button>
              )}
          </div>
        ))}
      </details>
      {batchEconomics !== null && (
        <Panel title="Batch economics · committed quotes, no invented savings">
          <pre>{JSON.stringify(batchEconomics, null, 2)}</pre>
        </Panel>
      )}
      <div className="toolbar">
        <select
          value={s.id}
          onChange={(e) => {
            setSelected(e.target.value);
            setTarget("");
          }}
        >
          {shipments.map((x) => (
            <option key={x.id} value={x.id}>
              {x.asset.internal_id} · {human(x.state)}
            </option>
          ))}
        </select>
        <Badge value={s.state} />
      </div>
      <div className="two-cols">
        <Panel title={base.asset.internal_id + " · physical journey"}>
          <dl className="details">
            <dt>Physical holder</dt>
            <dd>
              {base.asset.custody_segments &&
              base.asset.custody_segments.length > 1
                ? "Mixed custody — see per-quantity holders below"
                : name(base.asset.current_holder_org_id)}
              {base.asset.custody_segments &&
                base.asset.custody_segments.length > 1 && (
                  <ul>
                    {base.asset.custody_segments.map((segment, i) => (
                      <li key={i}>
                        {segment.quantity} unit(s) · {name(segment.holder)}
                      </li>
                    ))}
                  </ul>
                )}
            </dd>
            <dt>Route</dt>
            <dd>{base.route.data.stops.join(" → ")}</dd>
            <dt>Hub stage</dt>
            <dd>{human(s.data.hub_stage || "DIRECT")}</dd>
            <dt>Handover confirmations</dt>
            <dd>
              {Object.keys(s.data.handover_confirmations || {})
                .map((x) => name(x))
                .join(", ") || "Not yet recorded"}
            </dd>
          </dl>
          <div className="notice">
            Appointment and scheduled time do not transfer custody. Both
            physical handover parties must confirm pickup with evidence.
          </div>
          {choices.length > 0 &&
            !hasRole(actor, "REVIEWER") &&
            !hasRole(actor, "HUB") && (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  action("/shipments/" + s.id + "/events", {
                    state: next,
                    evidence,
                    notes,
                    physical,
                    condition_matches: matches,
                    receipt,
                  });
                }}
              >
                <div className="form-grid">
                  <Field label="Next permitted transition">
                    <select
                      value={next}
                      onChange={(e) => setTarget(e.target.value)}
                    >
                      {choices.map((x) => (
                        <option key={x} value={x}>
                          {human(x)}
                        </option>
                      ))}
                    </select>
                  </Field>
                  <Field label="Physical milestone evidence / reference">
                    <input
                      value={evidence}
                      onChange={(e) => setEvidence(e.target.value)}
                    />
                  </Field>
                </div>
                <Field label="Reason / observed condition / notes">
                  <textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                  />
                </Field>
                {["RECEIVED", "RECEIPT_DISPUTED"].includes(next) && (
                  <Field label="Per-item receipt outcome">
                    <select
                      value={receipt}
                      onChange={(e) => setReceipt(e.target.value)}
                    >
                      {[
                        "ACCEPTED",
                        "PARTIALLY_ACCEPTED",
                        "REJECTED",
                        "RECEIVED_PENDING_INSPECTION",
                      ].map((x) => (
                        <option key={x} value={x}>
                          {human(x)}
                        </option>
                      ))}
                    </select>
                  </Field>
                )}
                <div className="checks">
                  <label>
                    <input
                      type="checkbox"
                      checked={physical}
                      onChange={(e) => setPhysical(e.target.checked)}
                    />{" "}
                    I confirm this physical handover / receipt occurred.
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      checked={matches}
                      onChange={(e) => setMatches(e.target.checked)}
                    />{" "}
                    Condition matches the recorded scope and snapshot.
                  </label>
                </div>
                <button className="primary">
                  Record milestone as {actor.name.split(" · ")[0]}
                </button>
              </form>
            )}
          {base.route.hub_id &&
            s.state === "IN_TRANSIT" &&
            hasRole(actor, "HUB", "TRANSPORTER") && (
              <div>
                <h4>Hub custody confirmations</h4>
                <Field label="Hub handover evidence">
                  <input
                    value={evidence}
                    onChange={(e) => setEvidence(e.target.value)}
                  />
                </Field>
                <div className="checks">
                  <label>
                    <input
                      type="checkbox"
                      checked={physical}
                      onChange={(e) => setPhysical(e.target.checked)}
                    />{" "}
                    Physical hub handover confirmed
                  </label>
                </div>
                <div className="actions">
                  {["HUB_RECEIVED", "HUB_DISPATCHED"].map((x) => (
                    <button
                      key={x}
                      onClick={() =>
                        action("/shipments/" + s.id + "/hub-events", {
                          event: x,
                          physical,
                          evidence,
                        })
                      }
                    >
                      {human(x)} · confirm
                    </button>
                  ))}
                </div>
                <p className="muted">
                  Switch between hub and transporter actors. Both must confirm
                  each handover.
                </p>
              </div>
            )}
          <h4>Closure gates</h4>
          {s.closure?.can_close ? (
            <Badge value="READY_TO_CLOSE" />
          ) : (
            <ul className="gate-list">
              {s.closure?.reasons.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          )}
        </Panel>
        <Panel title="Append-only custody timeline">
          {s.custody?.length ? (
            s.custody.map((c) => (
              <div className="timeline-item" key={c.id}>
                <span className="timeline-dot" />
                <div>
                  <strong>{human(c.event_type)}</strong>
                  <p>
                    {name(c.previous_holder)} → {name(c.new_holder)}
                  </p>
                  <small>
                    {date(c.created_at)} · Recorded by {c.actor_id}
                  </small>
                  <p className="muted">{c.data.evidence}</p>
                </div>
              </div>
            ))
          ) : (
            <Empty>
              No physical custody transfers yet. Scheduling alone leaves the
              holder unchanged.
            </Empty>
          )}
          <h4>
            Transit signals <span className="pill">SIMULATED</span>
          </h4>
          {s.telemetry?.map((t) => (
            <div className="evidence" key={t.id}>
              <div className="card-line">
                <strong>{human(t.data.event)}</strong>
                <Badge value={t.alert ? "REVIEW_ALERT" : "RECORDED"} />
              </div>
              <small>
                SIMULATED · {t.data.value ?? "No numeric value"} ·{" "}
                {date(t.created_at)}
              </small>
              <small>{t.data.notice}</small>
            </div>
          ))}
          {actor.organisation_id === base.transporter_org_id &&
            ["PICKED_UP", "IN_TRANSIT", "EXCEPTION_HOLD"].includes(s.state) && (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  action("/shipments/" + s.id + "/telemetry", {
                    event: telemetry,
                    value: Number(value),
                    notes: "Simulated telemetry signal",
                  });
                }}
              >
                <Field label="Simulated telemetry update">
                  <select
                    value={telemetry}
                    onChange={(e) => setTelemetry(e.target.value)}
                  >
                    {[
                      "ROUTE_DEVIATION",
                      "PROLONGED_STOP",
                      "TEMPERATURE",
                      "SHOCK",
                      "MISSING_EVENT",
                      "REPORTED_INCIDENT",
                    ].map((x) => (
                      <option key={x} value={x}>
                        {human(x)}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="Reading · km / minutes / °C / g as applicable">
                  <input
                    type="number"
                    value={value}
                    onChange={(e) => setValue(e.target.value)}
                  />
                </Field>
                <button>Record Simulated Update</button>
              </form>
            )}
        </Panel>
      </div>
    </>
  );
}
