import { useState } from "react";
import { Field, human, Badge } from "./components";
import type { SafetyScope } from "./registrationTypes";
import {
  blankSafety,
  applicationTypes,
  chemistryOptions,
  categoryOptions,
  conditionOptions,
} from "./registrationTypes";
import type { CapabilitySummary } from "./organisationTypes";
import type { Action } from "./types";
export function MultiChoices({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: string[];
  value: string[];
  onChange: (v: string[]) => void;
}) {
  return (
    <fieldset>
      <legend>{label}</legend>
      <div className="checks">
        {options.map((x) => (
          <label key={x}>
            <input
              type="checkbox"
              checked={value.includes(x)}
              onChange={(e) =>
                onChange(
                  e.target.checked
                    ? [...value, x]
                    : value.filter((v) => v !== x),
                )
              }
            />
            {human(x)}
          </label>
        ))}
      </div>
    </fieldset>
  );
}
export function SafetyScopeEditor({
  scope,
  onChange,
  kind,
  showTechnical = false,
}: {
  showTechnical?: boolean;
  scope: SafetyScope;
  onChange: (s: SafetyScope) => void;
  kind: string;
}) {
  return (
    <section>
      <h4>Activity-specific battery acceptance</h4>
      {showTechnical && (
        <>
          <MultiChoices
            label="Currently accepted chemistries"
            options={chemistryOptions}
            value={scope.chemistries || []}
            onChange={(v) => onChange({ ...scope, chemistries: v })}
          />
          <MultiChoices
            label="Currently accepted categories"
            options={categoryOptions}
            value={scope.formats || []}
            onChange={(v) => onChange({ ...scope, formats: v })}
          />
          <MultiChoices
            label="Currently supported conditions"
            options={conditionOptions}
            value={scope.conditions || []}
            onChange={(v) => onChange({ ...scope, conditions: v })}
          />
        </>
      )}
      <p className="muted">
        Declarations are separate from reviewed qualifications. Transport scope
        does not authorize repair, processing or emergency response.
      </p>
      <Field label="Maximum PBS claimed for this activity">
        <select
          value={scope.max_pbs || ""}
          onChange={(e) =>
            onChange({
              ...scope,
              max_pbs: (e.target.value || null) as SafetyScope["max_pbs"],
            })
          }
        >
          <option value="">Unknown / not declared</option>
          {["L1", "L2", "L3", "L4", "L5"].map((x) => (
            <option key={x}>{x}</option>
          ))}
        </select>
      </Field>
      <MultiChoices
        label="Accepted applications"
        options={applicationTypes}
        value={scope.application_types}
        onChange={(v) => onChange({ ...scope, application_types: v })}
      />
      {(
        [
          "specialist_assessment",
          "damaged_handling",
          "critical_hazard_handling",
          ...(kind === "TRANSPORT" ? ["dangerous_goods"] : []),
        ] as (keyof SafetyScope)[]
      ).map((k) => (
        <label className="checks" key={k}>
          <input
            type="checkbox"
            checked={Boolean(scope[k])}
            onChange={(e) => onChange({ ...scope, [k]: e.target.checked })}
          />
          {k === "specialist_assessment" && kind === "TRANSPORT"
            ? "Handling during transport to specialist assessment"
            : human(k)}
        </label>
      ))}
      <Field label="Collection/service areas · comma separated, blank defers to existing geographic constraints">
        <input
          value={scope.service_areas.join(", ")}
          onChange={(e) =>
            onChange({
              ...scope,
              service_areas: e.target.value
                .split(",")
                .map((x) => x.trim())
                .filter(Boolean),
            })
          }
        />
      </Field>
      <Field label="Technical restrictions / acceptance conditions">
        <textarea
          maxLength={2000}
          value={scope.restrictions}
          onChange={(e) => onChange({ ...scope, restrictions: e.target.value })}
        />
      </Field>
    </section>
  );
}
export function CapabilityDeclaration({
  capability: c,
  org,
  action,
}: {
  capability: CapabilitySummary;
  org: string;
  action: Action;
}) {
  const [scope, setScope] = useState<SafetyScope>({
      ...blankSafety,
      ...c.scope.declared_safety,
      chemistries: c.scope.declared_safety?.chemistries ?? c.scope.chemistries,
      formats: c.scope.declared_safety?.formats ?? c.scope.formats,
      conditions:
        c.scope.declared_safety?.conditions ?? c.scope.conditions ?? [],
    }),
    [open, setOpen] = useState(false);
  if (
    c.id.startsWith("request:") ||
    !["PATHWAY", "TRANSPORT", "OPERATION"].includes(c.kind)
  )
    return null;
  return (
    <details open={open} onToggle={(e) => setOpen(e.currentTarget.open)}>
      <summary>Maintain {human(c.name)} acceptance declaration</summary>
      <p>
        Reviewed maximum PBS: {c.scope.verified_safety?.max_pbs || "Unknown"}{" "}
        <Badge value={c.status} />
      </p>
      <p>
        Limits you reduce take effect immediately. Expansion requires a scope
        modification request and operator verification. Pending route plans are
        reassessed.
      </p>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          if (
            await action(
              `/organisation-profiles/${org}/capabilities/${c.id}/declaration`,
              { kind: c.kind, scope },
              "PATCH",
            )
          )
            setOpen(false);
        }}
      >
        <SafetyScopeEditor
          kind={c.kind}
          scope={scope}
          onChange={setScope}
          showTechnical
        />
        <button>Save current declaration</button>
      </form>
    </details>
  );
}
