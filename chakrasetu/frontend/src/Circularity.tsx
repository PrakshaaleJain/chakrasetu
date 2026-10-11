import type { Actor, Action, Battery, Network } from "./types";
import { circularTabs } from "./navigation";
import { useEffect } from "react";
import { Panel, Field } from "./components";
import { useCircularity } from "./circularity/useCircularity";
import { PathwaysSection } from "./circularity/PathwaysSection";
import { AssessmentsSection } from "./circularity/AssessmentsSection";
import { OperationsSection } from "./circularity/OperationsSection";
import { ProductsSection } from "./circularity/ProductsSection";
import { HandoffsSection } from "./circularity/HandoffsSection";

export function Circularity({
  actor,
  action,
  version,
  batteries,
  network,
}: {
  actor: Actor;
  action: Action;
  version: number;
  batteries: Battery[];
  network: Network;
}) {
  const ctx = useCircularity({ actor, action, version, batteries, network });
  const {
    tab,
    setTab,
    evidence,
    setEvidence,
    spec,
    setSpec,
    aError,
    iError,
    jError,
  } = ctx;
  const tabs = circularTabs(actor);
  useEffect(() => {
    if (!tabs.includes(tab)) setTab(tabs[0] || "Pathways");
  }, [actor, tab]);
  return (
    <>
      <div className="actions">
        {tabs.map((x) => (
          <button
            className={tab === x ? "primary" : ""}
            key={x}
            onClick={() => setTab(x)}
          >
            {x}
          </button>
        ))}
      </div>
      <p className="notice">
        Plan a pathway, record processing and track downstream handovers.
        Completion requires the relevant evidence and acceptance.
      </p>
      {(aError || iError || jError) && (
        <p role="alert">{aError || iError || jError}</p>
      )}
      <Panel title="Evidence for the next action">
        <Field label="Evidence / report reference">
          <textarea
            required
            value={evidence}
            onChange={(e) => setEvidence(e.target.value)}
            placeholder="Enter a report or supporting record reference"
          />
        </Field>
        <Field label="Defined technical / receiving specification">
          <textarea
            value={spec}
            onChange={(e) => setSpec(e.target.value)}
            placeholder="Application-specific criteria; a generic SOH threshold is insufficient"
          />
        </Field>
      </Panel>
      {tab === "Pathways" && <PathwaysSection ctx={ctx} />}
      {tab === "Assessments" && <AssessmentsSection ctx={ctx} />}
      {tab === "Operations" && <OperationsSection ctx={ctx} />}
      {tab === "Products & materials" && <ProductsSection ctx={ctx} />}
      {tab === "Downstream handoffs" && <HandoffsSection ctx={ctx} />}
    </>
  );
}
