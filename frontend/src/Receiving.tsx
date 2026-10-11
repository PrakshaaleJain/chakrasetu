import { hasRole } from "./navigation";
import { useState } from "react";
import type { Actor, Action, Shipment, Transaction, Settlement } from "./types";
import { useResource } from "./api";
import { Panel, Field, Badge, Empty, money, human } from "./components";
export function Receiving({
  actor,
  shipments,
  transactions,
  action,
  version,
}: {
  actor: Actor;
  shipments: Shipment[];
  transactions: Transaction[];
  action: Action;
  version: number;
}) {
  const [selected, setSelected] = useState("");
  const [outcome, setOutcome] = useState("ACCEPT_AS_AGREED");
  const [price, setPrice] = useState("18000");
  const [evidence, setEvidence] = useState("");
  const [notes, setNotes] = useState("");
  const [disposition, setDisposition] = useState("REFURBISHMENT_COMPLETED");
  const [settlementStatus, setSettlementStatus] = useState("PAYMENT_REPORTED");
  const s = shipments.find((x) => x.id === selected) || shipments[0];
  const tx = transactions.find((t) => t.id === s?.transaction_id);
  const { data: settlement } = useResource<Settlement | null>(
    tx && !hasRole(actor, "TRANSPORTER") && !hasRole(actor, "HUB")
      ? "/transactions/" + tx.id + "/settlement"
      : null,
    version,
    null,
  );
  if (!s || !tx)
    return (
      <Panel title="Receiving and completion">
        <Empty>
          No shipment available. Physical arrival and receipt precede
          inspection, settlement and disposition.
        </Empty>
      </Panel>
    );
  const receiver = actor.organisation_id === tx.buyer_org_id;
  const party = [tx.seller_org_id, tx.buyer_org_id].includes(
    actor.organisation_id,
  );
  const dispositions =
    tx.pathway === "QUALIFIED_REVIEW"
      ? ["TRANSFERRED_TO_ELIGIBLE_OPERATOR", "PENDING_FURTHER_ASSESSMENT"]
      : tx.pathway === "RECYCLING"
        ? [
            "SENT_FOR_RECYCLING",
            "RECYCLING_COMPLETED",
            "PENDING_FURTHER_ASSESSMENT",
          ]
        : tx.pathway === "SECOND_LIFE_ASSESSMENT"
          ? [
              "SECOND_LIFE_ASSESSMENT_COMPLETED",
              "PENDING_FURTHER_ASSESSMENT",
              "SENT_FOR_RECYCLING",
            ]
          : [
              "REFURBISHMENT_COMPLETED",
              "PENDING_FURTHER_ASSESSMENT",
              "SENT_FOR_RECYCLING",
            ];
  const current = dispositions.includes(disposition)
    ? disposition
    : dispositions[0];
  return (
    <>
      <div className="toolbar">
        <select value={s.id} onChange={(e) => setSelected(e.target.value)}>
          {shipments.map((x) => (
            <option key={x.id} value={x.id}>
              {x.asset.internal_id} · {human(x.state)}
            </option>
          ))}
        </select>
        <Badge value={s.state} />
      </div>
      <div className="two-cols">
        <Panel title="Receiving inspection">
          <p className="notice">
            Arrival, physical receipt and inspection acceptance are separate
            milestones. Record physical receipt in Shipments first.
          </p>
          {receiver ? (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                action("/shipments/" + s.id + "/inspection", {
                  outcome,
                  evidence,
                  notes,
                  ...(outcome === "REVISE_PRICE"
                    ? { price_paise: Math.round(Number(price) * 100) }
                    : {}),
                });
              }}
            >
              <Field label="Inspection decision">
                <select
                  value={outcome}
                  onChange={(e) => setOutcome(e.target.value)}
                >
                  {[
                    "ACCEPT_AS_AGREED",
                    "REVISE_PRICE",
                    "FURTHER_INSPECTION",
                    "REJECT_PATHWAY",
                    "POSSIBLE_HAZARD",
                  ].map((x) => (
                    <option key={x} value={x}>
                      {human(x)}
                    </option>
                  ))}
                </select>
              </Field>
              {outcome === "REVISE_PRICE" && (
                <Field label="Proposed new purchase price · INR">
                  <input
                    type="number"
                    min="0"
                    value={price}
                    onChange={(e) => setPrice(e.target.value)}
                  />
                </Field>
              )}
              <Field label="Inspection evidence">
                <input
                  required
                  value={evidence}
                  onChange={(e) => setEvidence(e.target.value)}
                />
              </Field>
              <Field label="Observations / rationale">
                <textarea
                  required
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                />
              </Field>
              <button className="primary">Record inspection</button>
              <p className="muted">
                A price revision creates new terms. Both parties must confirm
                that version in Transactions before settlement resumes.
              </p>
            </form>
          ) : (
            <Empty>The receiving organisation records inspection.</Empty>
          )}
          {s.data.inspections?.map((i: any, n: number) => (
            <div className="evidence" key={n}>
              <strong>{human(i.outcome)}</strong>
              <small>
                {i.notes} · {i.evidence}
              </small>
            </div>
          ))}
        </Panel>
        <Panel title="Settlement record · no money movement">
          {settlement ? (
            <>
              <div className="card-line">
                <strong className="big-number">
                  {money(settlement.amount_paise)}
                </strong>
                <Badge value={settlement.status} />
              </div>
              <p className="muted">
                {settlement.payer_org_id} → {settlement.payee_org_id}. Payment
                reported requires separate payee confirmation.
              </p>
              {party && (
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    action("/transactions/" + tx.id + "/settlement", {
                      status: settlementStatus,
                      reference: evidence,
                    });
                  }}
                >
                  <Field label="Record status">
                    <select
                      value={settlementStatus}
                      onChange={(e) => setSettlementStatus(e.target.value)}
                    >
                      {[
                        "DUE",
                        "PAYMENT_REPORTED",
                        "SETTLED_CONFIRMED",
                        "DISPUTED",
                        "OVERDUE",
                      ].map((x) => (
                        <option key={x} value={x}>
                          {human(x)}
                        </option>
                      ))}
                    </select>
                  </Field>
                  <Field label="Supporting reference">
                    <input
                      required
                      value={evidence}
                      onChange={(e) => setEvidence(e.target.value)}
                    />
                  </Field>
                  <button>Record settlement status</button>
                </form>
              )}
              <details>
                <summary>Settlement history</summary>
                <pre>{JSON.stringify(settlement.data, null, 2)}</pre>
              </details>
            </>
          ) : (
            <Empty>Confirm mutual terms to create a settlement record.</Empty>
          )}
          <h4>Final disposition</h4>
          {receiver ? (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                action("/batteries/" + tx.asset_id + "/disposition", {
                  outcome: current,
                  evidence,
                });
              }}
            >
              <Field label="Actual reported downstream outcome">
                <select
                  value={current}
                  onChange={(e) => setDisposition(e.target.value)}
                >
                  {dispositions.map((x) => (
                    <option key={x} value={x}>
                      {human(x)}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Outcome evidence / report">
                <input
                  required
                  value={evidence}
                  onChange={(e) => setEvidence(e.target.value)}
                />
              </Field>
              <button className="primary">Record evidenced disposition</button>
            </form>
          ) : (
            <Empty>The receiver attests the outcome.</Empty>
          )}
          <p className="notice">
            Sent for recycling does not mean recycling completed. Closure
            remains gated by inspection, settlement, disposition and unresolved
            exceptions.
          </p>
        </Panel>
      </div>
    </>
  );
}
