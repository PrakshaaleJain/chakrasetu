import { human } from "../components";
import { hasRole } from "../navigation";
import { useState } from "react";
import { useResource } from "../api";
import type { Actor, Action, Battery, Network } from "../types";
import { Field } from "../components";
import { OPERATIONS } from "./domain";
import type {
  Assessment,
  Item,
  Job,
  Product,
  Lot,
  Handoff,
  Capability,
} from "./domain";
export function useCircularity({
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
  const [tab, setTab] = useState("Pathways"),
    [asset, setAsset] = useState(""),
    [facility, setFacility] = useState(""),
    [operation, setOperation] = useState("REFURBISHMENT"),
    [evidence, setEvidence] = useState(""),
    [procedure, setProcedure] = useState(""),
    [observations, setObservations] = useState(""),
    [measurement, setMeasurement] = useState(""),
    [spec, setSpec] = useState(""),
    [outcome, setOutcome] = useState("INFORMATION_INSUFFICIENT"),
    [limitations, setLimitations] = useState(""),
    [itemIds, setItemIds] = useState<string[]>([]),
    [outputId, setOutputId] = useState(""),
    [kind, setKind] = useState("MATERIAL"),
    [category, setCategory] = useState("BLACK_MASS"),
    [outputMass, setOutputMass] = useState(""),
    [loss, setLoss] = useState(""),
    [selectedJob, setSelectedJob] = useState(""),
    [customer, setCustomer] = useState(""),
    [receiver, setReceiver] = useState(""),
    [price, setPrice] = useState(""),
    [cap, setCap] = useState(""),
    [quote, setQuote] = useState(""),
    [carrier, setCarrier] = useState(""),
    [item, setItem] = useState(""),
    [payer, setPayer] = useState(""),
    [trace, setTrace] = useState<unknown | null>(null),
    [event, setEvent] = useState("ACCEPT"),
    [condition, setCondition] = useState(true),
    [physical, setPhysical] = useState(false),
    [capacity, setCapacity] = useState(""),
    [chemistries, setChemistries] = useState("LFP,NMC"),
    [formats, setFormats] = useState("PACK,MODULE"),
    [categories, setCategories] = useState(
      "BLACK_MASS,COPPER,ALUMINIUM,REFINED_LITHIUM,SECOND_LIFE_SYSTEM",
    ),
    [measurementUnit, setMeasurementUnit] = useState("Ah"),
    [measurementName, setMeasurementName] = useState("capacity"),
    [extraOutputs, setExtraOutputs] = useState<
      {
        identifier: string;
        kind: string;
        mass_kg: number;
        category: string;
        specification: string;
        evidence: string;
        chemistry: string;
      }[]
    >([]);
  const { data: assessments, error: aError } = useResource<Assessment[]>(
    "/circularity/assessments",
    version,
    [],
  );
  const { data: items, error: iError } = useResource<Item[]>(
    "/circularity/items",
    version,
    [],
  );
  const { data: jobs, error: jError } = useResource<Job[]>(
    "/circularity/jobs",
    version,
    [],
  );
  const { data: products } = useResource<Product[]>(
    "/circularity/products",
    version,
    [],
  );
  const { data: lots } = useResource<Lot[]>(
    "/circularity/material-lots",
    version,
    [],
  );
  const { data: handoffs } = useResource<Handoff[]>(
    "/circularity/handoffs",
    version,
    [],
  );
  const { data: requests } = useResource<
    {
      handoff_id: string;
      transporter_id: string;
      kind: string;
      category: string;
      mass_kg: number;
      source_facility_id: string;
      receiver_facility_id: string;
      required_handling_specification: string;
    }[]
  >(
    hasRole(actor, "TRANSPORTER") ? "/circularity/quote-requests" : null,
    version,
    [],
  );
  const { data: capabilities } = useResource<Capability[]>(
    "/circularity/capabilities",
    version,
    [],
  );
  const ownFacilities = network.facilities.filter(
    (f) => f.organisation_id === actor.organisation_id,
  );
  const isReviewer = hasRole(actor, "REVIEWER");
  const pickFacility = (
    <Field label="Your physical operating facility">
      <select
        required
        value={facility}
        onChange={(e) => setFacility(e.target.value)}
      >
        <option value="">Choose facility</option>
        {ownFacilities.map((f) => (
          <option key={f.id} value={f.id}>
            {f.name}
          </option>
        ))}
      </select>
    </Field>
  );
  const pickAsset = (
    <Field label="Battery asset">
      <select required value={asset} onChange={(e) => setAsset(e.target.value)}>
        <option value="">Choose visible asset</option>
        {batteries.map((b) => (
          <option value={b.id} key={b.id}>
            {b.internal_id} · {human(b.state)}
          </option>
        ))}
      </select>
    </Field>
  );
  const operationField = (
    <Field label="Defined operation">
      <select value={operation} onChange={(e) => setOperation(e.target.value)}>
        {OPERATIONS.map((o) => (
          <option key={o} value={o}>
            {human(o)}
          </option>
        ))}
      </select>
    </Field>
  );
  const hBody = (h: Handoff) => ({
    item_id: h.item_id,
    receiver_facility_id: h.receiver_facility_id,
    price_paise: h.terms.price_paise,
    payer_org_id: h.terms.payer_org_id,
    budget_paise: cap === "" ? null : Math.round(Number(cap) * 100),
    acceptance_specification: h.terms.data.acceptance_specification,
    evidence,
    window_start: h.data.window_start,
    window_end: h.data.window_end,
  });
  const opOut = () => ({
    identifier: outputId,
    kind,
    mass_kg: Number(outputMass),
    category,
    specification: spec,
    evidence,
    chemistry: "UNKNOWN",
  });
  return {
    actor,
    action,
    version,
    batteries,
    network,
    tab,
    setTab,
    asset,
    setAsset,
    facility,
    setFacility,
    operation,
    setOperation,
    evidence,
    setEvidence,
    procedure,
    setProcedure,
    observations,
    setObservations,
    measurement,
    setMeasurement,
    spec,
    setSpec,
    outcome,
    setOutcome,
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
    customer,
    setCustomer,
    receiver,
    setReceiver,
    price,
    setPrice,
    cap,
    setCap,
    quote,
    setQuote,
    carrier,
    setCarrier,
    item,
    setItem,
    payer,
    setPayer,
    trace,
    setTrace,
    event,
    setEvent,
    condition,
    setCondition,
    physical,
    setPhysical,
    capacity,
    setCapacity,
    chemistries,
    setChemistries,
    formats,
    setFormats,
    categories,
    setCategories,
    measurementUnit,
    setMeasurementUnit,
    measurementName,
    setMeasurementName,
    extraOutputs,
    setExtraOutputs,
    assessments,
    aError,
    items,
    iError,
    jobs,
    jError,
    products,
    lots,
    handoffs,
    requests,
    capabilities,
    ownFacilities,
    isReviewer,
    pickFacility,
    pickAsset,
    operationField,
    hBody,
    opOut,
  };
}
