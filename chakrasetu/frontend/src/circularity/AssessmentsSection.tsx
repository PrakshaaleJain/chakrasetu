import { displayJSON } from "../components";
import { Panel, Field, Badge, human } from "../components";
import type { useCircularity } from "./useCircularity";
import { reviewBody } from "./domain";
import { useState } from "react";
export function AssessmentsSection({
  ctx,
}: {
  ctx: ReturnType<typeof useCircularity>;
}) {
  const [technical, setTechnical] = useState<Record<string, boolean | null>>(
    {},
  );
  const {
    action,
    network,
    asset,
    facility,
    setFacility,
    operation,
    evidence,
    procedure,
    setProcedure,
    observations,
    setObservations,
    measurement,
    setMeasurement,
    spec,
    outcome,
    setOutcome,
    limitations,
    setLimitations,
    measurementUnit,
    setMeasurementUnit,
    measurementName,
    setMeasurementName,
    assessments,
    capabilities,
    ownFacilities,
    isReviewer,
    pickAsset,
    operationField,
  } = ctx;
  return (
    <>
      <Panel title="Assign a qualified assessment">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            action("/circularity/assessments", {
              asset_id: asset,
              facility_id: facility,
              intended_operation: operation,
              procedure,
            });
          }}
        >
          {pickAsset}
          <Field label="Assigned diagnostic facility">
            <select
              required
              value={facility}
              onChange={(e) => setFacility(e.target.value)}
            >
              <option value="">Choose qualified facility</option>
              {network.facilities
                .filter((f) =>
                  capabilities.some(
                    (c) =>
                      c.facility_id === f.id &&
                      c.operation === "ASSESSMENT" &&
                      c.verified,
                  ),
                )
                .map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.name}
                  </option>
                ))}
            </select>
          </Field>
          {operationField}
          <Field label="Required test / procedure reference">
            <input
              required
              value={procedure}
              onChange={(e) => setProcedure(e.target.value)}
            />
          </Field>
          <button>Assign assessment</button>
        </form>
      </Panel>
      {assessments.map((a) => (
        <Panel
          title={a.asset_id + " · " + human(a.intended_operation)}
          key={a.id}
          aside={<Badge value={a.state} />}
        >
          <p>
            Facility {a.facility_id} · procedure {a.data.procedure}
          </p>
          {a.state === "ASSIGNED" &&
            ownFacilities.some((f) => f.id === a.facility_id) && (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  action("/circularity/assessments/" + a.id + "/submit", {
                    observations,
                    measurements: [
                      {
                        name: measurementName,
                        value: measurement === "" ? null : Number(measurement),
                        unit: measurementUnit,
                        method: procedure,
                      },
                    ],
                    evidence,
                    equipment_reference: procedure,
                    outcome,
                    limitations,
                    acceptance_specification: spec,
                    technical_findings: Object.values(technical).some(
                      (v) => v !== null,
                    )
                      ? { ...technical, application_reference: spec }
                      : null,
                  });
                }}
              >
                <Field label="Recorded observations">
                  <textarea
                    required
                    value={observations}
                    onChange={(e) => setObservations(e.target.value)}
                  />
                </Field>
                <div className="form-grid">
                  <Field label="Measurement name">
                    <input
                      required
                      value={measurementName}
                      onChange={(e) => setMeasurementName(e.target.value)}
                    />
                  </Field>
                  <Field label="Measurement value · blank means unknown">
                    <input
                      type="number"
                      step="any"
                      value={measurement}
                      onChange={(e) => setMeasurement(e.target.value)}
                    />
                  </Field>
                  <Field label="Unit">
                    <input
                      required
                      value={measurementUnit}
                      onChange={(e) => setMeasurementUnit(e.target.value)}
                    />
                  </Field>
                </div>
                <Field label="Equipment and method reference">
                  <input
                    required
                    value={procedure}
                    onChange={(e) => setProcedure(e.target.value)}
                  />
                </Field>
                <Field label="Defined outcome">
                  <select
                    value={outcome}
                    onChange={(e) => setOutcome(e.target.value)}
                  >
                    {[
                      "INFORMATION_INSUFFICIENT",
                      "UNSUITABLE",
                      "SUITABLE_FOR_DEFINED_OPERATION",
                    ].map((x) => (
                      <option key={x} value={x}>
                        {human(x)}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="Limitations and missing information">
                  <textarea
                    required
                    value={limitations}
                    onChange={(e) => setLimitations(e.target.value)}
                  />
                </Field>
                <fieldset>
                  <legend>Application-specific technical findings</legend>
                  <p>
                    Record supported findings only. Unknown is distinct from a
                    failed test. These findings become authoritative only after
                    independent assessment acceptance.
                  </p>
                  <div className="form-grid">
                    {[
                      ["fault_identified", "Fault or deficiency identified"],
                      ["repairable", "Technically repairable"],
                      [
                        "parts_available",
                        "Compatible parts/expertise available",
                      ],
                      [
                        "requalification_possible",
                        "Post-repair requalification feasible",
                      ],
                      [
                        "automotive_application_passed",
                        "Defined vehicle requirements passed",
                      ],
                      [
                        "second_life_application_passed",
                        "Defined second-life requirements passed",
                      ],
                      [
                        "remaining_life_adequate",
                        "Remaining life adequate for the application",
                      ],
                    ].map(([key, label]) => (
                      <Field label={label} key={key}>
                        <select
                          value={
                            technical[key] == null
                              ? "UNKNOWN"
                              : technical[key]
                                ? "YES"
                                : "NO"
                          }
                          onChange={(e) =>
                            setTechnical((v) => ({
                              ...v,
                              [key]:
                                e.target.value === "UNKNOWN"
                                  ? null
                                  : e.target.value === "YES",
                            }))
                          }
                        >
                          <option value="UNKNOWN">
                            Unknown / not established
                          </option>
                          <option value="YES">Yes, with evidence</option>
                          <option value="NO">No, with evidence</option>
                        </select>
                      </Field>
                    ))}
                  </div>
                </fieldset>
                <button>Submit immutable technician report</button>
              </form>
            )}
          {isReviewer && a.state === "SUBMITTED" && (
            <div className="actions">
              <button
                onClick={() =>
                  action(
                    "/circularity/assessments/" + a.id + "/review",
                    reviewBody(evidence),
                  )
                }
              >
                Accept defined assessment with evidence
              </button>
              <button
                onClick={() =>
                  action(
                    "/circularity/assessments/" + a.id + "/review",
                    reviewBody(evidence, false),
                  )
                }
              >
                Reject report
              </button>
            </div>
          )}
          {a.state !== "ASSIGNED" && (
            <button
              onClick={() =>
                action("/circularity/assessments", {
                  asset_id: a.asset_id,
                  facility_id: a.facility_id,
                  intended_operation: a.intended_operation,
                  procedure: procedure || a.data.procedure,
                  revision_of: a.id,
                })
              }
            >
              Create linked revision
            </button>
          )}
          <details>
            <summary>Provenance, measurements, limitations and review</summary>
            <pre>{displayJSON(a.data, null, 2)}</pre>
          </details>
        </Panel>
      ))}
    </>
  );
}
