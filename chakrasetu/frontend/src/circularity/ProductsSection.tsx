import { displayJSON } from "../components";
import { api } from "../api";
import { Panel, Field, Badge, Empty, human } from "../components";
import type { useCircularity } from "./useCircularity";
export function ProductsSection({
  ctx,
}: {
  ctx: ReturnType<typeof useCircularity>;
}) {
  const {
    actor,
    action,
    network,
    evidence,
    spec,
    customer,
    setCustomer,
    trace,
    setTrace,
    event,
    setEvent,
    items,
    products,
    lots,
  } = ctx;
  return (
    <>
      <Panel title="Trace every input and output">
        {items.map((i) => (
          <div className="record-row" key={i.id}>
            <span>
              <strong>{i.identifier}</strong>
              <small>
                {i.kind} · {i.mass_kg ?? "Unknown"} kg · Operator record ·
                Custodian {i.custodian_org_id}
              </small>
            </span>
            <Badge value={i.state} />
            <button
              onClick={async () => {
                try {
                  setTrace(
                    await api(
                      "/circularity/items/" + i.id + "/trace?direction=BOTH",
                    ),
                  );
                } catch (e) {
                  setTrace({ error: (e as Error).message });
                }
              }}
            >
              View provenance trace
            </button>
          </div>
        ))}
        {trace !== null && (
          <details open>
            <summary>
              Documentary genealogy and custody · blended inputs are labelled
            </summary>
            <pre>{displayJSON(trace, null, 2)}</pre>
          </details>
        )}
      </Panel>
      <Panel title="Second-life products, acceptance and deployment">
        <Field label="Product event">
          <select value={event} onChange={(e) => setEvent(e.target.value)}>
            {[
              "ACCEPT",
              "DEPLOY",
              "SERVICE",
              "RETIRE",
              "TAKE_BACK_CONTRACT",
              "INCIDENT_REPORTED",
            ].map((x) => (
              <option key={x} value={x}>
                {human(x)}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Deployment / contracted take-back customer">
          <select
            value={customer}
            onChange={(e) => setCustomer(e.target.value)}
          >
            <option value="">Not applicable / unknown</option>
            {network.organisations.map((o) => (
              <option key={o.id} value={o.id}>
                {o.name}
              </option>
            ))}
          </select>
        </Field>
        {products.map((p) => (
          <div className="evidence" key={p.id}>
            <strong>
              {p.item.identifier} · {p.intended_application}
            </strong>
            <Badge value={p.state} />
            <p>{p.item.data.specification}</p>
            {p.item.custodian_org_id === actor.organisation_id && (
              <button
                onClick={() =>
                  action("/circularity/products/" + p.id + "/events", {
                    event,
                    evidence,
                    notes: spec,
                    customer_org_id: customer || null,
                  })
                }
              >
                Append documented {human(event)} event
              </button>
            )}
            <details>
              <summary>Installation, service and recovery history</summary>
              <pre>{displayJSON(p.events, null, 2)}</pre>
            </details>
          </div>
        ))}
      </Panel>
      <Panel title="Recovered material lots">
        {lots.length === 0 ? (
          <Empty>No measured material lots have been reported.</Empty>
        ) : (
          lots.map((l) => (
            <div className="evidence" key={l.id}>
              <strong>
                {l.item.identifier} · {l.category}
              </strong>
              <p>
                {l.quantity} {l.unit} · source job {l.source_job_id}
              </p>
              <p>{l.item.data.specification}</p>
              <Badge value={l.item.state} />
            </div>
          ))
        )}
      </Panel>
    </>
  );
}
