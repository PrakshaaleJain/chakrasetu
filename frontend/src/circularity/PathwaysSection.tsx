import { Panel, Field, Badge, money, human } from "../components";
import type { useCircularity } from "./useCircularity";
export function PathwaysSection({
  ctx,
}: {
  ctx: ReturnType<typeof useCircularity>;
}) {
  const {
    actor,
    action,
    asset,
    evidence,
    decision,
    setDecision,
    pathway,
    setPathway,
    economics,
    setEconomics,
    pickAsset,
  } = ctx;
  return (
    <>
      <Panel title="Complete downstream pathway decision">
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            const values: Record<string, number | null | string> = {
              source: actor.synthetic ? "SYNTHETIC" : "OWNER_ESTIMATED",
              reference: evidence,
            };
            for (const key of [
              "terminal_revenue_paise",
              "acquisition_paise",
              "assessment_paise",
              "processing_paise",
              "transport_paise",
              "overhead_paise",
            ])
              values[key] = economics[key]
                ? Math.round(Number(economics[key]) * 100)
                : null;
            const r = await action(
              "/circularity/batteries/" + asset + "/pathways",
              { inputs: evidence ? { [pathway]: values } : {} },
            );
            if (r) setDecision(r);
          }}
        >
          {pickAsset}
          <Field label="Whole pathway for explicit economic inputs">
            <select
              value={pathway}
              onChange={(e) => setPathway(e.target.value)}
            >
              {["SECOND_LIFE", "RECOVER_MATERIALS", "DISMANTLE_PROCESS"].map(
                (x) => (
                  <option key={x} value={x}>
                    {human(x)}
                  </option>
                ),
              )}
            </select>
          </Field>
          <div className="form-grid">
            {[
              "terminal_revenue_paise",
              "acquisition_paise",
              "assessment_paise",
              "processing_paise",
              "transport_paise",
              "overhead_paise",
            ].map((key) => (
              <Field
                key={key}
                label={
                  human(key.replace("_paise", "")) + " · INR, whole pathway"
                }
              >
                <input
                  type="number"
                  min="0"
                  value={economics[key] || ""}
                  onChange={(e) =>
                    setEconomics({ ...economics, [key]: e.target.value })
                  }
                  placeholder="Unknown"
                />
              </Field>
            ))}
          </div>
          <p>
            Leaving any amount blank keeps the economic recommendation
            incomplete. Entering zero is an explicit assumption. Costs include
            acquisition and all downstream operations; no live market prices are
            inferred.
          </p>
          <button className="primary">
            Generate and persist explainable pathways
          </button>
        </form>
      </Panel>
      {decision && (
        <Panel title="Decision and competing routes">
          <p>{decision.recommendation_reason}</p>
          <small>
            Recorded {decision.generated_at} · {decision.decision_id}
          </small>
          {decision.candidates.map((c) => (
            <div key={c.id} className="candidate">
              <strong>
                {human(c.pathway)}{" "}
                {c.id === decision.recommended_id &&
                  "· recommended conditionally"}
              </strong>
              <Badge value={c.status} />
              <ol>
                {c.stages.map((s, i) => (
                  <li key={i}>
                    {human(s.operation)} · {s.name}
                  </li>
                ))}
              </ol>
              <p>
                Estimated net {money(c.economics.net_paise)} · estimated cost
                per battery {money(c.economics.cost_per_battery_paise)} ·{" "}
                {c.economics.source}
              </p>
              <p>
                {c.distance_km} km · Haversine × 1.3 proxy, no road distance or
                real ETA
              </p>
              {c.conditions.map((r, i) => (
                <p key={i}>
                  <strong>{human(r.code)}</strong> {r.message}
                </p>
              ))}
              {c.economics.missing.length > 0 && (
                <p>Missing economics: {c.economics.missing.join(", ")}</p>
              )}
              {c.warnings.map((w) => (
                <small key={w}>
                  {w}
                  <br />
                </small>
              ))}
            </div>
          ))}
          <details>
            <summary>All excluded stages and evidence used</summary>
            <pre>
              {JSON.stringify(
                {
                  rejected: decision.rejected,
                  evidence: decision.evidence_used,
                },
                null,
                2,
              )}
            </pre>
          </details>
        </Panel>
      )}
    </>
  );
}
