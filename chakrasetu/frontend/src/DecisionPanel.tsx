import { useState } from "react";
import { api, useResource } from "./api";
import { Badge, Panel, Field, human, money, date } from "./components";
import { hasRole } from "./navigation";
import type { Actor } from "./types";
import type {
  DecisionPath,
  DecisionPolicy,
  FinanceInput,
  FinanceValue,
  PathwayDecision,
} from "./decisionTypes";

export function DecisionResults({
  result,
  compact = false,
}: {
  result: PathwayDecision;
  compact?: boolean;
}) {
  return (
    <div className={"decision-results " + (compact ? "compact" : "")}>
      <div className="decision-summary">
        <span className="eyebrow">RULES FIRST. ECONOMICS SECOND.</span>
        <h3>
          {result.recommended_pathway
            ? result.pathways.find(
                (p) => p.pathway === result.recommended_pathway,
              )?.label
            : result.similar_pathways.length
              ? "Several routes. No false precision."
              : result.safety_state.includes("HOLD") ||
                  result.safety_state === "SPECIALIST_REVIEW"
                ? "Review before routing."
                : "Keep the missing evidence visible."}
        </h3>
        <Badge value={result.evaluation_state} />
        <p aria-live="polite">{result.recommendation_reason}</p>
        <small>
          SoH{" "}
          {result.soh.value == null ? "unavailable" : result.soh.value + "%"} ·{" "}
          {human(result.soh.source)} · {human(result.soh.screening_band)}{" "}
          screening band
        </small>
        {result.restrictions.map((r) => (
          <p key={r.code} className="field-error">
            {r.message}
          </p>
        ))}
        {result.stale && (
          <p role="status" className="warning-banner">
            Important inputs changed. The current calculation below is
            refreshed; record a new decision to preserve it.
          </p>
        )}
        {result.recalculation_warning && (
          <p role="status">{result.recalculation_warning}</p>
        )}
      </div>
      <div className="decision-options">
        {result.pathways.map((p) => (
          <details
            key={p.pathway}
            className={
              "decision-option " +
              (p.pathway === result.recommended_pathway ? "preferred" : "")
            }
            open={
              compact ? undefined : p.pathway === result.recommended_pathway
            }
          >
            <summary>
              <span>{p.label}</span>
              <Badge value={p.status} />
              <strong>
                {p.economics.ranking_eligible
                  ? money(p.economics.net_paise)
                  : p.economics.complete
                    ? "Not ranked"
                    : "Quotes needed"}
              </strong>
            </summary>
            <p>{p.next_action}</p>
            <ul className="rule-list">
              {p.rules.map((r) => (
                <li key={r.code}>
                  <span
                    aria-label={
                      r.passed === null
                        ? "Evidence needed"
                        : r.passed
                          ? "Passed"
                          : "Failed"
                    }
                  >
                    {r.passed === null ? "?" : r.passed ? "✓" : "×"}
                  </span>
                  <div>
                    <strong>{human(r.code)}</strong>
                    <p>{r.message}</p>
                  </div>
                </li>
              ))}
            </ul>
            {p.economics.complete && (
              <p>
                Calculated net {money(p.economics.net_paise)}; range{" "}
                {money(p.economics.range_paise?.[0])}–
                {money(p.economics.range_paise?.[1])}.{" "}
                {human(p.economics.basis || "")} ·{" "}
                {human(p.economics.perspective || "")} · horizon{" "}
                {p.economics.horizon_years || 0} years.{" "}
                {p.economics.provisional
                  ? "Includes estimates."
                  : "Recorded quotations."}{" "}
                {p.status !== "FEASIBLE" &&
                  "This route failed a gate and is excluded from economic ranking."}
              </p>
            )}
            {!!p.economics.missing.length && (
              <p>
                Missing economics: {p.economics.missing.map(human).join(", ")}.
                No missing cost is treated as zero.
              </p>
            )}
            {!compact && (
              <>
                <div className="finance-provenance">
                  {p.economics.inputs.benefits?.map((v, i) => (
                    <p key={"b" + i}>
                      Benefit: {money(v.amount_paise)} · {human(v.source)} ·{" "}
                      {v.reference} · valid until {date(v.valid_until)} · year{" "}
                      {v.year}
                    </p>
                  ))}
                  {Object.entries(p.economics.inputs.costs || {}).map(
                    ([key, v]) => (
                      <p key={key}>
                        {human(key)}: {money(v.amount_paise)} ·{" "}
                        {human(v.source)} · {v.reference} · valid until{" "}
                        {date(v.valid_until)} · year {v.year}
                      </p>
                    ),
                  )}
                </div>
                {p.network.stages.map((s, i) => (
                  <div className="route-stage" key={s.operation + i}>
                    <strong>
                      {i + 1}. {human(s.operation)}
                    </strong>
                    {s.receivers.length ? (
                      s.receivers.map((r) => (
                        <p key={r.facility_id}>
                          {r.name} · eligible transport:{" "}
                          {r.transporters.map((t) => t.name).join(", ")}
                        </p>
                      ))
                    ) : (
                      <p>
                        No qualified, reachable facility is currently available.
                      </p>
                    )}
                  </div>
                ))}
                <details>
                  <summary>Participant exclusions</summary>
                  {p.network.rejected.map((r, i) => (
                    <div key={i}>
                      <strong>
                        {r.name} · {human(r.operation || "")}
                      </strong>
                      <ul>
                        {r.reasons.map((x, j) => (
                          <li key={j}>
                            {x.message} <small>({x.code})</small>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </details>
              </>
            )}
            {[
              ...p.qualification_conditions,
              ...(p.network.conditions || []),
            ].map((c) => (
              <p key={c} className="muted">
                {c}
              </p>
            ))}
          </details>
        ))}
      </div>
      {!compact && (
        <>
          <p className="muted">
            Calculated {date(result.generated_at)} · rules {result.rule_version}
            . This recommendation does not book transport, transfer custody or
            establish a completed outcome.
          </p>
          <details>
            <summary>Evidence sources and limitations</summary>
            {result.evidence_used.map((e, i) => (
              <p key={i}>
                {human(e.type)} · {human(e.source)} · {e.id || "Reported input"}{" "}
                · {e.application_reference} · {e.limitations}
              </p>
            ))}
          </details>
        </>
      )}
    </div>
  );
}

export function DecisionPanel({
  assetId,
  actor,
  version,
}: {
  assetId: string;
  actor: Actor;
  version: number;
}) {
  const [revision, setRevision] = useState(0),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [path, setPath] = useState<DecisionPath>("REFURBISHMENT"),
    [values, setValues] = useState<Record<string, string>>({}),
    [reference, setReference] = useState(""),
    [source, setSource] = useState("OWNER_ESTIMATE"),
    [basis, setBasis] = useState<"NET_TRANSACTION" | "NPV">("NET_TRANSACTION"),
    [horizon, setHorizon] = useState("5"),
    [rate, setRate] = useState("0.1"),
    [perspective, setPerspective] = useState<
      "WHOLE_PATHWAY" | "ORIGINATOR_TRANSACTION"
    >("WHOLE_PATHWAY"),
    [offer, setOffer] = useState(""),
    [quote, setQuote] = useState(""),
    [reason, setReason] = useState(""),
    [overridePath, setOverridePath] = useState<DecisionPath>("RECYCLING");
  const {
    data: result,
    loading,
    error: loadError,
  } = useResource<PathwayDecision | null>(
    "/circularity/batteries/" + assetId + "/recommendation",
    version + revision,
    null,
  );
  const { data: policy } = useResource<DecisionPolicy | null>(
    "/public/pathway-policy",
    0,
    null,
  );
  const { data: history } = useResource<
    { id: string; created_at: string; result: PathwayDecision }[]
  >(
    "/circularity/batteries/" + assetId + "/recommendation-history",
    version + revision,
    [],
  );
  const [recorded, setRecorded] = useState<PathwayDecision | null>(null);
  const current = recorded && revision === 0 ? recorded : result;
  async function save(economics: Record<string, FinanceInput>) {
    setBusy(true);
    setError("");
    try {
      const r = await api<PathwayDecision>(
        "/circularity/batteries/" + assetId + "/recommendation",
        { economics },
        "POST",
      );
      setRecorded(r);
      setRevision((v) => v + 1);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Panel title="Pathway decision">
      <p>
        Safety → technical evidence → qualified chain → comparable economics.
      </p>
      {loading && (
        <p role="status">Evaluating current evidence and capabilities…</p>
      )}
      {(error || loadError) && (
        <p role="alert" className="field-error">
          {error || loadError}
          <button onClick={() => setRevision((v) => v + 1)}>Retry</button>
        </p>
      )}
      {current && <DecisionResults result={current} />}
      <div className="actions">
        <button
          disabled={busy}
          onClick={() => save(current?.request_inputs || {})}
        >
          Record current evaluation
        </button>
        <button disabled={busy} onClick={() => setRevision((v) => v + 1)}>
          Recalculate
        </button>
      </div>
      <details>
        <summary>Add economic inputs or compare another pathway</summary>
        <p>
          All figures cover the entire registered quantity. Zero means an
          explicit documented assumption. Required costs left blank remain
          unknown. Different perspectives or horizons are not ranked together.
        </p>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const now = new Date().toISOString(),
              until = new Date(Date.now() + 7 * 86400000).toISOString();
            const value = (amount: string, year = 0): FinanceValue => ({
              amount_paise: Math.round(Number(amount) * 100),
              source,
              reference,
              recorded_at: now,
              valid_until: until,
              year,
              uncertainty_paise: 0,
            });
            const costs: Record<string, FinanceValue> = {};
            for (const key of policy?.cost_components[path] || [])
              if (values[key] !== "" && values[key] !== undefined)
                costs[key] = value(values[key]);
            const input: FinanceInput = {
              currency: "INR",
              perspective,
              basis,
              horizon_years: basis === "NPV" ? Number(horizon) : 0,
              discount_rate: basis === "NPV" ? Number(rate) : null,
              benefits: offer
                ? []
                : values.benefit
                  ? [
                      value(
                        values.benefit,
                        basis === "NPV" ? Number(horizon) : 0,
                      ),
                    ]
                  : [],
              costs,
              ...(offer ? { offer_id: offer } : {}),
              ...(quote ? { transport_quote_id: quote } : {}),
            };
            save({ ...current?.request_inputs, [path]: input });
          }}
        >
          <div className="form-grid">
            <Field label="Pathway">
              <select
                value={path}
                onChange={(e) => {
                  setPath(e.target.value as DecisionPath);
                  setValues({});
                  setOffer("");
                  setQuote("");
                }}
              >
                {Object.entries(policy?.pathways || {}).map(([k, l]) => (
                  <option key={k} value={k}>
                    {l}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Comparison perspective">
              <select
                value={perspective}
                onChange={(e) => {
                  setPerspective(e.target.value as typeof perspective);
                  setOffer("");
                }}
              >
                <option value="WHOLE_PATHWAY">Whole pathway</option>
                <option value="ORIGINATOR_TRANSACTION">
                  Originator transaction
                </option>
              </select>
            </Field>
            <Field label="Accounting basis">
              <select
                value={basis}
                onChange={(e) => setBasis(e.target.value as typeof basis)}
              >
                <option value="NET_TRANSACTION">Net transaction</option>
                <option value="NPV">Net present value</option>
              </select>
            </Field>
            <Field label="Source of estimated inputs">
              <select
                value={source}
                onChange={(e) => setSource(e.target.value)}
              >
                <option value="OWNER_ESTIMATE">Owner estimate</option>
                <option value="ORGANISATION_ESTIMATE">
                  Organization-provided estimate
                </option>
              </select>
            </Field>
          </div>
          <Field label="Evidence / quote / assumption reference">
            <input
              required
              minLength={3}
              value={reference}
              onChange={(e) => setReference(e.target.value)}
            />
          </Field>
          <p>
            Inputs recorded now and valid for seven days. Refresh them when
            prices change.
          </p>
          {basis === "NPV" && (
            <div className="form-grid">
              <Field label="Common horizon (years)">
                <input
                  required
                  type="number"
                  min={1}
                  max={30}
                  value={horizon}
                  onChange={(e) => setHorizon(e.target.value)}
                />
              </Field>
              <Field label="Annual discount rate (decimal)">
                <input
                  required
                  type="number"
                  min={0}
                  max={1}
                  step="0.01"
                  value={rate}
                  onChange={(e) => setRate(e.target.value)}
                />
              </Field>
              <p>
                This form places costs at year 0 and terminal benefit at the
                selected horizon. The API supports dated intermediate annual
                cash flows.
              </p>
            </div>
          )}
          {perspective === "ORIGINATOR_TRANSACTION" &&
            basis === "NET_TRANSACTION" && (
              <Field label="Existing purchase offer ID (optional)">
                <input
                  value={offer}
                  onChange={(e) => {
                    setOffer(e.target.value);
                    setValues({ ...values, benefit: "" });
                  }}
                  placeholder="Use a current offer from Listings & offers"
                />
              </Field>
            )}
          {!offer && (
            <Field label="Terminal benefit / sale value · INR">
              <input
                type="number"
                min={0}
                step="0.01"
                value={values.benefit || ""}
                onChange={(e) =>
                  setValues({ ...values, benefit: e.target.value })
                }
                placeholder="Unknown"
              />
            </Field>
          )}
          <Field label="Existing transport quote ID (optional)">
            <input
              value={quote}
              onChange={(e) => {
                setQuote(e.target.value);
                setValues({ ...values, transport: "" });
              }}
              placeholder="Current scoped quote; covers the quoted leg only"
            />
          </Field>
          <div className="form-grid">
            {(policy?.cost_components[path] || [])
              .filter((k) => k !== "transport" || !quote)
              .map((k) => (
                <Field key={k} label={human(k) + " · INR"}>
                  <input
                    type="number"
                    min={0}
                    step="0.01"
                    value={values[k] || ""}
                    onChange={(e) =>
                      setValues({ ...values, [k]: e.target.value })
                    }
                    placeholder="Unknown"
                  />
                </Field>
              ))}
          </div>
          <button disabled={busy} className="primary">
            Save inputs and evaluate
          </button>
        </form>
      </details>
      {hasRole(actor, "REVIEWER") && current?.decision_id && (
        <details>
          <summary>Record a reasoned reviewer override</summary>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              setBusy(true);
              setError("");
              try {
                await api(
                  "/circularity/decisions/" + current.decision_id + "/override",
                  { pathway: overridePath, reason },
                  "POST",
                );
                setRevision((v) => v + 1);
              } catch (e) {
                setError((e as Error).message);
              } finally {
                setBusy(false);
              }
            }}
          >
            <Field label="Qualified feasible alternative">
              <select
                value={overridePath}
                onChange={(e) =>
                  setOverridePath(e.target.value as DecisionPath)
                }
              >
                {current.pathways
                  .filter((p) => p.status === "FEASIBLE")
                  .map((p) => (
                    <option key={p.pathway} value={p.pathway}>
                      {p.label}
                    </option>
                  ))}
              </select>
            </Field>
            <Field label="Reason (required)">
              <textarea
                required
                minLength={10}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
            </Field>
            <button disabled={busy}>
              Record override without changing the engine result
            </button>
          </form>
        </details>
      )}
      {(current?.overrides || current?.override) && (
        <p>
          Reviewer selection{" "}
          {(current.overrides || current.override)!.active === false
            ? "(historical; inputs changed) "
            : ""}
          {human((current.overrides || current.override)!.selected_pathway)}:{" "}
          {(current.overrides || current.override)!.reason}. The original engine
          result is retained.
        </p>
      )}
      <details>
        <summary>Decision history ({history.length})</summary>
        {history.map((h) => (
          <details key={h.id}>
            <summary>
              {date(h.created_at)} · {h.result.evaluation_state} · {h.id}
            </summary>
            <DecisionResults result={h.result} />
          </details>
        ))}
      </details>
    </Panel>
  );
}
