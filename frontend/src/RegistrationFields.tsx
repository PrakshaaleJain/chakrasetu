import { useResource } from "./api";
import { Field } from "./components";
import type { PBSDefinition, PBSLevel } from "./registrationTypes";
import { documentDescription } from "./registrationTypes";
export function PBSCards({
  value,
  onChange,
}: {
  value: PBSLevel | null;
  onChange: (v: PBSLevel) => void;
}) {
  const { data: policy, error } = useResource<{ levels: PBSDefinition[] }>(
    "/registration-policy",
    0,
    { levels: [] },
  );
  return (
    <section>
      <h3>Perceived Battery Safety (PBS)</h3>
      <p>
        Based on preliminary observations only. PBS does not certify safety and
        is separate from SoH, SoC and diagnostic findings. When uncertain,
        choose a higher-concern level.
      </p>
      {error && <p role="alert">{error}</p>}
      <div
        className="pbs-cards"
        role="group"
        aria-label="Perceived Battery Safety"
      >
        {policy.levels.map((l) => (
          <button
            type="button"
            key={l.level}
            aria-pressed={value === l.level}
            className={
              "pbs-card " + l.level + (value === l.level ? " chosen" : "")
            }
            onClick={() => onChange(l.level)}
          >
            <strong>
              {l.level} · {l.title}
            </strong>
            <span>{l.description}</span>
            <small>
              {value === l.level ? "✓ Selected" : "Select " + l.level}
            </small>
          </button>
        ))}
      </div>
    </section>
  );
}
export function DocumentsInput({
  files,
  onChange,
  error,
}: {
  files: File[];
  onChange: (f: File[]) => void;
  error?: string;
}) {
  return (
    <section>
      <Field label="Upload documents..." error={error}>
        <input
          type="file"
          multiple
          accept=".pdf,.docx,.xlsx,.jpg,.jpeg,.png,.txt"
          onChange={(e) => {
            onChange([...files, ...Array.from(e.target.files || [])]);
            e.target.value = "";
          }}
        />
      </Field>
      <p className="muted">{documentDescription}</p>
      <small>
        Up to four files · 10 MB per file · 25 MB total. No files required.
      </small>
      {files.map((f, i) => (
        <div className="evidence" key={f.name + ":" + i}>
          <span>
            {f.name} · {(f.size / 1024 / 1024).toFixed(2)} MB
          </span>
          <button
            type="button"
            onClick={() => onChange(files.filter((_, j) => i !== j))}
          >
            Remove {f.name}
          </button>
        </div>
      ))}
    </section>
  );
}
