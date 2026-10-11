import { displayJSON } from "./components";
import { useState } from "react";
import type { Action, Actor, Transaction } from "./types";
import { Badge, Panel, Field, Empty, human, money, date } from "./components";
export function Transactions({
  transactions,
  actor,
  action,
}: {
  transactions: Transaction[];
  actor: Actor;
  action: Action;
}) {
  const [cap, setCap] = useState("4500");
  const [reason, setReason] = useState("Approve disclosed logistics overrun");
  const [evidence, setEvidence] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  return (
    <>
      {transactions.length === 0 ? (
        <Panel title="Transaction terms">
          <Empty>
            Select a buyer offer in Listings to begin mutual terms confirmation.
          </Empty>
        </Panel>
      ) : (
        transactions.map((tx) => (
          <Panel
            key={tx.id}
            title={tx.asset.internal_id + " · terms v" + tx.terms_version}
            aside={<Badge value={tx.status} />}
          >
            <div className="two-cols">
              <div>
                <dl className="details">
                  <dt>Seller / buyer</dt>
                  <dd>
                    {tx.seller_org_id} → {tx.buyer_org_id}
                  </dd>
                  <dt>Pathway</dt>
                  <dd>{human(tx.pathway)}</dd>
                  <dt>Logistics state</dt>
                  <dd>
                    <Badge value={tx.logistics_status} />
                  </dd>
                  <dt>Price</dt>
                  <dd>
                    {money(tx.terms?.price_paise)} · INR, per asset record
                  </dd>
                  <dt>Logistics payer / cap</dt>
                  <dd>
                    {tx.terms?.payer_org_id} · {money(tx.terms?.budget_paise)}
                  </dd>
                  <dt>Confirmation</dt>
                  <dd>
                    {tx.terms?.confirmations.map((id) => (
                      <span className="pill" key={id}>
                        {id} ✓
                      </span>
                    ))}
                    {tx.terms?.confirmations.length === 0 &&
                      "No party has confirmed this version"}
                  </dd>
                </dl>
                {tx.terms &&
                  [tx.seller_org_id, tx.buyer_org_id].includes(
                    actor.organisation_id,
                  ) &&
                  !tx.terms.confirmations.includes(actor.organisation_id) && (
                    <button
                      className="primary"
                      onClick={() =>
                        action("/transactions/" + tx.id + "/confirm", {
                          version: tx.terms_version,
                        })
                      }
                    >
                      Confirm exact terms v{tx.terms_version}
                    </button>
                  )}
                <details>
                  <summary>Accepted-term history and full snapshots</summary>
                  {tx.terms_history?.map((t) => (
                    <div key={t.id} className="evidence">
                      <strong>
                        Version {t.version} · {money(t.price_paise)} · logistics
                        cap {money(t.budget_paise)}
                      </strong>
                      <small>
                        {date(t.created_at)} · confirmations:{" "}
                        {t.confirmations.join(", ") || "none"}
                      </small>
                      <pre>{displayJSON(t.data, null, 2)}</pre>
                    </div>
                  ))}
                </details>
                {[tx.seller_org_id, tx.buyer_org_id].includes(
                  actor.organisation_id,
                ) &&
                  tx.status !== "CLOSED" &&
                  tx.status !== "CANCELLED" && (
                    <>
                      <h4>Recover a pending logistics round</h4>
                      <div className="form-grid">
                        <Field label="New window start · local">
                          <input
                            type="datetime-local"
                            value={start}
                            onChange={(e) => setStart(e.target.value)}
                          />
                        </Field>
                        <Field label="New window end · local">
                          <input
                            type="datetime-local"
                            value={end}
                            onChange={(e) => setEnd(e.target.value)}
                          />
                        </Field>
                      </div>
                      <div className="actions">
                        <button
                          disabled={!start || !end}
                          onClick={() =>
                            action("/transactions/" + tx.id + "/reschedule", {
                              window_start: new Date(start).toISOString(),
                              window_end: new Date(end).toISOString(),
                              reason,
                              evidence,
                            })
                          }
                        >
                          Propose new pickup window
                        </button>
                        <button
                          onClick={() =>
                            action("/transactions/" + tx.id + "/cancel", {
                              reason,
                              evidence,
                            })
                          }
                        >
                          Confirm cancellation under terms
                        </button>
                      </div>
                      <small className="muted">
                        Rescheduling creates new terms for both parties to
                        confirm. Cancellation requires both parties; it does not
                        happen on a single tap.
                      </small>
                    </>
                  )}
              </div>
              {tx.terms?.payer_org_id === actor.organisation_id && (
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    action("/transactions/" + tx.id + "/amend", {
                      budget_paise: Math.round(Number(cap) * 100),
                      reason,
                      evidence,
                    });
                  }}
                >
                  <h4>Propose revised logistics cap</h4>
                  <p className="muted">
                    Creates a new terms version. Both parties must approve; old
                    routes and quotes need revalidation.
                  </p>
                  <Field label="Revised cap · INR">
                    <input
                      type="number"
                      min="0"
                      required
                      value={cap}
                      onChange={(e) => setCap(e.target.value)}
                    />
                  </Field>
                  <Field label="Reason">
                    <input
                      required
                      value={reason}
                      onChange={(e) => setReason(e.target.value)}
                    />
                  </Field>
                  <Field label="Approval evidence / reference">
                    <input
                      required
                      value={evidence}
                      onChange={(e) => setEvidence(e.target.value)}
                    />
                  </Field>
                  <button>Propose amendment</button>
                </form>
              )}
            </div>
          </Panel>
        ))
      )}
    </>
  );
}
