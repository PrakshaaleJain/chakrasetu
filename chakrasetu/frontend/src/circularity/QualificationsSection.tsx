import { Panel, Field, Badge, human } from "../components";
import type { useCircularity } from "./useCircularity";
import { reviewBody } from "./domain";
export function QualificationsSection({
  ctx,
}: {
  ctx: ReturnType<typeof useCircularity>;
}) {
  const {
    action,
    facility,
    operation,
    evidence,
    capacity,
    setCapacity,
    chemistries,
    setChemistries,
    formats,
    setFormats,
    categories,
    setCategories,
    capabilities,
    isReviewer,
    pickFacility,
    operationField,
  } = ctx;
  return (
    <>
      <Panel title="Declare an operation capability">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            action("/circularity/capabilities", {
              facility_id: facility,
              operation,
              capacity_kg: capacity === "" ? null : Number(capacity),
              chemistries: chemistries.split(",").map((x) => x.trim()),
              formats: formats.split(",").map((x) => x.trim()),
              material_categories: categories.split(",").map((x) => x.trim()),
              evidence,
            });
          }}
        >
          {pickFacility}
          {operationField}
          <Field label="Available operation capacity · kg (unknown allowed)">
            <input
              type="number"
              min="0.001"
              step="any"
              value={capacity}
              onChange={(e) => setCapacity(e.target.value)}
            />
          </Field>
          <Field label="Declared chemistries · comma separated">
            <input
              value={chemistries}
              onChange={(e) => setChemistries(e.target.value)}
            />
          </Field>
          <Field label="Declared battery formats">
            <input
              value={formats}
              onChange={(e) => setFormats(e.target.value)}
            />
          </Field>
          <Field label="Declared product/material categories">
            <input
              value={categories}
              onChange={(e) => setCategories(e.target.value)}
            />
          </Field>
          <button>Save declaration; verification remains pending</button>
        </form>
      </Panel>
      <Panel title="Scoped operation qualifications">
        {capabilities.map((c) => (
          <div className="evidence" key={c.id}>
            <strong>
              {c.facility_id} · {human(c.operation)}
            </strong>
            <Badge value={c.verified ? "VERIFIED" : "UNVERIFIED"} />
            <p>
              Capacity {c.capacity_kg ?? "Unknown"} kg · scope{" "}
              {c.chemistries.join(", ")} · {c.material_categories.join(", ")}
            </p>
            {isReviewer && (
              <div className="actions">
                <button
                  onClick={() =>
                    action(
                      "/circularity/capabilities/" + c.id + "/review",
                      reviewBody(evidence),
                    )
                  }
                >
                  Record qualification review
                </button>
                <button
                  onClick={() =>
                    action(
                      "/circularity/capabilities/" + c.id + "/review",
                      reviewBody(evidence, false),
                    )
                  }
                >
                  Suspend operation scope
                </button>
              </div>
            )}
          </div>
        ))}
      </Panel>
    </>
  );
}
