export interface Actor {
  id: string;
  name: string;
  role: string;
  organisation_id: string;
  selected_role?: string;
  roles?: string[];
  email?: string;
  platform_admin?: boolean;
  memberships?: {
    id: string;
    organisation_id: string;
    organisation_name: string;
    roles: string[];
  }[];
  synthetic: boolean;
}
// Domain records mirror API columns; data carries versioned input snapshots and evidence metadata.
export interface RecordBase {
  id: string;
  created_at: string;
  data: { [key: string]: any };
}
export interface Battery extends RecordBase {
  internal_id: string;
  state: string;
  chemistry: string;
  form: string;
  condition: string;
  mass_kg: number | null;
  quantity: number;
  lat: number | null;
  lng: number | null;
  owner_org_id: string;
  custodian_org_id: string;
  current_holder_org_id: string;
  originator_org_id: string;
  authority_confirmed: boolean;
  handling_concern?: {
    required_pbs_capability: string | null;
    source: string;
    notice: string;
  };
  evidence?: Evidence[];
  dispositions?: RecordBase[];
}
export interface Evidence extends RecordBase {
  kind: string;
  filename: string;
  checksum: string;
  version: number;
  review_status: string;
}
export interface Organisation extends RecordBase {
  name: string;
  role: string;
  verification: string;
  active: boolean;
  synthetic: boolean;
}
export interface Facility extends RecordBase {
  name: string;
  organisation_id: string;
  kind: string;
  lat: number;
  lng: number;
  registration: string;
  valid_until: string;
  active: boolean;
}
export interface Capability extends RecordBase {
  facility_id: string;
  pathway: string;
  verification: string;
  capacity_kg: number;
  available_kg: number;
  valid_until: string;
}
export interface Transporter extends RecordBase {
  name: string;
  organisation_id: string;
  verification: string;
  capacity_kg: number;
  valid_until: string;
  active: boolean;
}
export interface Network {
  organisations: Organisation[];
  facilities: Facility[];
  capabilities: Capability[];
  transporters: Transporter[];
}
export interface Listing extends RecordBase {
  asset_id: string;
  seller_org_id: string;
  status: string;
  expires_at: string;
  asset: {
    internal_id: string;
    chemistry: string;
    condition: string;
    mass_kg: number | null;
  };
  eligible_for_actor: Candidate[];
}
export interface Offer extends RecordBase {
  listing_id: string;
  buyer_org_id: string;
  facility_id: string;
  pathway: string;
  price_paise: number;
  expires_at: string;
  status: string;
}
export interface Terms extends RecordBase {
  version: number;
  payer_org_id: string;
  budget_paise: number;
  price_paise: number;
  confirmations: string[];
}
export interface Transaction extends RecordBase {
  asset_id: string;
  offer_id: string;
  seller_org_id: string;
  buyer_org_id: string;
  facility_id: string;
  pathway: string;
  status: string;
  logistics_status: string;
  terms_version: number;
  terms: Terms | null;
  terms_history: Terms[];
  asset: { internal_id: string; state: string; current_holder_org_id: string };
}
export interface Reason {
  code: string;
  message: string;
  field?: string;
  blocking?: boolean;
  next_action?: string;
}
export interface Candidate {
  status?: string;
  facility: Facility;
  pathway: string;
  eligible: boolean;
  reasons: Reason[];
  capability_id: string | null;
}
export interface Route extends RecordBase {
  transaction_id: string;
  terms_version: number;
  hub_id: string | null;
  distance_km: number;
  hours: number;
  estimated_cost_paise: number | null;
  score: number;
  expires_at: string;
}
export interface Quote extends RecordBase {
  transaction_id: string;
  route_id: string;
  transporter_id: string;
  total_paise: number | null;
  terms_version: number;
  status: string;
  expires_at: string;
}
export interface Shipment extends RecordBase {
  transaction_id: string;
  route_id: string;
  quote_id: string;
  state: string;
  asset: {
    id: string;
    internal_id: string;
    current_holder_org_id: string;
    custody_segments?: any[];
  };
  transporter_org_id: string;
  buyer_org_id: string;
  seller_org_id: string;
  route: Route;
  custody?: Custody[];
  telemetry?: Telemetry[];
  closure?: { can_close: boolean; reasons: string[] };
}
export interface Custody extends RecordBase {
  event_type: string;
  actor_id: string;
  previous_holder: string;
  new_holder: string;
}
export interface Telemetry extends RecordBase {
  source: string;
  alert: boolean;
}
export interface ExceptionCase extends RecordBase {
  object_type: string;
  object_id: string;
  category: string;
  severity: string;
  owner_org_id: string;
  status: string;
  next_action: string;
  due_at: string;
  resolution: string | null;
}
export interface Settlement extends RecordBase {
  transaction_id: string;
  status: string;
  payer_org_id: string;
  payee_org_id: string;
  amount_paise: number;
}
export type Action = (
  path: string,
  body?: unknown,
  method?: string,
) => Promise<any>;
export const FLAGS = [
  "collision_crush",
  "swelling",
  "leakage",
  "heat",
  "smoke_fire",
  "odour",
  "exposed_conductors",
  "water_flood",
  "impact_drop",
  "thermal_event",
  "unknown_history",
];
export const PATHWAYS = [
  "REPAIR_REFURBISHMENT",
  "SECOND_LIFE_ASSESSMENT",
  "RECYCLING",
];
