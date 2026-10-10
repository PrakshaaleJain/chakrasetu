import { useState } from "react";
import type { Action, Battery, Network } from "./types";
import { FLAGS } from "./types";
import { Field, Panel, human } from "./components";
interface Props {
  asset?: Battery;
  org: string;
  network: Network;
  action: Action;
  fields: Record<string, string>;
  done: () => void;
}
export function Intake({ asset, org, network, action, fields, done }: Props) {
  const [form, setForm] = useState<any>(
    asset
      ? {
          internal_id: asset.internal_id,
          owner_org_id: asset.owner_org_id,
          custodian_org_id: asset.custodian_org_id,
          chemistry: asset.chemistry,
          form: asset.form,
          condition: asset.condition,
          mass_kg: asset.mass_kg,
          quantity: asset.quantity,
          lat: asset.lat,
          lng: asset.lng,
          authority_confirmed: asset.authority_confirmed,
          removal_reason: asset.data.removal_reason || "unknown",
          address: asset.data.address || "",
          access_notes: asset.data.access_notes || "",
          flags: asset.data.flags,
          notes: asset.data.notes || "",
          declaration: asset.data.declaration,
          window_start: asset.data.window_start,
          window_end: asset.data.window_end,
          provenance: asset.data.provenance || "SELF_DECLARED",
        }
      : {
          internal_id: "",
          owner_org_id: org,
          custodian_org_id: org,
          chemistry: "UNKNOWN",
          form: "PACK",
          condition: "UNKNOWN",
          mass_kg: null,
          quantity: 1,
          lat: 12.9716,
          lng: 77.5946,
          authority_confirmed: false,
          removal_reason: "unknown",
          address: "",
          access_notes: "",
          flags: Object.fromEntries(FLAGS.map((f) => [f, "UNKNOWN"])),
          notes: "",
          declaration: false,
          window_start: new Date(Date.now() + 86400000).toISOString(),
          window_end: new Date(Date.now() + 3 * 86400000).toISOString(),
          provenance: "SELF_DECLARED",
        },
  );
  function set(key: string, value: any) {
    setForm({ ...form, [key]: value });
  }
  async function save(e: React.FormEvent) {
    e.preventDefault();
    const r = await action(
      asset ? "/batteries/" + asset.id : "/batteries",
      form,
      asset ? "PATCH" : "POST",
    );
    if (r) done();
  }
  return (
    <Panel
      title={
        asset ? "Update intake · history retained" : "Register a battery asset"
      }
    >
      <form onSubmit={save}>
        <div className="form-grid">
          <Field label="Internal asset ID *" error={fields.internal_id}>
            <input
              required
              value={form.internal_id}
              onChange={(e) => set("internal_id", e.target.value)}
            />
          </Field>
          {(["owner_org_id", "custodian_org_id"] as const).map((key) => (
            <Field
              key={key}
              label={
                key === "owner_org_id"
                  ? "Legal owner *"
                  : "Physical custodian *"
              }
            >
              <select
                value={form[key]}
                disabled={!!asset}
                onChange={(e) => set(key, e.target.value)}
              >
                {network.organisations.map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.name}
                  </option>
                ))}
              </select>
            </Field>
          ))}
          <Field label="Chemistry *">
            <select
              value={form.chemistry}
              onChange={(e) => set("chemistry", e.target.value)}
            >
              {[
                "UNKNOWN",
                "LFP",
                "NMC",
                "NCA",
                "LCO",
                "LMO",
                "lead-acid",
                "NiMH",
                "other",
              ].map((x) => (
                <option key={x}>{x}</option>
              ))}
            </select>
          </Field>
          <Field label="Form *">
            <select
              value={form.form}
              onChange={(e) => set("form", e.target.value)}
            >
              {["UNKNOWN", "PACK", "MODULE", "CELL", "LOOSE_COMPONENT"].map(
                (x) => (
                  <option key={x}>{x}</option>
                ),
              )}
            </select>
          </Field>
          <Field label="Reported condition *">
            <select
              value={form.condition}
              onChange={(e) => set("condition", e.target.value)}
            >
              {[
                "UNKNOWN",
                "WORKING",
                "DEGRADED",
                "NON_FUNCTIONAL",
                "DAMAGED_REPORTED",
              ].map((x) => (
                <option key={x}>{x}</option>
              ))}
            </select>
          </Field>
          <Field
            label="Total mass (kg) · blank means UNKNOWN"
            error={fields.mass_kg}
          >
            <input
              type="number"
              step="0.01"
              min="0.01"
              value={form.mass_kg ?? ""}
              onChange={(e) =>
                set(
                  "mass_kg",
                  e.target.value === "" ? null : Number(e.target.value),
                )
              }
            />
          </Field>
          <Field label="Quantity *" error={fields.quantity}>
            <input
              type="number"
              min="1"
              required
              value={form.quantity}
              onChange={(e) => set("quantity", Number(e.target.value))}
            />
          </Field>
          <Field label="Removal reason *">
            <select
              value={form.removal_reason}
              onChange={(e) => set("removal_reason", e.target.value)}
            >
              {[
                "degradation",
                "fault",
                "impact/accident",
                "maintenance replacement",
                "end-of-life",
                "unknown",
                "other",
              ].map((x) => (
                <option key={x}>{x}</option>
              ))}
            </select>
          </Field>
          <Field label="Pickup address">
            <input
              value={form.address}
              onChange={(e) => set("address", e.target.value)}
            />
          </Field>
          {["lat", "lng"].map((key) => (
            <Field
              key={key}
              label={key === "lat" ? "Pickup latitude" : "Pickup longitude"}
            >
              <input
                type="number"
                step="any"
                value={form[key] ?? ""}
                onChange={(e) =>
                  set(
                    key,
                    e.target.value === "" ? null : Number(e.target.value),
                  )
                }
              />
            </Field>
          ))}
          {["window_start", "window_end"].map((key) => (
            <Field
              key={key}
              label={
                key === "window_start"
                  ? "Pickup window begins · local time"
                  : "Window ends · local time"
              }
            >
              <input
                type="datetime-local"
                value={
                  form[key]
                    ? new Date(
                        new Date(form[key]).getTime() -
                          new Date(form[key]).getTimezoneOffset() * 60000,
                      )
                        .toISOString()
                        .slice(0, 16)
                    : ""
                }
                onChange={(e) =>
                  set(
                    key,
                    e.target.value
                      ? new Date(e.target.value).toISOString()
                      : null,
                  )
                }
              />
            </Field>
          ))}
          <Field label="Loading and access notes">
            <input
              value={form.access_notes}
              onChange={(e) => set("access_notes", e.target.value)}
            />
          </Field>
        </div>
        <h4>Incident history</h4>
        <p className="muted">
          Answer every item. No flag reported is not a safety certification. Do
          not open or test a pack to complete this form.
        </p>
        <div className="flag-grid">
          {FLAGS.map((f) => (
            <Field key={f} label={human(f)}>
              <select
                value={form.flags[f]}
                onChange={(e) =>
                  set("flags", { ...form.flags, [f]: e.target.value })
                }
              >
                {["UNKNOWN", "NO", "YES"].map((x) => (
                  <option key={x}>{x}</option>
                ))}
              </select>
            </Field>
          ))}
        </div>
        <Field label="Supporting notes">
          <textarea
            value={form.notes}
            onChange={(e) => set("notes", e.target.value)}
          />
        </Field>
        <div className="checks">
          <label>
            <input
              type="checkbox"
              checked={form.authority_confirmed}
              onChange={(e) => set("authority_confirmed", e.target.checked)}
            />{" "}
            I confirm authority to transfer. Supporting evidence is required
            before listing.
          </label>
          <label>
            <input
              type="checkbox"
              checked={form.declaration}
              onChange={(e) => set("declaration", e.target.checked)}
            />{" "}
            I confirm this declaration records the information currently
            available to me.
          </label>
        </div>
        <button className="primary">Save intake</button>
        <button type="button" onClick={done}>
          Cancel
        </button>
      </form>
    </Panel>
  );
}
