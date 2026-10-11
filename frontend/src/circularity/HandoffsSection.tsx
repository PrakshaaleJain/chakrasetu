import { hasRole } from "../navigation";
import { Panel, Field, Badge, Empty, money, human } from "../components";
import type { useCircularity } from "./useCircularity";
import { days, reviewBody } from "./domain";
export function HandoffsSection({
  ctx,
}: {
  ctx: ReturnType<typeof useCircularity>;
}) {
  const {
    actor,
    action,
    network,
    evidence,
    spec,
    receiver,
    setReceiver,
    price,
    setPrice,
    cap,
    setCap,
    quote,
    setQuote,
    carrier,
    setCarrier,
    item,
    setItem,
    payer,
    setPayer,
    condition,
    setCondition,
    physical,
    setPhysical,
    items,
    handoffs,
    requests,
    isReviewer,
    hBody,
  } = ctx;
  return (
    <>
      <Panel title="Offer a documented output to a qualified receiver">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            action("/circularity/handoffs", {
              item_id: item,
              receiver_facility_id: receiver,
              price_paise:
                price === "" ? null : Math.round(Number(price) * 100),
              payer_org_id: payer,
              budget_paise: cap === "" ? null : Math.round(Number(cap) * 100),
              acceptance_specification: spec,
              evidence,
              window_start: days(1),
              window_end: days(3),
            });
          }}
        >
          <Field label="Your owned, physically held output">
            <select
              required
              value={item}
              onChange={(e) => setItem(e.target.value)}
            >
              <option value="">Choose output</option>
              {items
                .filter(
                  (i) =>
                    i.kind !== "BATTERY" &&
                    i.owner_org_id === actor.organisation_id &&
                    i.custodian_org_id === actor.organisation_id,
                )
                .map((i) => (
                  <option key={i.id} value={i.id}>
                    {i.identifier} · {human(i.state)}
                  </option>
                ))}
            </select>
          </Field>
          <Field label="Receiving facility">
            <select
              required
              value={receiver}
              onChange={(e) => {
                setReceiver(e.target.value);
                setPayer(
                  network.facilities.find((f) => f.id === e.target.value)
                    ?.organisation_id || "",
                );
              }}
            >
              <option value="">Choose receiving facility</option>
              {network.facilities
                .filter((f) => f.organisation_id !== actor.organisation_id)
                .map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.name}
                  </option>
                ))}
            </select>
          </Field>
          <div className="form-grid">
            <Field label="Proposed sale price · INR">
              <input
                type="number"
                min="0"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
              />
            </Field>
            <Field label="Approved logistics cap · INR">
              <input
                type="number"
                min="0"
                value={cap}
                onChange={(e) => setCap(e.target.value)}
              />
            </Field>
          </div>
          <Field label="Responsible logistics payer">
            <select
              required
              value={payer}
              onChange={(e) => setPayer(e.target.value)}
            >
              <option value="">Select party</option>
              <option value={actor.organisation_id}>Seller</option>
              {receiver && (
                <option
                  value={
                    network.facilities.find((f) => f.id === receiver)
                      ?.organisation_id
                  }
                >
                  Receiver
                </option>
              )}
            </select>
          </Field>
          <p>
            Demo collection window: tomorrow through three days from now.
            Technical requirements must be accepted by the actual receiver.
            Unknown commercial figures block booking.
          </p>
          <button>Propose versioned offtake / product sale</button>
        </form>
      </Panel>
      <Panel title="Transport quote inputs">
        <Field label="Your transporter profile">
          <select value={carrier} onChange={(e) => setCarrier(e.target.value)}>
            <option value="">Select own verified carrier</option>
            {network.transporters
              .filter((t) => t.organisation_id === actor.organisation_id)
              .map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
          </select>
        </Field>
        <Field label="Actual all-inclusive submitted quote · INR">
          <input
            type="number"
            min="0"
            value={quote}
            onChange={(e) => setQuote(e.target.value)}
          />
        </Field>
        <label>
          <input
            type="checkbox"
            checked={physical}
            onChange={(e) => setPhysical(e.target.checked)}
          />{" "}
          I am confirming a physical handover for custody events
        </label>
        <label>
          <input
            type="checkbox"
            checked={condition}
            onChange={(e) => setCondition(e.target.checked)}
          />{" "}
          Condition matches the agreed receiving specification
        </label>
      </Panel>
      {hasRole(actor, "TRANSPORTER") && (
        <Panel title="Eligible quote requests · operational scope only">
          {requests.length === 0 ? (
            <Empty>
              No eligible pending quote requests for your verified scope.
            </Empty>
          ) : (
            requests.map((r) => (
              <div key={r.handoff_id} className="evidence">
                <strong>
                  {r.kind} · {r.category} · {r.mass_kg} kg
                </strong>
                <p>
                  {r.source_facility_id} → {r.receiver_facility_id}
                </p>
                <p>{r.required_handling_specification}</p>
                <button
                  disabled={quote === ""}
                  onClick={() =>
                    action("/circularity/handoffs/" + r.handoff_id + "/quote", {
                      transporter_id: r.transporter_id,
                      total_paise: Math.round(Number(quote) * 100),
                      expires_at: days(1),
                      evidence,
                      acceptance_specification_confirmed: condition,
                    })
                  }
                >
                  Submit own all-inclusive quote
                </button>
              </div>
            ))
          )}
        </Panel>
      )}
      {handoffs.map((h) => (
        <Panel
          key={h.id}
          title={h.item.identifier + " · terms v" + h.version}
          aside={<Badge value={h.state} />}
        >
          <p>
            {h.seller_org_id} → {h.buyer_org_id} · price{" "}
            {money(h.terms.price_paise)} · logistics payer{" "}
            {h.terms.payer_org_id} · cap {money(h.terms.budget_paise)}
          </p>
          <p>
            Confirmations: {h.terms.confirmations.join(", ") || "None"} · quote{" "}
            {money(h.data.quote?.total_paise)} · settlement {h.data.settlement}{" "}
            (record only)
          </p>
          <p>{h.terms.data.acceptance_specification}</p>
          <div className="actions">
            {[h.seller_org_id, h.buyer_org_id].includes(
              actor.organisation_id,
            ) &&
              ["PROPOSED", "CONTRACTED"].includes(h.state) && (
                <button
                  onClick={() =>
                    action("/circularity/handoffs/" + h.id + "/confirm", {
                      version: h.version,
                    })
                  }
                >
                  Confirm exact version {h.version}
                </button>
              )}
            {h.state === "CONTRACTED" && hasRole(actor, "TRANSPORTER") && (
              <button
                disabled={!carrier || quote === ""}
                onClick={() =>
                  action("/circularity/handoffs/" + h.id + "/quote", {
                    transporter_id: carrier,
                    total_paise: Math.round(Number(quote) * 100),
                    expires_at: days(1),
                    evidence,
                    acceptance_specification_confirmed: condition,
                  })
                }
              >
                Submit actual quote with declared scope
              </button>
            )}
            {h.state === "CONTRACTED" &&
              h.terms.payer_org_id === actor.organisation_id && (
                <>
                  <button
                    onClick={() =>
                      action("/circularity/handoffs/" + h.id + "/book")
                    }
                  >
                    Accept quote, reserve and book
                  </button>
                  <button
                    disabled={cap === ""}
                    onClick={() =>
                      action(
                        "/circularity/handoffs/" + h.id + "/amend",
                        hBody(h),
                      )
                    }
                  >
                    Propose revised cap (use cap field above)
                  </button>
                </>
              )}
            {["BOOKED", "PICKED_UP", "ARRIVED", "RECEIVED"].includes(
              h.state,
            ) && (
              <>
                {(h.state === "BOOKED"
                  ? ["PICKED_UP"]
                  : h.state === "PICKED_UP"
                    ? ["ARRIVED"]
                    : h.state === "ARRIVED"
                      ? ["RECEIVED", "DISPUTED"]
                      : ["CLOSED"]
                ).map((state) => (
                  <button
                    key={state}
                    onClick={() =>
                      action("/circularity/handoffs/" + h.id + "/events", {
                        state,
                        physical,
                        condition_matches: condition,
                        evidence,
                      })
                    }
                  >
                    Record {human(state)}
                  </button>
                ))}
              </>
            )}
            {h.state === "RECEIVED" &&
              actor.organisation_id === h.buyer_org_id && (
                <button
                  onClick={() =>
                    action("/circularity/handoffs/" + h.id + "/settlement", {
                      status: "REPORTED",
                      evidence,
                    })
                  }
                >
                  Buyer: report payment record
                </button>
              )}
            {h.state === "RECEIVED" &&
              actor.organisation_id === h.seller_org_id && (
                <button
                  onClick={() =>
                    action("/circularity/handoffs/" + h.id + "/settlement", {
                      status: "CONFIRMED",
                      evidence,
                    })
                  }
                >
                  Seller: confirm payment receipt record
                </button>
              )}
            {isReviewer &&
              ["DISPUTED", "RECEIVED", "CONTRACTED"].includes(h.state) && (
                <button
                  onClick={() =>
                    action(
                      "/circularity/handoffs/" + h.id + "/resolve",
                      reviewBody(evidence),
                    )
                  }
                >
                  Resolve documented commercial / receipt exception
                </button>
              )}
          </div>
          <ol>
            {h.custody.map((c) => (
              <li key={c.id}>
                {human(c.event_type)} · {c.previous_org_id} → {c.new_org_id}
              </li>
            ))}
          </ol>
          <details>
            <summary>Terms history, route, quote and evidence</summary>
            <pre>
              {JSON.stringify({ history: h.history, data: h.data }, null, 2)}
            </pre>
          </details>
        </Panel>
      ))}
    </>
  );
}
