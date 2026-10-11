import { hasRole } from "./navigation";
import { useState } from "react";
import type { Action, Actor, Battery, Network } from "./types";
import { useResource } from "./api";
import { RegistrationReviewPanel, EvidenceReview } from "./RegistrationReview";
import { DocumentsInput } from "./RegistrationFields";
import { Intake } from "./Intake";
import { DecisionPanel } from "./DecisionPanel";
import { Badge, Panel, Empty, human, date } from "./components";
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
  const [confirmation, setConfirmation] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [selected, setSelected] = useState("");
  const [edit, setEdit] = useState(false);
  const [creating, setCreating] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [uploadProgress, setUploadProgress] = useState("");
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
        done={(submitted) => {
          if (submitted !== undefined)
            setConfirmation(
              submitted
                ? "Registration submitted. It awaits network-operator approval; pending registrations cannot enter ordinary matching."
                : "Draft saved privately. Complete it and submit for review when ready.",
            );
          setCreating(false);
          setEdit(false);
        }}
      />
    );
  const orgName = (id: string) =>
    network.organisations.find((o) => o.id === id)?.name || id;
  return (
    <>
      {confirmation && (
        <p role="status" className="success-banner">
          {confirmation}
        </p>
      )}
      <div className="toolbar">
        <p className="muted">
          Assets visible to your organisation · durable intake and evidence
          history
        </p>
        {hasRole(actor, "ORIGINATOR") && (
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
          {hasRole(actor, "REVIEWER") && (
            <label>
              Registration queue filter
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="">All registrations</option>
                {[
                  "PENDING_REVIEW",
                  "INFORMATION_REQUESTED",
                  "SPECIALIST_ASSESSMENT",
                  "APPROVED",
                  "REJECTED",
                ].map((x) => (
                  <option key={x}>{x}</option>
                ))}
              </select>
            </label>
          )}
          {batteries.length === 0 ? (
            <Empty>
              Your organisation has no visible battery records yet. Buyers can
              discover eligible assets in Listings.
            </Empty>
          ) : (
            <div className="record-list">
              {batteries
                .filter(
                  (b) =>
                    !statusFilter ||
                    b.data.registration?.status === statusFilter,
                )
                .map((b) => (
                  <button
                    className={
                      "record-row " + (selected === b.id ? "selected" : "")
                    }
                    key={b.id}
                    onClick={() => setSelected(b.id)}
                  >
                    <span className="battery-avatar">↻</span>
                    <span>
                      <strong>
                        {b.data.registration_title || b.internal_id}
                      </strong>
                      <small>
                        {b.chemistry} · {human(b.form)} ·{" "}
                        {b.mass_kg == null ? "Mass unknown" : b.mass_kg + " kg"}
                      </small>
                    </span>
                    <Badge value={b.data.registration?.status || b.state} />
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
            <RegistrationReviewPanel
              key={asset.id}
              asset={asset}
              actor={actor}
              action={action}
              version={version}
            />
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
                <strong>{human(r.code)}</strong>
                <p>{r.message}</p>
                <small>{r.next_action}</small>
              </div>
            ))}
            {hasRole(actor, "ORIGINATOR") &&
              actor.organisation_id === asset.originator_org_id && (
                <div className="actions">
                  <button onClick={() => setEdit(true)}>
                    Revise and resubmit
                  </button>
                  <button
                    className="primary"
                    onClick={() => action("/batteries/" + asset.id + "/screen")}
                  >
                    Check approval and handling gates
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
                <a href={"/api/evidence/" + e.id + "/download"}>
                  Download {e.filename}
                </a>
                {hasRole(actor, "REVIEWER") && (
                  <EvidenceReview id={e.id} kind={e.kind} action={action} />
                )}
                {actor.organisation_id === asset.originator_org_id && (
                  <button
                    onClick={() =>
                      action(
                        `/batteries/${asset.id}/evidence/${e.id}/remove`,
                        {},
                      )
                    }
                  >
                    Remove attachment
                  </button>
                )}
              </div>
            ))}
            {hasRole(actor, "ORIGINATOR") &&
              actor.organisation_id === asset.originator_org_id && (
                <>
                  <form
                    onSubmit={async (e) => {
                      e.preventDefault();
                      if (uploading) return;
                      setUploadError("");
                      if (
                        files.length + (asset.evidence?.length || 0) > 4 ||
                        files.some((f) => f.size > 10 * 1024 * 1024) ||
                        files.reduce((s, f) => s + f.size, 0) +
                          (asset.evidence || []).reduce(
                            (s, f) => s + (f.data.size_bytes || 0),
                            0,
                          ) >
                          25 * 1024 * 1024
                      ) {
                        setUploadError(
                          "Use at most four files, 10 MB each and 25 MB total.",
                        );
                        return;
                      }
                      setUploading(true);
                      try {
                        for (let i = 0; i < files.length; i++) {
                          setUploadProgress(
                            `Uploading ${i + 1} of ${files.length}`,
                          );
                          const f = new FormData();
                          f.append("file", files[i]);
                          if (
                            !(await action(
                              `/batteries/${asset.id}/evidence`,
                              f,
                            ))
                          )
                            return;
                        }
                        setFiles([]);
                        setUploadProgress("Attachments saved.");
                      } finally {
                        setUploading(false);
                      }
                    }}
                  >
                    <DocumentsInput
                      files={files}
                      onChange={setFiles}
                      error={uploadError}
                    />
                    <p role="status">{uploadProgress}</p>
                    <button disabled={uploading || !files.length}>
                      Save attachments
                    </button>
                  </form>
                  <h4>Transfer authorization · commercial stage</h4>
                  <p className="muted">
                    Upload any available authorization evidence using the
                    generic field. The operator classifies and reviews it before
                    commercial commitments.
                  </p>
                  <button
                    onClick={() =>
                      action(
                        `/batteries/${asset.id}/confirm-transfer-authority`,
                        {},
                      )
                    }
                  >
                    Confirm transfer authority against reviewed evidence
                  </button>
                </>
              )}
            {asset.dispositions?.length ? (
              <>
                <h4>Recorded outcomes</h4>
                {asset.dispositions.map((d) => (
                  <div key={d.id} className="evidence">
                    <strong>
                      {human(d.data.outcome || String((d as any).outcome))}
                    </strong>
                    <small>{d.data.evidence} · Owner-reported evidence</small>
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
      {asset && (
        <DecisionPanel
          key={asset.id}
          assetId={asset.id}
          actor={actor}
          version={version}
        />
      )}
    </>
  );
}
