import { useState } from "react";
import type { Network as NetworkData, Actor, Action } from "./types";
import { Panel, Field, Badge, RouteMap, human, date } from "./components";
export function Network({
  network,
  actor,
  action,
}: {
  network: NetworkData;
  actor: Actor;
  action: Action;
}) {
  const [show, setShow] = useState(false);
  const [name, setName] = useState("");
  const [kind, setKind] = useState("RECEIVER");
  const [path, setPath] = useState("RECYCLING");
  const [chem, setChem] = useState("LFP");
  const [mass, setMass] = useState("500");
  const [lat, setLat] = useState("12.97");
  const [lng, setLng] = useState("77.59");
  const [reviewKind, setReviewKind] = useState("capability");
  const [reviewId, setReviewId] = useState("");
  const [status, setStatus] = useState("VERIFIED");
  const [scope, setScope] = useState("ORDINARY");
  const [evidence, setEvidence] = useState("");
  const [reason, setReason] = useState("");
  const records =
    reviewKind === "organisation"
      ? network.organisations
      : reviewKind === "facility"
        ? network.facilities
        : reviewKind === "capability"
          ? network.capabilities
          : network.transporters;
  const selected = records.find((x) => x.id === reviewId) || records[0];
  return (
    <>
      <div className="toolbar">
        <p className="muted">
          Identity, declared capability, scoped verification and current
          availability remain separate.
        </p>
        <button onClick={() => setShow(!show)}>
          {show ? "Hide onboarding" : "Onboard / review participant"}
        </button>
      </div>
      {show && (
        <Panel title="Participant onboarding and scoped review">
          <div className="two-cols">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (actor.role === "TRANSPORTER")
                  action("/transporters", {
                    name,
                    capacity_kg: Number(mass),
                    center: [Number(lat), Number(lng)],
                    radius_km: 250,
                  });
                else if (actor.role === "REVIEWER")
                  action("/organisations", {
                    name,
                    role: kind === "HUB" ? "HUB" : "BUYER",
                    address: "Synthetic participant declared address",
                    contact: evidence,
                  });
                else
                  action("/facilities", {
                    name,
                    kind,
                    lat: Number(lat),
                    lng: Number(lng),
                    pathway: path,
                    chemistries: chem.split(",").map((x) => x.trim()),
                    capacity_kg: Number(mass),
                  });
              }}
            >
              <h4>Create pending record</h4>
              <p className="muted">
                New declarations are unverified and cannot pass matching. A
                reviewer must verify identity and each capability separately.
              </p>
              <Field label="Organisation / facility / transporter name">
                <input
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </Field>
              <div className="form-grid">
                <Field label="Facility kind / organisation role">
                  <select
                    value={kind}
                    onChange={(e) => setKind(e.target.value)}
                  >
                    {["RECEIVER", "HUB", "REVIEW"].map((x) => (
                      <option key={x}>{x}</option>
                    ))}
                  </select>
                </Field>
                <Field label="Declared pathway">
                  <select
                    value={path}
                    onChange={(e) => setPath(e.target.value)}
                  >
                    {[
                      "REPAIR_REFURBISHMENT",
                      "SECOND_LIFE_ASSESSMENT",
                      "RECYCLING",
                      "QUALIFIED_REVIEW",
                    ].map((x) => (
                      <option key={x}>{x}</option>
                    ))}
                  </select>
                </Field>
                <Field label="Chemistries · comma separated">
                  <input
                    value={chem}
                    onChange={(e) => setChem(e.target.value)}
                  />
                </Field>
                <Field label="Declared capacity · kg">
                  <input
                    type="number"
                    min="1"
                    value={mass}
                    onChange={(e) => setMass(e.target.value)}
                  />
                </Field>
                <Field label="Latitude">
                  <input
                    type="number"
                    step="any"
                    value={lat}
                    onChange={(e) => setLat(e.target.value)}
                  />
                </Field>
                <Field label="Longitude">
                  <input
                    type="number"
                    step="any"
                    value={lng}
                    onChange={(e) => setLng(e.target.value)}
                  />
                </Field>
              </div>
              {actor.role === "REVIEWER" && (
                <Field label="Authorised contact · private">
                  <input
                    required
                    value={evidence}
                    onChange={(e) => setEvidence(e.target.value)}
                  />
                </Field>
              )}
              <button>Create pending record</button>
            </form>
            {actor.role === "REVIEWER" && (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  if (selected)
                    action(
                      "/network/" + reviewKind + "/" + selected.id + "/review",
                      {
                        verification: status,
                        valid_until: new Date(
                          Date.now() + 365 * 86400000,
                        ).toISOString(),
                        reason,
                        evidence,
                        chemistries: chem.split(",").map((x) => x.trim()),
                        forms: ["PACK", "MODULE"],
                        conditions:
                          scope === "CONTROLLED_HANDLING"
                            ? ["DAMAGED_REPORTED", "UNKNOWN", "DEGRADED"]
                            : ["WORKING", "DEGRADED", "NON_FUNCTIONAL"],
                        handling_scope: scope,
                        window_start: new Date().toISOString(),
                        window_end: new Date(
                          Date.now() + 90 * 86400000,
                        ).toISOString(),
                      },
                    );
                }}
              >
                <h4>Record a scoped verification decision</h4>
                <Field label="Verification applies to">
                  <select
                    value={reviewKind}
                    onChange={(e) => {
                      setReviewKind(e.target.value);
                      setReviewId("");
                    }}
                  >
                    {[
                      "organisation",
                      "facility",
                      "capability",
                      "transporter",
                    ].map((x) => (
                      <option key={x}>{x}</option>
                    ))}
                  </select>
                </Field>
                <Field label="Record">
                  <select
                    value={selected?.id || ""}
                    onChange={(e) => setReviewId(e.target.value)}
                  >
                    {records.map((x) => (
                      <option value={x.id} key={x.id}>
                        {"name" in x ? x.name : x.id}
                      </option>
                    ))}
                  </select>
                </Field>
                <div className="form-grid">
                  <Field label="Review outcome">
                    <select
                      value={status}
                      onChange={(e) => setStatus(e.target.value)}
                    >
                      {[
                        "VERIFIED",
                        "UNDER_REVIEW",
                        "REJECTED",
                        "SUSPENDED",
                        "EXPIRED",
                      ].map((x) => (
                        <option key={x}>{x}</option>
                      ))}
                    </select>
                  </Field>
                  <Field label="Handling scope">
                    <select
                      value={scope}
                      onChange={(e) => setScope(e.target.value)}
                    >
                      <option>ORDINARY</option>
                      <option>CONTROLLED_HANDLING</option>
                    </select>
                  </Field>
                </div>
                <Field label="Reason">
                  <textarea
                    required
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                  />
                </Field>
                <Field label="Evidence reference">
                  <input
                    required
                    value={evidence}
                    onChange={(e) => setEvidence(e.target.value)}
                  />
                </Field>
                <p className="notice">
                  For capability/transporter verification, chemistries use the
                  left-hand field; form scope is packs/modules. Verification is
                  mock demo data.
                </p>
                <button className="primary">
                  Record review · retain audit history
                </button>
              </form>
            )}
          </div>
        </Panel>
      )}
      <Panel title="Synthetic participant network">
        <RouteMap routes={[]} network={network} />
        <p className="notice">
          Every organisation, registration, capacity and verification shown here
          is fictional demonstration data.
        </p>
        <div className="network-grid">
          {network.facilities.map((f) => (
            <div className="network-card" key={f.id}>
              <div className="card-line">
                <span className="battery-avatar">
                  {f.kind === "HUB" ? "▣" : "↻"}
                </span>
                <Badge value={f.registration} />
              </div>
              <h3>{f.name}</h3>
              <p>{human(f.kind)} · synthetic</p>
              {network.capabilities
                .filter((c) => c.facility_id === f.id)
                .map((c) => (
                  <div className="capability" key={c.id}>
                    <strong>{human(c.pathway)}</strong>
                    <small>
                      Declared: {c.data.declared_chemistries?.join(", ")}
                    </small>
                    <small>
                      Verified mock scope:{" "}
                      {c.data.verified_chemistries?.join(", ")} ·{" "}
                      {c.data.handling_scope}
                    </small>
                    <small>
                      Capacity {c.capacity_kg} kg · declared available{" "}
                      {c.available_kg} kg
                    </small>
                    <small>
                      {human(c.verification)} · validity {date(c.valid_until)}
                    </small>
                  </div>
                ))}
            </div>
          ))}
        </div>
      </Panel>
      <Panel title="Transporter profiles">
        <div className="network-grid">
          {network.transporters.map((t) => (
            <div className="network-card" key={t.id}>
              <h3>{t.name}</h3>
              <Badge value={t.verification} />
              <p>
                {t.capacity_kg} kg · {t.data.radius_km} km coverage
              </p>
              <small>
                {t.data.handling_scope} · synthetic rate {t.data.rate_source}
              </small>
            </div>
          ))}
        </div>
      </Panel>
    </>
  );
}
