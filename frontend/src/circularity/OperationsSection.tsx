import { Panel, Field, Badge, human } from "../components";
import type { useCircularity } from "./useCircularity";
import { reviewBody } from "./domain";
export function OperationsSection({
  ctx,
}: {
  ctx: ReturnType<typeof useCircularity>;
}) {
  const {
    actor,
    action,
    asset,
    facility,
    operation,
    evidence,
    procedure,
    setProcedure,
    spec,
    limitations,
    setLimitations,
    itemIds,
    setItemIds,
    outputId,
    setOutputId,
    kind,
    setKind,
    category,
    setCategory,
    outputMass,
    setOutputMass,
    loss,
    setLoss,
    selectedJob,
    setSelectedJob,
    extraOutputs,
    setExtraOutputs,
    items,
    jobs,
    isReviewer,
    pickFacility,
    pickAsset,
    operationField,
    opOut,
  } = ctx;
  return (
    <>
      <Panel title="Link an existing physically held battery">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            action("/circularity/items/import-battery", {
              asset_id: asset,
              facility_id: facility,
              receipt_evidence: evidence,
            });
          }}
        >
          {pickAsset}
          {pickFacility}
          <button>Link battery identity to process trace</button>
        </form>
      </Panel>
      <Panel title="Create a transformation job">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            action("/circularity/jobs", {
              facility_id: facility,
              operation,
              item_ids: itemIds,
              procedure,
              evidence,
            });
          }}
        >
          {pickFacility}
          {operationField}
          <Field label="Procedure / processing contract reference">
            <input
              required
              value={procedure}
              onChange={(e) => setProcedure(e.target.value)}
            />
          </Field>
          <div className="checks">
            {items
              .filter(
                (i) =>
                  i.custodian_org_id === actor.organisation_id &&
                  ["AVAILABLE", "RETIRED"].includes(i.state),
              )
              .map((i) => (
                <label key={i.id}>
                  <input
                    type="checkbox"
                    checked={itemIds.includes(i.id)}
                    onChange={(e) =>
                      setItemIds(
                        e.target.checked
                          ? [...itemIds, i.id]
                          : itemIds.filter((x) => x !== i.id),
                      )
                    }
                  />
                  {i.identifier} · {i.mass_kg ?? "Unknown"} kg · {i.kind}
                </label>
              ))}
          </div>
          <p>
            Each input owner must separately approve the operation and output
            ownership terms. Multiple inputs and outputs retain explicit links.
          </p>
          <button disabled={!itemIds.length}>
            Create job and batch where applicable
          </button>
        </form>
      </Panel>
      {jobs.map((j) => (
        <Panel
          key={j.id}
          title={human(j.operation) + " · " + j.id}
          aside={<Badge value={j.state} />}
        >
          <p>
            {j.inputs
              .map(
                (x) =>
                  items.find((i) => i.id === x.item_id)?.identifier ||
                  x.item_id,
              )
              .join(" + ")}{" "}
            →{" "}
            {j.outputs
              .map(
                (x) =>
                  items.find((i) => i.id === x.item_id)?.identifier ||
                  x.item_id,
              )
              .join(" + ") || "Outputs not recorded"}
          </p>
          <p>{j.data.output_ownership_terms}</p>
          <div className="actions">
            {j.state === "DRAFT" && (
              <>
                <button
                  onClick={() =>
                    action(
                      "/circularity/jobs/" + j.id + "/authorize",
                      reviewBody(evidence),
                    )
                  }
                >
                  Input owner: approve operation and output title
                </button>
                <button
                  onClick={() => action("/circularity/jobs/" + j.id + "/start")}
                >
                  Operator: start with atomic allocation
                </button>
              </>
            )}
            {j.state === "RUNNING" && (
              <button
                onClick={() => {
                  setSelectedJob(j.id);
                  setExtraOutputs([]);
                }}
              >
                Record measured outputs
              </button>
            )}
            {isReviewer && j.state === "COMPLETED_REPORTED" && (
              <>
                <button
                  onClick={() =>
                    action(
                      "/circularity/jobs/" + j.id + "/review",
                      reviewBody(evidence),
                    )
                  }
                >
                  Review and accept reported processing
                </button>
                <button
                  onClick={() =>
                    action(
                      "/circularity/jobs/" + j.id + "/review",
                      reviewBody(evidence, false),
                    )
                  }
                >
                  Dispute reported outputs
                </button>
              </>
            )}
          </div>
        </Panel>
      ))}
      {selectedJob && (
        <Panel title="Measured outputs and documented mass balance">
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              const outs = outputId ? [...extraOutputs, opOut()] : extraOutputs;
              if (
                await action("/circularity/jobs/" + selectedJob + "/complete", {
                  outputs: outs,
                  process_evidence: evidence,
                  measured_loss_kg: Number(loss),
                  loss_evidence: limitations,
                })
              )
                setSelectedJob("");
            }}
          >
            <div className="form-grid">
              <Field label="Unique output identifier">
                <input
                  value={outputId}
                  onChange={(e) => setOutputId(e.target.value)}
                />
              </Field>
              <Field label="Output kind">
                <select value={kind} onChange={(e) => setKind(e.target.value)}>
                  <option value="MATERIAL">{human("MATERIAL")}</option>
                  <option value="PRODUCT">{human("PRODUCT")}</option>
                </select>
              </Field>
              <Field label="Measured output mass · kg">
                <input
                  type="number"
                  min="0.001"
                  step="any"
                  value={outputMass}
                  onChange={(e) => setOutputMass(e.target.value)}
                />
              </Field>
              <Field label="Material category or intended application">
                <input
                  required
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                />
              </Field>
            </div>
            <button
              type="button"
              disabled={!outputId || !outputMass || !spec || !evidence}
              onClick={() => {
                setExtraOutputs([...extraOutputs, opOut()]);
                setOutputId("");
                setOutputMass("");
              }}
            >
              Add another output to this report
            </button>
            {extraOutputs.map((o, i) => (
              <p key={i}>
                {o.identifier} · {o.mass_kg} kg · {o.kind}
              </p>
            ))}
            <Field label="Measured documented process loss · kg">
              <input
                type="number"
                required
                min="0"
                step="any"
                value={loss}
                onChange={(e) => setLoss(e.target.value)}
              />
            </Field>
            <Field label="Loss measurement / reconciliation evidence">
              <textarea
                required
                value={limitations}
                onChange={(e) => setLimitations(e.target.value)}
              />
            </Field>
            <p>
              Output mass plus documented loss must equal all recorded inputs.
              Completion is reported; outputs stay unavailable until review.
            </p>
            <button className="primary">Persist outputs and genealogy</button>
          </form>
        </Panel>
      )}
    </>
  );
}
