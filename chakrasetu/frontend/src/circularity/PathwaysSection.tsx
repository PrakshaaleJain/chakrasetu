import { Panel } from "../components";
import { DecisionPanel } from "../DecisionPanel";
import type { useCircularity } from "./useCircularity";
export function PathwaysSection({
  ctx,
}: {
  ctx: ReturnType<typeof useCircularity>;
}) {
  return (
    <>
      <Panel title="Choose a battery to evaluate">
        {ctx.pickAsset}
        <p>
          Application-specific evidence, activity qualifications and current
          prices determine the pathway. The same engine powers the public
          explorer and the battery record.
        </p>
      </Panel>
      {ctx.asset && (
        <DecisionPanel
          key={ctx.asset}
          assetId={ctx.asset}
          actor={ctx.actor}
          version={ctx.version}
        />
      )}
    </>
  );
}
