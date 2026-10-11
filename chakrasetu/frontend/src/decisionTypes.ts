export type DecisionPath =
  "AUTOMOTIVE" | "REFURBISHMENT" | "SECOND_LIFE" | "RECYCLING" | "ASSESSMENT";
export interface RuleOutcome {
  code: string;
  passed: boolean | null;
  message: string;
}
export interface FinanceValue {
  amount_paise: number;
  source: string;
  reference: string;
  recorded_at: string;
  valid_until: string;
  year: number;
  uncertainty_paise: number;
}
export interface FinanceInput {
  currency: "INR";
  perspective: "WHOLE_PATHWAY" | "ORIGINATOR_TRANSACTION";
  basis: "NET_TRANSACTION" | "NPV";
  horizon_years: number;
  discount_rate: number | null;
  benefits: FinanceValue[];
  costs: Record<string, FinanceValue>;
  offer_id?: string;
  transport_quote_id?: string;
  facility_id?: string;
}
export interface PathwayResult {
  pathway: DecisionPath;
  label: string;
  status: string;
  rules: RuleOutcome[];
  missing_information: string[];
  next_action: string;
  qualification_conditions: string[];
  economics: {
    complete: boolean;
    ranking_eligible: boolean;
    missing: string[];
    net_paise: number | null;
    range_paise: [number, number] | null;
    basis?: string;
    perspective?: string;
    horizon_years?: number;
    provisional: boolean;
    inputs: Partial<FinanceInput>;
    formula?: string;
  };
  network: {
    complete: boolean;
    conditions?: string[];
    stages: {
      operation: string;
      receivers: {
        facility_id: string;
        name: string;
        transporters: { id: string; name: string }[];
      }[];
    }[];
    rejected: {
      name?: string;
      operation?: string;
      reasons: { code: string; message: string }[];
    }[];
  };
}
export interface PathwayDecision {
  generated_at: string;
  rule_version: string;
  asset_id?: string;
  decision_id?: string;
  recorded_at?: string;
  stale?: boolean;
  safety_state: string;
  reported_pbs: string | null;
  required_handling_level: string | null;
  recommended_pathway: DecisionPath | null;
  similar_pathways: DecisionPath[];
  evaluation_state: string;
  recommendation_reason: string;
  soh: { value: number | null; source: string; screening_band: string };
  pathways: PathwayResult[];
  required_tests: string[];
  next_action: string;
  restrictions: { code: string; message: string }[];
  evidence_used: {
    id?: string;
    type: string;
    source: string;
    application_reference?: string;
    limitations?: string;
    recorded_at?: string;
  }[];
  input_fingerprint: string;
  request_inputs?: Record<string, FinanceInput>;
  overrides?: { selected_pathway: string; reason: string; active?: boolean };
  override?: { selected_pathway: string; reason: string; active?: boolean };
  recalculation_warning?: string;
  execution_status: string;
}
export interface DecisionPolicy {
  policy: {
    version: string;
    automotive_screen_soh: number;
    second_life_screen_soh: number;
    description: string;
  };
  pbs_levels: { level: string; title: string; description: string }[];
  pathways: Record<DecisionPath, string>;
  cost_components: Record<DecisionPath, string[]>;
}
export interface ExplorerInputs {
  pbs: string;
  soh_percent: number | null;
  measurements_available: boolean;
  repairable: boolean | null;
  critical_hazard: boolean;
  application_qualified: boolean;
  application: "VEHICLE" | "STATIONARY" | "UNASSESSED";
  qualified_receiver: boolean;
  qualified_transporter: boolean;
  quotes_available: boolean;
}
