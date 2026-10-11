import type { SafetyScope } from "./registrationTypes";

export interface OrganisationProfile {
  id: string;
  name: string;
  display_name: string;
  description: string;
  organisation_type: string;
  website: string;
  regions: string[];
  roles: string[];
  verification: string;
  logo_url: string | null;
  contact_visibility: string;
  editable_profile?: ProfileEdit;
  facilities: {
    id: string;
    name: string;
    kind: string;
    lat: number;
    lng: number;
    registration: string;
    description: string;
    address?: string;
  }[];
  capabilities: CapabilitySummary[];
}
export interface CapabilitySummary {
  id: string;
  kind: string;
  facility_id: string | null;
  name: string;
  status: string;
  scope: {
    declared_safety?: SafetyScope;
    verified_safety?: SafetyScope;
    chemistries: string[];
    conditions?: string[];
    center?: number[];
    radius_km?: number;
    formats: string[];
    material_categories: string[];
    handling_scope: string | null;
    capacity_kg: number | null;
  };
  valid_until: string | null;
  updated_at: string;
}
export interface ProfileEdit {
  display_name: string;
  description: string;
  organisation_type: string;
  business_email: string;
  business_phone: string;
  website: string;
  primary_address: string;
  regions: string[];
  business_identifiers: string;
  contact_visibility: string;
}
export interface VerificationRequest {
  id: string;
  organisation_id: string;
  kind: string;
  action: string;
  facility_id: string | null;
  target_id: string | null;
  status: string;
  updated_at: string;
  requested_scope: {
    role?: string;
    operation?: string;
    pathway?: string;
    description: string;
    [key: string]: unknown;
  };
  data: {
    history: {
      action: string;
      timestamp: string;
      reason?: string;
      message?: string;
    }[];
  };
}
export interface Contacts {
  business_email: string;
  business_phone: string;
  primary_address: string;
}
