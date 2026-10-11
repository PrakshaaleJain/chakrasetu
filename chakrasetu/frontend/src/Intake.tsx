import { useState } from "react";
import type { Action, Battery, Network } from "./types";
import { Field, Panel, human } from "./components";
import { PBSCards, DocumentsInput } from "./RegistrationFields";
import {
  applicationTypes,
  chemistryOptions,
  conditionOptions,
  categoryOptions,
  blankInspection,
} from "./registrationTypes";
import type {
  RegistrationInput,
  ReportedInspection,
} from "./registrationTypes";
interface Props {
  asset?: Battery;
  org: string;
  network: Network;
  action: Action;
  fields: Record<string, string>;
  done: (submitted?: boolean) => void;
}
export function Intake({ asset, org, action, fields, done }: Props) {
  const defaults: RegistrationInput = {
    internal_id:
      asset?.internal_id || "BAT-" + crypto.randomUUID().slice(0, 12),
    registration_title: asset?.internal_id || "",
    form: "UNKNOWN",
    application_type: "UNKNOWN",
    quantity: 1,
    address: "",
    lat: null,
    lng: null,
    removal_date: null,
    removal_reason: "unknown",
    condition: "UNKNOWN",
    manufacturer: null,
    model: null,
    serial_number: null,
    chemistry: "UNKNOWN",
    manufacturing_date: null,
    manufacturing_year: null,
    nominal_voltage: null,
    nominal_capacity_ah: null,
    rated_energy_kwh: null,
    mass_kg: null,
    age_years: null,
    bms_available: "UNKNOWN",
    other_specifications: null,
    inspection: { ...blankInspection },
    pbs: null,
    pbs_comments: "",
    current_owner: null,
    current_custodian: null,
    collection_availability: "TO_BE_CONFIRMED",
    preferred_timeframe: null,
    handling_instructions: null,
    additional_information: "",
    mixed_batch: false,
    owner_org_id: org,
    custodian_org_id: org,
    authority_confirmed: false,
    window_start: null,
    window_end: null,
  };
  const [form, setForm] = useState<RegistrationInput>(() => {
    if (!asset) return defaults;
    const d = { ...defaults };
    for (const k of Object.keys(defaults) as (keyof RegistrationInput)[])
      if (asset.data[k] !== undefined) Object.assign(d, { [k]: asset.data[k] });
    return {
      ...d,
      internal_id: asset.internal_id,
      owner_org_id: asset.owner_org_id,
      custodian_org_id: asset.custodian_org_id,
      chemistry: asset.chemistry,
      form: asset.form,
      condition: asset.condition,
      quantity: asset.quantity,
      mass_kg: asset.mass_kg,
      lat: asset.lat,
      lng: asset.lng,
      authority_confirmed: asset.authority_confirmed,
      flags: asset.data.flags,
      inspection: { ...blankInspection, ...asset.data.inspection },
    };
  });
  const [files, setFiles] = useState<File[]>([]),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [savedId, setSavedId] = useState(asset?.id || ""),
    [progress, setProgress] = useState("");
  function set<K extends keyof RegistrationInput>(
    key: K,
    value: RegistrationInput[K],
  ) {
    setForm((f) => ({ ...f, [key]: value }));
  }
  function test<K extends keyof ReportedInspection>(
    key: K,
    value: ReportedInspection[K],
  ) {
    set("inspection", { ...form.inspection, [key]: value });
  }
  const selects = (
    key: keyof RegistrationInput,
    label: string,
    options: string[],
  ) => (
    <Field label={label} error={fields[key]}>
      <select
        value={String(form[key] ?? "")}
        onChange={(e) => set(key, e.target.value as never)}
      >
        {options.map((x) => (
          <option key={x} value={x}>
            {x === "NON_FUNCTIONAL"
              ? "Faulty"
              : x === "DAMAGED_REPORTED"
                ? "Damaged"
                : human(x)}
          </option>
        ))}
      </select>
    </Field>
  );
  function input(
    key: keyof RegistrationInput,
    label: string,
    type = "text",
    required = false,
  ) {
    return (
      <Field label={label} error={fields[key]}>
        <input
          type={type}
          required={required}
          step={type === "number" ? "any" : undefined}
          value={(form[key] as string | number) ?? ""}
          onChange={(e) =>
            set(
              key,
              (e.target.value === ""
                ? ["registration_title", "address", "internal_id"].includes(key)
                  ? ""
                  : null
                : type === "number"
                  ? Number(e.target.value)
                  : e.target.value) as never,
            )
          }
        />
      </Field>
    );
  }
  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (busy) return;
    setError("");
    const draft = Boolean(
      (e.nativeEvent as SubmitEvent).submitter?.getAttribute("data-draft"),
    );
    if (!draft && !form.pbs) {
      setError("Select a Perceived Battery Safety level.");
      return;
    }
    const existing = (asset?.evidence || []).reduce(
      (n, f) => n + (f.data.removed ? 0 : 1),
      0,
    );
    if (
      files.length + existing > 4 ||
      files.some((f) => f.size > 10 * 1024 * 1024) ||
      files.reduce((n, f) => n + f.size, 0) +
        (asset?.evidence || []).reduce(
          (n, f) => n + (f.data.size_bytes || 0),
          0,
        ) >
        25 * 1024 * 1024
    ) {
      setError(
        "Use up to four files, at most 10 MB each and 25 MB total. Remove existing files in the registry before replacements.",
      );
      return;
    }
    setBusy(true);
    try {
      const r = await action(
        (savedId ? "/batteries/" + savedId : "/batteries") +
          (draft ? "?draft=true" : ""),
        form,
        savedId ? "PATCH" : "POST",
      );
      if (!r) return;
      setSavedId(r.id);
      for (let i = 0; i < files.length; i++) {
        setProgress(`Uploading ${i + 1} of ${files.length}: ${files[i].name}`);
        const fd = new FormData();
        fd.append("file", files[i]);
        if (!(await action("/batteries/" + r.id + "/evidence", fd))) {
          setError(
            "The registration is saved. An attachment failed; retry or remove it. Already uploaded files will not be duplicated.",
          );
          return;
        }
      }
      setProgress(
        draft
          ? "Draft saved privately."
          : "Registration submitted for network-operator approval.",
      );
      done(!draft);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Panel
      title={asset ? "Revise and resubmit registration" : "Register a battery"}
    >
      <form onSubmit={save}>
        <p className="notice">
          Register using available information. Registration does not transfer
          ownership or custody. Transfer authorization is checked when
          commercial commitments and movement are arranged.
        </p>
        {error && (
          <p role="alert" className="error-banner">
            {error}
          </p>
        )}
        {progress && <p role="status">{progress}</p>}
        <h3>A. Basic information</h3>
        <div className="form-grid">
          {input("registration_title", "Registration title", "text", true)}
          {selects("form", "Battery category", categoryOptions)}
          {selects(
            "application_type",
            "Vehicle/application type",
            applicationTypes,
          )}
          {input("quantity", "Number of batteries", "number", true)}
          {input("address", "Current location/address", "text", true)}
          {input("lat", "Latitude", "number", true)}
          {input("lng", "Longitude", "number", true)}
          {input("removal_date", "Battery removal date", "date")}
          {selects("removal_reason", "Reason for removal", [
            "end-of-life",
            "degradation",
            "fault",
            "impact/accident",
            "upgrade/replacement",
            "other",
            "unknown",
          ])}
          {selects("condition", "Current condition", conditionOptions)}
        </div>
        {form.quantity > 1 && (
          <label className="checks">
            <input
              type="checkbox"
              checked={form.mixed_batch}
              onChange={(e) => set("mixed_batch", e.target.checked)}
            />{" "}
            This batch has differing specifications or safety conditions. It
            will remain held until separated into individual or homogeneous
            registrations. Sample measurements never apply to every battery.
          </label>
        )}
        <details>
          <summary>B. Battery specifications · optional</summary>
          <div className="form-grid">
            {input("manufacturer", "Manufacturer/brand")}
            {input("model", "Battery model")}
            {input("serial_number", "Serial number or identifier")}
            {selects("chemistry", "Battery chemistry", chemistryOptions)}
            {input("manufacturing_date", "Manufacturing date", "date")}
            {input("manufacturing_year", "Manufacturing year", "number")}
            {input("nominal_voltage", "Rated voltage (V)", "number")}
            {input("nominal_capacity_ah", "Rated capacity (Ah)", "number")}
            {input("rated_energy_kwh", "Rated energy (kWh)", "number")}
            {input("mass_kg", "Approximate total batch weight (kg)", "number")}
            {input("age_years", "Battery age (years)", "number")}
            {selects("bms_available", "BMS availability", [
              "YES",
              "NO",
              "UNKNOWN",
            ])}
            {input("other_specifications", "Other known specifications")}
          </div>
        </details>
        <h3>C. Inspection and test results</h3>
        <Field label="Have any inspections or tests been conducted on this battery?">
          <select
            value={form.inspection.conducted}
            onChange={(e) =>
              set(
                "inspection",
                e.target.value === "YES"
                  ? { ...form.inspection, conducted: "YES" }
                  : {
                      ...blankInspection,
                      conducted: e.target.value as "NO" | "UNKNOWN",
                    },
              )
            }
          >
            {["UNKNOWN", "NO", "YES"].map((x) => (
              <option key={x}>{x}</option>
            ))}
          </select>
        </Field>
        {form.inspection.conducted === "YES" && (
          <div className="form-grid">
            <Field label="Inspection date">
              <input
                type="date"
                value={form.inspection.date || ""}
                onChange={(e) => test("date", e.target.value || null)}
              />
            </Field>
            <Field label="Person conducting inspection">
              <input
                value={form.inspection.inspector || ""}
                onChange={(e) => test("inspector", e.target.value || null)}
              />
            </Field>
            <Field label="Information source">
              <select
                value={form.inspection.source}
                onChange={(e) =>
                  test("source", e.target.value as ReportedInspection["source"])
                }
              >
                {[
                  "UNKNOWN",
                  "MEASURED",
                  "BMS_REPORTED",
                  "ESTIMATED",
                  "OTHER_REPORTED",
                ].map((x) => (
                  <option key={x}>{x}</option>
                ))}
              </select>
            </Field>
            <Field label="Measurement applies to">
              <select
                value={form.inspection.scope}
                onChange={(e) =>
                  test("scope", e.target.value as ReportedInspection["scope"])
                }
              >
                {(form.quantity > 1
                  ? ["UNKNOWN", "SAMPLE_ONLY"]
                  : ["UNKNOWN", "INDIVIDUAL"]
                ).map((x) => (
                  <option key={x}>{x}</option>
                ))}
              </select>
            </Field>
            {(
              [
                ["soh_percent", "SoH (%)"],
                ["soc_percent", "SoC (%)"],
                ["voltage_v", "Measured voltage (V)"],
                ["capacity_ah", "Measured capacity (Ah)"],
                ["resistance", "Resistance/impedance"],
                ["imbalance_v", "Cell/module imbalance (V)"],
              ] as const
            ).map(([k, l]) => (
              <Field key={k} label={l}>
                <input
                  type="number"
                  step="any"
                  min="0"
                  max={k.endsWith("percent") ? 100 : undefined}
                  value={form.inspection[k] ?? ""}
                  onChange={(e) =>
                    test(
                      k,
                      e.target.value === "" ? null : Number(e.target.value),
                    )
                  }
                />
              </Field>
            ))}
            <Field label="Resistance unit">
              <select
                value={form.inspection.resistance_unit}
                onChange={(e) => test("resistance_unit", e.target.value)}
              >
                {["UNKNOWN", "OHM", "MILLIOHM"].map((x) => (
                  <option key={x}>{x}</option>
                ))}
              </select>
            </Field>
            {(
              [
                ["resistance_method", "Measurement method"],
                ["temperature", "Temperature observations"],
                ["fault_codes", "BMS fault codes"],
                ["findings", "Physical findings"],
                [
                  "charge_discharge_results",
                  "Charging/discharging test results",
                ],
                ["other_tests", "Other tests conducted"],
              ] as const
            ).map(([k, l]) => (
              <Field key={k} label={l}>
                <textarea
                  value={form.inspection[k] || ""}
                  onChange={(e) => test(k, e.target.value || null)}
                />
              </Field>
            ))}
          </div>
        )}
        <PBSCards value={form.pbs} onChange={(v) => set("pbs", v)} />
        <Field label="Additional safety observations · optional">
          <textarea
            maxLength={4000}
            value={form.pbs_comments}
            onChange={(e) => set("pbs_comments", e.target.value)}
          />
        </Field>
        <h3>D. Ownership and handling</h3>
        <div className="form-grid">
          {input("current_owner", "Current owner, if different · optional")}
          {input(
            "current_custodian",
            "Current custodian, if different · optional",
          )}
          {selects("collection_availability", "Availability for collection", [
            "YES",
            "NO",
            "TO_BE_CONFIRMED",
          ])}
          {input(
            "preferred_timeframe",
            "Preferred collection timeframe · optional",
          )}
          {(["window_start", "window_end"] as const).map((k) => (
            <Field
              key={k}
              label={
                k === "window_start"
                  ? "Collection window start · optional"
                  : "Collection window end · optional"
              }
            >
              <input
                type="datetime-local"
                value={
                  form[k]
                    ? new Date(
                        new Date(form[k]!).getTime() -
                          new Date(form[k]!).getTimezoneOffset() * 60000,
                      )
                        .toISOString()
                        .slice(0, 16)
                    : ""
                }
                onChange={(e) =>
                  set(
                    k,
                    e.target.value
                      ? new Date(e.target.value).toISOString()
                      : null,
                  )
                }
              />
            </Field>
          ))}
        </div>
        <Field label="Handling instructions or known hazards · optional">
          <textarea
            maxLength={4000}
            value={form.handling_instructions || ""}
            onChange={(e) =>
              set("handling_instructions", e.target.value || null)
            }
          />
        </Field>
        <DocumentsInput files={files} onChange={setFiles} />
        <Field label="Additional information">
          <textarea
            maxLength={4000}
            value={form.additional_information}
            onChange={(e) => set("additional_information", e.target.value)}
          />
        </Field>
        <p className="muted">
          Enter any other information that may help us understand the battery's
          condition, history, availability, or handling requirements.
        </p>
        <button className="primary" disabled={busy}>
          {busy ? "Saving registration…" : "Submit for network-operator review"}
        </button>
        <button type="submit" formNoValidate data-draft="true" disabled={busy}>
          Save draft
        </button>
        <button type="button" disabled={busy} onClick={() => done()}>
          Cancel
        </button>
      </form>
    </Panel>
  );
}
