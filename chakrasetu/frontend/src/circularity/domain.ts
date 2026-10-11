export interface Assessment {
  id: string;
  asset_id: string;
  facility_id: string;
  intended_operation: string;
  state: string;
  data: { procedure: string; report?: unknown; review?: unknown };
}
export interface Item {
  id: string;
  identifier: string;
  kind: string;
  state: string;
  mass_kg: number | null;
  owner_org_id: string;
  custodian_org_id: string;
  facility_id: string | null;
  data: {
    category?: string;
    specification?: string;
    evidence?: string;
    synthetic?: boolean;
  };
}
export interface Job {
  id: string;
  facility_id: string;
  operation: string;
  state: string;
  inputs: { item_id: string; mass_kg: number }[];
  outputs: { item_id: string; mass_kg: number }[];
  data: {
    owner_authorizations: Record<string, unknown>;
    output_ownership_terms: string;
    synthetic: boolean;
  };
}
export interface Product {
  id: string;
  item_id: string;
  state: string;
  intended_application: string;
  item: Item;
  events: { id: string; event_type: string; data: unknown }[];
}
export interface Lot {
  id: string;
  item_id: string;
  category: string;
  quantity: number;
  unit: string;
  item: Item;
  source_job_id: string;
}
export interface Capability {
  id: string;
  facility_id: string;
  operation: string;
  verified: boolean;
  capacity_kg: number | null;
  valid_until: string | null;
  chemistries: string[];
  formats: string[];
  material_categories: string[];
}
export interface Terms {
  version: number;
  price_paise: number | null;
  budget_paise: number | null;
  payer_org_id: string;
  confirmations: string[];
  data: { acceptance_specification: string };
}
export interface Handoff {
  id: string;
  version: number;
  state: string;
  item_id: string;
  seller_org_id: string;
  buyer_org_id: string;
  receiver_facility_id: string;
  item: Item;
  terms: Terms;
  history: Terms[];
  custody: {
    id: string;
    event_type: string;
    previous_org_id: string;
    new_org_id: string;
  }[];
  data: {
    window_start: string;
    window_end: string;
    quote?: { total_paise: number; expires_at: string };
    settlement: string;
    route?: unknown;
    synthetic: boolean;
  };
}
export interface Candidate {
  id: string;
  pathway: string;
  status: string;
  distance_km: number;
  stages: { operation: string; facility_id: string; name: string }[];
  conditions: { code: string; message: string }[];
  economics: {
    net_paise: number | null;
    cost_per_battery_paise: number | null;
    missing: string[];
    complete: boolean;
    source: string;
  };
  warnings: string[];
}
export interface Decision {
  decision_id: string;
  recommended_id: string | null;
  recommendation_reason: string;
  candidates: Candidate[];
  rejected: {
    facility_id?: string;
    operation?: string;
    pathway: string;
    reasons: { code: string; message: string }[];
  }[];
  evidence_used: unknown[];
  generated_at: string;
}
export const OPERATIONS = [
  "ASSESSMENT",
  "REFURBISHMENT",
  "REPURPOSING",
  "INTEGRATION",
  "DISMANTLING",
  "RECYCLING",
  "PROCESSING",
  "REFINING",
  "MANUFACTURING",
];
export const days = (n: number) =>
  new Date(Date.now() + n * 86400000).toISOString();
export const reviewBody = (evidence: string, accepted = true) => ({
  accepted,
  evidence,
  reason: evidence,
  valid_until: days(30),
});
