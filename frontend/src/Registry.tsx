import { useState } from "react";
import type { Action, Actor, Battery, Network } from "./types";
import { useResource } from "./api";
import { Intake } from "./Intake";
import { Badge, Panel, Field, Empty, human, date } from "./components";
export function Registry({
  batteries,
  network,
  actor,
  action,
  version,
  fields,
}: {
  batteries: Battery[];
  network: Network;
  actor: Actor;
  action: Action;
  version: number;
  fields: Record<string, string>;
}) {
  const [selected, setSelected] = useState("");
  const [edit, setEdit] = useState(false);
  const [creating, setCreating] = useState(false);
  const [kind, setKind] = useState("TRANSFER_AUTHORITY");
  const [reference, setReference] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const { data: asset } = useResource<Battery | null>(
    selected ? "/batteries/" + selected : null,
    version,
    null,
  );
  if (creating || (edit && asset))
    return (
      <Intake
        key={asset?.id || "new"}
        asset={creating ? undefined : asset!}
        org={actor.organisation_id}
        network={network}
        action={action}
        fields={fields}
        done={() => {
          setCreating(false);
          setEdit(false);
        }}
      />
    );
  const orgName = (id: string) =>
    network.organisations.find((o) => o.id === id)?.name || id;
  return (
    <>
      <div className="toolbar">
        <p className="muted">
          Assets visible to your organisation · durable intake and evidence
          history
        </p>
        {actor.role === "ORIGINATOR" && (
          <button className="primary" onClick={() => setCreating(true)}>
            + Register battery
          </button>
        )}
      </div>
      <div className="split">
        <Panel
          title="Battery registry"
          aside={<span className="count">{batteries.length}</span>}
        >
          {batteries.length === 0 ? (
            <Empty>
              No assets visible to this actor. Buyers can discover eligible
              assets in Listings.
            </Empty>
          ) : (
            <div className="record-list">
              {batteries.map((b) => (
                <button
                  className={
                    "record-row " + (selected === b.id ? "selected" : "")
                  }
                  key={b.id}
                  onClick={() => setSelected(b.id)}
                >
                  <span className="battery-avatar">↻</span>
                  <span>
                    <strong>{b.internal_id}</strong>
                    <small>
                      {b.chemistry} · {human(b.form)} ·{" "}
                      {b.mass_kg == null ? "Mass unknown" : b.mass_kg + " kg"}
                    </small>
                  </span>
                  <Badge value={b.state} />
                </button>
              ))}
            </div>
          )}
        </Panel>
        {asset ? (
          <Panel
            title={asset.internal_id}
            aside={<Badge value={asset.state} />}
          >
            <dl className="details">
              <dt>Legal owner</dt>
              <dd>{orgName(asset.owner_org_id)}</dd>
              <dt>Physical holder</dt>
              <dd>
                {asset.data.custody_segments?.length > 1
                  ? "Mixed custody"
                  : orgName(asset.current_holder_org_id)}
                {asset.data.custody_segments?.length > 1 && (
                  <ul>
                    {asset.data.custody_segments.map(
                      (segment: any, i: number) => (
                        <li key={i}>
                          {segment.quantity} unit(s) · {orgName(segment.holder)}
                        </li>
                      ),
                    )}
                  </ul>
                )}
              </dd>
              <dt>Handling scope</dt>
              <dd>
                {asset.data.handling_clearance
                  ? "Scoped controlled handling · qualified report and expiry apply"
                  : "No qualified clearance recorded"}
              </dd>
              <dt>Condition</dt>
              <dd>{human(asset.condition)}</dd>
              <dt>Provenance</dt>
              <dd>
                {human(asset.data.provenance || "UNKNOWN")} ·{" "}
                {date(asset.data.recorded_at)}
              </dd>
              <dt>Pickup</dt>
              <dd>{asset.data.address || "Unknown"}</dd>
              <dt>Window</dt>
              <dd>
                {date(asset.data.window_start)} — {date(asset.data.window_end)}
              </dd>
              <dt>Authority</dt>
              <dd>
                {asset.authority_confirmed
                  ? "Declared; evidence required"
                  : "Unconfirmed"}
              </dd>
            </dl>
            <div className="notice">
              Operational screening only. This platform does not diagnose or
              certify battery safety.
            </div>
            {asset.data.screening?.reasons?.map((r: any) => (
              <div className="reason" key={r.code}>
                <strong>{r.code}</strong>
                <p>{r.message}</p>
                <small>{r.next_action}</small>
              </div>
            ))}
            {actor.role === "ORIGINATOR" &&
              actor.organisation_id === asset.originator_org_id && (
                <div className="actions">
                  <button onClick={() => setEdit(true)}>
                    Edit draft/intake
                  </button>
                  <button
                    className="primary"
                    onClick={() => action("/batteries/" + asset.id + "/screen")}
                  >
                    Run screening
                  </button>
                </div>
              )}
            <h4>Evidence · versioned</h4>
            {asset.evidence?.map((e) => (
              <div className="evidence" key={e.id}>
                <strong>
                  {human(e.kind)} <small>v{e.version}</small>
                </strong>
                <span>{e.filename}</span>
                <small>{e.data.reference || e.checksum.slice(0, 20)}</small>
                <Badge value={e.review_status} />
                {actor.role === "REVIEWER" && (
                  <button
                    onClick={() =>
                      action("/evidence/" + e.id + "/review", {
                        status: "VERIFIED",
                        reason:
                          "Reviewed submitted demo transfer-authority evidence",
                        evidence: e.data.reference || e.checksum,
                      })
                    }
                  >
                    Record mock evidence review
                  </button>
                )}
              </div>
            ))}
            {actor.role === "ORIGINATOR" && (
              <form
                onSubmit={async (e) => {
                  e.preventDefault();
                  const form = new FormData();
                  form.append("kind", kind);
                  form.append("reference", reference);
                  if (file) form.append("file", file);
                  if (
                    await action("/batteries/" + asset.id + "/evidence", form)
                  ) {
                    setReference("");
                    setFile(null);
                  }
                }}
              >
                <div className="form-grid">
                  <Field label="Evidence type">
                    <select
                      value={kind}
                      onChange={(e) => setKind(e.target.value)}
                    >
                      {[
                        "TRANSFER_AUTHORITY",
                        "PHOTO",
                        "SERVICE_REPORT",
                        "TEST_REPORT",
                        "INVOICE",
                        "OTHER",
                      ].map((x) => (
                        <option key={x}>{x}</option>
                      ))}
                    </select>
                  </Field>
                  <Field label="Reference / synthetic evidence description">
                    <input
                      value={reference}
                      onChange={(e) => setReference(e.target.value)}
                      required={!file}
                    />
                  </Field>
                </div>
                <Field label="Optional attachment · PDF, image or text, max 5 MiB">
                  <input
                    type="file"
                    accept=".pdf,.png,.jpg,.jpeg,.txt"
                    onChange={(e) => setFile(e.target.files?.[0] || null)}
                  />
                </Field>
                <button>Add evidence version</button>
              </form>
            )}
            {asset.dispositions?.length ? (
              <>
                <h4>Recorded outcomes</h4>
                {asset.dispositions.map((d) => (
                  <div key={d.id} className="evidence">
                    <strong>
                      {human(d.data.outcome || String((d as any).outcome))}
                    </strong>
                    <small>
                      {d.data.evidence} · self-reported synthetic evidence
                    </small>
                  </div>
                ))}
              </>
            ) : null}
          </Panel>
        ) : (
          <Panel title="Asset detail">
            <Empty>
              Select a battery to inspect intake, custody and evidence.
            </Empty>
          </Panel>
        )}
      </div>
    </>
  );
}
