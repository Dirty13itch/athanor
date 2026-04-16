export type InspectionStatus = "draft" | "submitted" | "reported" | "delivered";

export type FoundationType = "slab" | "crawlspace" | "basement" | "pier_beam";
export type InsulationType = "fiberglass_batt" | "blown_cellulose" | "blown_fiberglass" | "spray_foam_open" | "spray_foam_closed" | "rigid_foam" | "mineral_wool";
export type WindowFrameType = "vinyl" | "wood" | "aluminum" | "fiberglass" | "composite";
export type HvacSystemType = "furnace" | "ac" | "heat_pump" | "boiler" | "mini_split" | "geothermal";
export type DuctTestMethod = "total_leakage" | "leakage_to_outside" | "both";

export interface BuildingEnvelope {
  orientation: string;
  sqft: number;
  ceilingHeight: number;
  stories: number;
  foundationType: FoundationType;
}

export interface BlowerDoorTest {
  cfm50: number;
  ach50: number;
  enclosureArea: number;
  passFail: boolean;
}

export interface DuctLeakageTest {
  cfm25Total: number;
  cfm25Outside: number;
  testMethod: DuctTestMethod;
}

export interface InsulationEntry {
  id: string;
  location: string;
  rValue: number;
  type: InsulationType;
  depth: number;
  notes?: string;
}

export interface WindowEntry {
  id: string;
  location: string;
  uFactor: number;
  shgc: number;
  frameType: WindowFrameType;
  count: number;
  area: number;
}

export interface HvacSystem {
  id: string;
  systemType: HvacSystemType;
  model: string;
  capacity: string;
  efficiencyRating: string;
  ductLocation: string;
}

export interface InspectionPhoto {
  id: string;
  filename: string;
  section: string;
  caption: string;
  uploadedAt: string;
}

export interface Inspection {
  id: string;
  projectId: string;
  address: string;
  builder: string;
  inspector: string;
  status: InspectionStatus;
  createdAt: string;
  updatedAt: string;
  buildingEnvelope?: BuildingEnvelope;
  blowerDoor?: BlowerDoorTest;
  ductLeakage?: DuctLeakageTest;
  insulation: InsulationEntry[];
  windows: WindowEntry[];
  hvacSystems: HvacSystem[];
  photos: InspectionPhoto[];
}

export interface InspectionListItem {
  id: string;
  address: string;
  builder: string;
  inspector: string;
  status: InspectionStatus;
  createdAt: string;
  hersIndex?: number;
}

export interface CreateInspectionRequest {
  projectId?: string;
  address: string;
  builder: string;
  inspector?: string;
}
