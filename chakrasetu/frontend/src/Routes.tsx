import { displayJSON } from "./components";
import { hasRole } from "./navigation";
import { useState } from "react";
import type {
  Actor,
  Action,
  Transaction,
  Route,
  Quote,
  Network,
} from "./types";
import { useResource } from "./api";
import {
  Badge,
  Panel,
  Field,
  Empty,
  RouteMap,
  money,
  date,
  human,
} from "./components";
export function Routes({
  transactions,
  actor,
  action,
  version,
  network,
}: {
  transactions: Transaction[];
  actor: Actor;
  action: Action;
  version: number;
  network: Network;
}) {
  const [selection, setSelection] = useState("");
  const [chosen, setChosen] = useState("");
  const [total, setTotal] = useState("4200");
  const [status, setStatus] = useState("SUBMITTED");
  const [evidence, setEvidence] = useState("");
  const tx = transactions.find((t) => t.id === selection) || transactions[0];
  const { data: plans } = useResource<Route[]>(
    tx ? "/transactions/" + tx.id + "/route-plans" : null,
    version,
    [],
  );
  const { data: quotes } = useResource<Quote[]>(
    tx && !hasRole(actor, "HUB")
      ? "/transactions/" + tx.id + "/transport-quotes"
      : null,
    version,
    [],
  );
  const { data: diagnostics } = useResource<{ rejected: any[] }>(
    tx && [tx.seller_org_id, tx.buyer_org_id].includes(actor.organisation_id)
      ? "/transactions/" + tx.id + "/route-diagnostics"
      : null,
    version,
    { rejected: [] },
  );
  const current = plans.filter(
    (p) =>
      p.terms_version === tx?.terms_version &&
      new Date(p.expires_at).getTime() > Date.now(),
  );
  const route = current.find((p) => p.id === chosen) || current[0];
  if (!tx)
    return (
      <Panel title="Routes and transport">
        <Empty>
          No confirmed transactions. Select an offer and confirm the same terms
          version as both parties first.
        </Empty>
      </Panel>
    );
  const party = [tx.seller_org_id, tx.buyer_org_id].includes(
    actor.organisation_id,
  );
  const payer = tx.terms?.payer_org_id === actor.organisation_id;
  return (
    <>
      <div className="toolbar">
        <select
          value={tx.id}
          onChange={(e) => {
            setSelection(e.target.value);
            setChosen("");
          }}
        >
          {transactions.map((t) => (
            <option value={t.id} key={t.id}>
              {t.asset.internal_id} · {human(t.logistics_status)}
            </option>
          ))}
        </select>
        {party && (
          <button
            className="primary"
            onClick={() => action("/transactions/" + tx.id + "/route-plans")}
          >
            Find Available Transport Routes
          </button>
        )}
      </div>
      <Panel
        title="Route alternatives"
        aside={<span className="pill">Deterministic · rule chakra-1.0</span>}
      >
        <RouteMap routes={current.slice(0, 2)} network={network} />
        <p className="notice">
          Distance: Haversine × 1.3 proxy. Travel time: 30 km/h assumption.
          Configured rate cards are estimates; booking requires a submitted and
          accepted quote.
        </p>
        <div className="route-grid">
          {current.length === 0 ? (
            <Empty>
              No current plan. Generate alternatives after both parties confirm
              terms.
            </Empty>
          ) : (
            current.map((p) => (
              <div
                className={"route-card " + (route?.id === p.id ? "active" : "")}
                key={p.id}
              >
                <div className="card-line">
                  <strong>
                    {p.hub_id
                      ? "Via one aggregation hub"
                      : "Direct to receiver"}
                  </strong>
                  <input
                    aria-label="Select route"
                    type="radio"
                    name="route"
                    checked={route?.id === p.id}
                    onChange={() => setChosen(p.id)}
                  />
                </div>
                <div className="route-stats">
                  <span>
                    <strong>{p.distance_km.toFixed(1)} km</strong>
                    <small>distance proxy</small>
                  </span>
                  <span>
                    <strong>{p.hours} h</strong>
                    <small>time proxy</small>
                  </span>
                  <span>
                    <strong>{money(p.estimated_cost_paise)}</strong>
                    <small>Estimated Transport Cost</small>
                  </span>
                </div>
                <ol className="legs">
                  {p.data.legs.map((l: any, i: number) => (
                    <li key={i}>
                      {l.from} → {l.to}
                      <small>
                        {l.distance_km} km · {l.source}
                      </small>
                    </li>
                  ))}
                </ol>
                <p className="muted">
                  Score {p.score} · {human(p.data.ranking.objective)} · expires{" "}
                  {date(p.expires_at)}
                </p>
                <details>
                  <summary>Constraints, ranking components and scope</summary>
                  <pre>
                    {displayJSON(
                      {
                        constraints: p.data.constraints,
                        ranking: p.data.ranking,
                        scope: p.data.scope,
                        transporters: p.data.transporters,
                      },
                      null,
                      2,
                    )}
                  </pre>
                </details>
                {p.hub_id && (
                  <p>
                    <Badge
                      value={
                        p.data.hub_approved_by
                          ? "HUB_APPROVED"
                          : "HUB_APPROVAL_REQUIRED"
                      }
                    />
                    {hasRole(actor, "HUB") && !p.data.hub_approved_by && (
                      <button
                        onClick={() =>
                          action("/route-plans/" + p.id + "/hub-approval")
                        }
                      >
                        Approve hub dwell and onward plan
                      </button>
                    )}
                  </p>
                )}
              </div>
            ))
          )}
        </div>
        {diagnostics.rejected.length > 0 && (
          <details>
            <summary>
              Rejected route / transporter candidates · reason codes
            </summary>
            {diagnostics.rejected.map((r, i) => (
              <div key={i} className="reason">
                <strong>
                  {r.transporter_id ||
                    r.facility?.name ||
                    r.hub_id ||
                    "Candidate"}
                </strong>
                {r.reasons?.map((x: any, n: number) => (
                  <p key={n}>
                    <strong>{human(x.code)}</strong> {x.message}
                  </p>
                ))}
              </div>
            ))}
          </details>
        )}
      </Panel>
      {hasRole(actor, "TRANSPORTER") && route && (
        <Panel title="Submit Transport Offer">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              action("/transactions/" + tx.id + "/transport-quotes", {
                route_id: route.id,
                total_paise:
                  status === "SUBMITTED"
                    ? Math.round(Number(total) * 100)
                    : null,
                expires_at: new Date(Date.now() + 86400000).toISOString(),
                status,
                evidence,
              });
            }}
          >
            <div className="form-grid">
              <Field label="Response">
                <select
                  value={status}
                  onChange={(e) => setStatus(e.target.value)}
                >
                  {["SUBMITTED", "DECLINED", "NO_RESPONSE"].map((s) => (
                    <option key={s} value={s}>
                      {human(s)}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="All-inclusive quote total · INR">
                <input
                  type="number"
                  min="0"
                  required={status === "SUBMITTED"}
                  value={total}
                  onChange={(e) => setTotal(e.target.value)}
                  disabled={status !== "SUBMITTED"}
                />
              </Field>
              <Field label="Quote evidence / reason">
                <input
                  required
                  value={evidence}
                  onChange={(e) => setEvidence(e.target.value)}
                />
              </Field>
            </div>
            <p className="muted">
              The selected route, load, handling scope and time window are bound
              to this quote. Hub routes include both legs under this
              transporter.
            </p>
            <button className="primary">Record response</button>
          </form>
        </Panel>
      )}
      {!hasRole(actor, "HUB") && (
        <Panel
          title="Quotes and booking"
          aside={
            <span className="pill">
              Approved cap {money(tx.terms?.budget_paise)}
            </span>
          }
        >
          {quotes.length === 0 ? (
            <Empty>
              No transport offers yet. Eligible transporters can submit an
              actual response.
            </Empty>
          ) : (
            quotes.map((q) => (
              <div key={q.id} className="quote-row">
                <div>
                  <strong>
                    {money(q.total_paise)}{" "}
                    <small>
                      {
                        network.transporters.find(
                          (t) => t.id === q.transporter_id,
                        )?.name
                      }
                    </small>
                  </strong>
                  <p>
                    {q.route_id === route?.id
                      ? "Selected route"
                      : "Other route"}{" "}
                    · terms v{q.terms_version} · {date(q.expires_at)}
                  </p>
                  {q.total_paise != null &&
                    tx.terms &&
                    q.total_paise > tx.terms.budget_paise && (
                      <span className="field-error">
                        Over cap by{" "}
                        {money(q.total_paise - tx.terms.budget_paise)} · payer{" "}
                        {tx.terms.payer_org_id}
                      </span>
                    )}
                </div>
                <Badge value={q.status} />
                {payer && q.status === "SUBMITTED" && (
                  <button onClick={() => action("/quotes/" + q.id + "/accept")}>
                    Accept quote
                  </button>
                )}
              </div>
            ))
          )}
          {party && (
            <div className="actions">
              <button
                onClick={() =>
                  route &&
                  action("/transactions/" + tx.id + "/reserve-capacity", {
                    route_id: route.id,
                  })
                }
                disabled={!route}
              >
                Hold selected route capacity
              </button>
              <button
                className="primary"
                onClick={() => action("/transactions/" + tx.id + "/shipments")}
              >
                Commit holds and book shipment
              </button>
              <button
                onClick={() =>
                  action("/transactions/" + tx.id + "/release-capacity")
                }
              >
                Release / requote
              </button>
              <button
                onClick={() =>
                  action("/transactions/" + tx.id + "/quote-round/close")
                }
              >
                Close round · no acceptance
              </button>
              {tx.logistics_status === "NO_ACCEPTANCE" && (
                <button
                  onClick={() =>
                    action("/transactions/" + tx.id + "/quote-round/reopen")
                  }
                >
                  Open new quote round
                </button>
              )}
            </div>
          )}
          <p className="muted">
            Quote acceptance is separate from a booking. Capacity holds expire
            after 30 minutes. Booking rechecks every constraint.
          </p>
        </Panel>
      )}
    </>
  );
}
