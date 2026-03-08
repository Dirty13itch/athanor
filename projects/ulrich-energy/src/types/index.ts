// Ulrich Energy — TypeScript types matching PostgreSQL schema

export type JobStatus = "draft" | "submitted" | "reported" | "delivered";
export type ReportStatus = "draft" | "generating" | "complete" | "error";
export type SystemType = "furnace" | "ac" | "heat_pump" | "boiler" | "mini_split" | "other";
export type FoundationType = "basement" | "crawlspace" | "slab" | "mixed";
export type FrameType = "vinyl" | "wood" | "aluminum" | "fiberglass" | "composite";
export type DuctTestMethod = "total_leakage" | "leakage_to_outside" | "both";

// -- Core job entity --

export interface Job {
  id: string; // UUID
  address: string;
  builder: string | null;
  inspector: string;
  status: JobStatus;
  created_at: string; // ISO 8601
  updated_at: string;
}

export interface JobCreateInput {
  address: string;
  builder?: string;
  inspector?: string;
}

export interface JobUpdateInput {
  address?: string;
  builder?: string;
  inspector?: string;
  status?: JobStatus;
  building_envelope?: BuildingEnvelopeInput;
  blower_door?: BlowerDoorInput;
  duct_leakage?: DuctLeakageInput;
  insulation?: InsulationInput[];
  windows?: WindowInput[];
  hvac_systems?: HVACSystemInput[];
}

// -- Building envelope --

export interface BuildingEnvelope {
  job_id: string;
  orientation: string | null;
  sqft: number | null;
  ceiling_height: number | null;
  stories: number | null;
  foundation_type: FoundationType | null;
}

export type BuildingEnvelopeInput = Omit<BuildingEnvelope, "job_id">;

// -- Blower door test --

export interface BlowerDoor {
  job_id: string;
  cfm50: number | null;
  ach50: number | null;
  enclosure_area: number | null;
  pass_fail: boolean | null;
}

export type BlowerDoorInput = Omit<BlowerDoor, "job_id">;

// -- Duct leakage test --

export interface DuctLeakage {
  job_id: string;
  cfm25_total: number | null;
  cfm25_outside: number | null;
  test_method: DuctTestMethod | null;
}

export type DuctLeakageInput = Omit<DuctLeakage, "job_id">;

// -- Insulation entries --

export interface Insulation {
  id: number;
  job_id: string;
  location: string;
  r_value: number | null;
  type: string | null;
  depth: number | null;
  notes: string | null;
}

export type InsulationInput = Omit<Insulation, "id" | "job_id">;

// -- Window entries --

export interface Window {
  id: number;
  job_id: string;
  location: string;
  u_factor: number | null;
  shgc: number | null;
  frame_type: FrameType | null;
  count: number;
  area: number | null;
}

export type WindowInput = Omit<Window, "id" | "job_id">;

// -- HVAC systems --

export interface HVACSystem {
  id: number;
  job_id: string;
  system_type: SystemType;
  model: string | null;
  capacity: string | null;
  efficiency_rating: string | null; // AFUE/SEER/HSPF value
  duct_location: string | null;
}

export type HVACSystemInput = Omit<HVACSystem, "id" | "job_id">;

// -- Photos --

export interface Photo {
  id: number;
  job_id: string;
  filename: string;
  section: string | null;
  caption: string | null;
  uploaded_at: string;
}

// -- Reports --

export interface Report {
  job_id: string;
  hers_index: number | null;
  narrative: string | null;
  pdf_path: string | null;
  generated_at: string;
  status: ReportStatus;
}

// -- Clients (not in original schema — added for client management) --

export interface Client {
  id: string;
  name: string;
  company: string | null;
  email: string | null;
  phone: string | null;
  created_at: string;
}

export type ClientCreateInput = Omit<Client, "id" | "created_at">;

// -- Full inspection (job with all related data) --

export interface Inspection {
  job: Job;
  building_envelope: BuildingEnvelope | null;
  blower_door: BlowerDoor | null;
  duct_leakage: DuctLeakage | null;
  insulation: Insulation[];
  windows: Window[];
  hvac_systems: HVACSystem[];
  photos: Photo[];
  report: Report | null;
}

// -- Analytics --

export interface DashboardAnalytics {
  jobs_by_status: Record<JobStatus, number>;
  total_jobs: number;
  avg_hers_index: number | null;
  avg_hers_by_builder: { builder: string; avg_hers: number; count: number }[];
  common_failures: {
    blower_door_fail_rate: number;
    avg_cfm50: number;
    avg_ach50: number;
    avg_duct_leakage: number;
  };
  revenue: {
    total: number;
    this_month: number;
    rate_per_job: number;
  };
}

// -- API response wrapper --

export interface ApiResponse<T> {
  data: T;
  error?: never;
}

export interface ApiError {
  data?: never;
  error: string;
  details?: string;
}

export type ApiResult<T> = ApiResponse<T> | ApiError;
