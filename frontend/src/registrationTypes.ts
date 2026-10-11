export type PBSLevel = "L1" | "L2" | "L3" | "L4" | "L5";
export interface PBSDefinition {
  level: PBSLevel;
  title: string;
  description: string;
  color: string;
}
export interface ReportedInspection {
  conducted: "YES" | "NO" | "UNKNOWN";
  date: string | null;
  inspector: string | null;
  source:
    "MEASURED" | "BMS_REPORTED" | "ESTIMATED" | "OTHER_REPORTED" | "UNKNOWN";
  scope: "INDIVIDUAL" | "SAMPLE_ONLY" | "UNKNOWN";
  soh_percent: number | null;
  soc_percent: number | null;
  voltage_v: number | null;
  capacity_ah: number | null;
  resistance: number | null;
  resistance_unit: string;
  resistance_method: string | null;
  imbalance_v: number | null;
  temperature: string | null;
  fault_codes: string | null;
  findings: string | null;
  charge_discharge_results: string | null;
  other_tests: string | null;
}
export interface RegistrationInput {
  internal_id: string;
  registration_title: string;
  form: string;
  application_type: string;
  quantity: number;
  address: string;
  lat: number | null;
  lng: number | null;
  removal_date: string | null;
  removal_reason: string;
  condition: string;
  manufacturer: string | null;
  model: string | null;
  serial_number: string | null;
  chemistry: string;
  manufacturing_date: string | null;
  manufacturing_year: number | null;
  nominal_voltage: number | null;
  nominal_capacity_ah: number | null;
  rated_energy_kwh: number | null;
  mass_kg: number | null;
  age_years: number | null;
  bms_available: string;
  other_specifications: string | null;
  inspection: ReportedInspection;
  pbs: PBSLevel | null;
  pbs_comments: string;
  current_owner: string | null;
  current_custodian: string | null;
  collection_availability: string;
  preferred_timeframe: string | null;
  handling_instructions: string | null;
  additional_information: string;
  mixed_batch: boolean;
  owner_org_id: string;
  custodian_org_id: string;
  authority_confirmed: boolean;
  flags?: Record<string, string>;
  window_start: string | null;
  window_end: string | null;
}
export const applicationTypes = [
  "TWO_WHEELER",
  "THREE_WHEELER",
  "FOUR_WHEELER",
  "COMMERCIAL_VEHICLE",
  "OTHER",
  "UNKNOWN",
];
export const chemistryOptions = [
  "LFP",
  "NMC",
  "NCA",
  "LCO",
  "LMO",
  "lead-acid",
  "NiMH",
  "other",
  "UNKNOWN",
];
export const conditionOptions = [
  "WORKING",
  "DEGRADED",
  "NON_FUNCTIONAL",
  "DAMAGED_REPORTED",
  "UNKNOWN",
];
export const categoryOptions = ["PACK", "MODULE", "CELL", "OTHER", "UNKNOWN"];
export const documentDescription =
  "You may upload any documents that you consider relevant to this battery registration. These could include a battery datasheet, technical booklet, purchase or ownership records, proof of authorization to transfer the battery, inspection reports, test results, warranty records, or photographs. Please upload only documents that are available to you and that you are permitted to share. Supporting documents are helpful for verification, but you can submit the registration without uploading any files.";
export const blankInspection: ReportedInspection = {
  conducted: "UNKNOWN",
  date: null,
  inspector: null,
  source: "UNKNOWN",
  scope: "UNKNOWN",
  soh_percent: null,
  soc_percent: null,
  voltage_v: null,
  capacity_ah: null,
  resistance: null,
  resistance_unit: "UNKNOWN",
  resistance_method: null,
  imbalance_v: null,
  temperature: null,
  fault_codes: null,
  findings: null,
  charge_discharge_results: null,
  other_tests: null,
};
export interface SafetyScope {
  chemistries?: string[] | null;
  formats?: string[] | null;
  conditions?: string[] | null;
  application_types: string[];
  max_pbs: PBSLevel | null;
  specialist_assessment: boolean;
  damaged_handling: boolean;
  critical_hazard_handling: boolean;
  dangerous_goods: boolean;
  service_areas: string[];
  restrictions: string;
}
export const blankSafety: SafetyScope = {
  application_types: [],
  max_pbs: null,
  specialist_assessment: false,
  damaged_handling: false,
  critical_hazard_handling: false,
  dangerous_goods: false,
  service_areas: [],
  restrictions: "",
};
