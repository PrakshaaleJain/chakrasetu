import { useState } from "react";
import type {
  Action,
  Actor,
  Battery,
  Listing,
  Offer,
  Candidate,
} from "./types";
import { useResource } from "./api";
import { Badge, Panel, Field, Empty, human, money, date } from "./components";
export function Marketplace({
  actor,
  batteries,
  listings,
  version,
  action,
}: {
  actor: Actor;
  batteries: Battery[];
  listings: Listing[];
  version: number;
  action: Action;
}) {
  const [selected, setSelected] = useState("");
  const [assetId, setAssetId] = useState("");
  const [price, setPrice] = useState("20000");
  const [budget, setBudget] = useState("3000");
  const [payer, setPayer] = useState("BUYER");
  const [facility, setFacility] = useState("");
  const [criteria, setCriteria] = useState(
    "Asset identity, count and reported condition match evidence. Price changes require mutual approval.",
  );
  const listing = listings.find((l) => l.id === selected);
  const own = listing?.seller_org_id === actor.organisation_id;
  const { data: offers } = useResource<Offer[]>(
    selected ? "/listings/" + selected + "/offers" : null,
    version,
    [],
  );
  const { data: candidates } = useResource<Candidate[]>(
    selected && (own || actor.role === "REVIEWER")
      ? "/listings/" + selected + "/eligible-buyers"
      : null,
    version,
    [],
  );
  const eligible = listing?.eligible_for_actor || [];
  const choice =
    eligible.find((c) => c.facility.id === facility) || eligible[0];
  return (
    <>
      <div className="toolbar">
        <p className="muted">
          Compatible downstream pathways, explainable exclusions and versioned
          offers.
        </p>
      </div>
      {actor.role === "ORIGINATOR" && (
        <Panel title="Publish a screened asset">
          <form
            className="inline-form"
            onSubmit={async (e) => {
              e.preventDefault();
              await action("/listings", {
                asset_id: assetId,
                expires_at: new Date(Date.now() + 7 * 86400000).toISOString(),
              });
            }}
          >
            <select
              required
              value={assetId}
              onChange={(e) => setAssetId(e.target.value)}
            >
              <option value="">Choose ready-for-listing battery</option>
              {batteries
                .filter((b) => b.state === "READY_FOR_LISTING")
                .map((b) => (
                  <option value={b.id} key={b.id}>
                    {b.internal_id}
                  </option>
                ))}
            </select>
            <button className="primary">Invite offers</button>
          </form>
        </Panel>
      )}
      <div className="split">
        <Panel title="Listings">
          <div className="record-list">
            {listings.length === 0 ? (
              <Empty>
                No eligible listings. An originator must publish a screened
                battery.
              </Empty>
            ) : (
              listings.map((l) => (
                <button
                  key={l.id}
                  className={
                    "record-row " + (selected === l.id ? "selected" : "")
                  }
                  onClick={() => setSelected(l.id)}
                >
                  <span className="battery-avatar">↻</span>
                  <span>
                    <strong>{l.asset.internal_id}</strong>
                    <small>
                      {l.asset.chemistry} · {l.asset.mass_kg ?? "Unknown"} kg ·
                      expires {date(l.expires_at)}
                    </small>
                  </span>
                  <Badge value={l.status} />
                </button>
              ))
            )}
          </div>
        </Panel>
        <Panel
          title={
            listing
              ? listing.asset.internal_id + " · commercial discovery"
              : "Listing detail"
          }
        >
          {!listing ? (
            <Empty>Select a listing.</Empty>
          ) : (
            <>
              <p className="muted">{listing.data.terms}</p>
              {(own || actor.role === "REVIEWER") && (
                <>
                  <h4>Downstream eligibility</h4>
                  {candidates.map((c, i) => (
                    <div key={i} className="candidate">
                      <div>
                        <strong>{c.facility.name}</strong>
                        <small>{human(c.pathway)}</small>
                      </div>
                      <Badge value={c.eligible ? "ELIGIBLE" : "EXCLUDED"} />
                      {c.reasons.length > 0 && (
                        <ul>
                          {c.reasons.map((r, i) => (
                            <li key={i}>
                              <code>{r.code}</code> {r.message}
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  ))}
                </>
              )}
              {actor.role === "BUYER" &&
                eligible.length > 0 &&
                listing.status === "OPEN" && (
                  <>
                    <h4>Submit a synthetic commercial offer</h4>
                    <form
                      onSubmit={async (e) => {
                        e.preventDefault();
                        if (choice)
                          await action("/listings/" + selected + "/offers", {
                            facility_id: choice.facility.id,
                            pathway: choice.pathway,
                            price_paise: Math.round(Number(price) * 100),
                            payer_org_id:
                              payer === "BUYER"
                                ? actor.organisation_id
                                : listing.seller_org_id,
                            budget_paise: Math.round(Number(budget) * 100),
                            expires_at: new Date(
                              Date.now() + 3 * 86400000,
                            ).toISOString(),
                            acceptance_criteria: criteria,
                          });
                      }}
                    >
                      <div className="form-grid">
                        <Field label="Eligible receiving facility">
                          <select
                            value={choice?.facility.id || ""}
                            onChange={(e) => setFacility(e.target.value)}
                          >
                            {eligible.map((c) => (
                              <option key={c.facility.id} value={c.facility.id}>
                                {c.facility.name} · {human(c.pathway)}
                              </option>
                            ))}
                          </select>
                        </Field>
                        <Field label="Gross purchase price · INR">
                          <input
                            type="number"
                            min="0"
                            required
                            value={price}
                            onChange={(e) => setPrice(e.target.value)}
                          />
                        </Field>
                        <Field label="Logistics payer">
                          <select
                            value={payer}
                            onChange={(e) => setPayer(e.target.value)}
                          >
                            <option value="BUYER">Buyer</option>
                            <option value="SELLER">Seller</option>
                          </select>
                        </Field>
                        <Field label="Proposed logistics cap · INR">
                          <input
                            type="number"
                            min="0"
                            required
                            value={budget}
                            onChange={(e) => setBudget(e.target.value)}
                          />
                        </Field>
                      </div>
                      <Field label="Conditional inspection acceptance criteria">
                        <textarea
                          required
                          value={criteria}
                          onChange={(e) => setCriteria(e.target.value)}
                        />
                      </Field>
                      <p className="muted">
                        Conditional on inspection · logistics cost currently
                        unknown · INR per asset record.
                      </p>
                      <button className="primary">Submit offer</button>
                    </form>
                  </>
                )}
              <h4>Offer comparison</h4>
              {offers.length === 0 ? (
                <Empty>
                  No offers submitted yet. Switch to an eligible buyer demo
                  actor to submit one.
                </Empty>
              ) : (
                offers.map((o) => (
                  <div key={o.id} className="offer-card">
                    <div className="card-line">
                      <strong>{money(o.price_paise)}</strong>
                      <Badge value={o.status} />
                    </div>
                    <p>
                      {human(o.pathway)} · {o.buyer_org_id}
                    </p>
                    <dl className="details">
                      <dt>Transport cap</dt>
                      <dd>
                        {money(o.data.budget_paise)} · payer{" "}
                        {o.data.payer_org_id}
                      </dd>
                      <dt>Seller net</dt>
                      <dd>
                        {o.data.payer_org_id === listing.seller_org_id
                          ? "Incomplete — actual logistics cost unknown"
                          : money(o.price_paise) +
                            " before any agreed seller costs"}
                      </dd>
                      <dt>Inspection</dt>
                      <dd>{o.data.acceptance_criteria}</dd>
                      <dt>Expiry</dt>
                      <dd>{date(o.expires_at)}</dd>
                    </dl>
                    {own &&
                      o.status === "SUBMITTED" &&
                      listing.status === "OPEN" && (
                        <button
                          className="primary"
                          onClick={() => action("/offers/" + o.id + "/accept")}
                        >
                          Select offer · create terms v1
                        </button>
                      )}
                  </div>
                ))
              )}
            </>
          )}
        </Panel>
      </div>
    </>
  );
}
