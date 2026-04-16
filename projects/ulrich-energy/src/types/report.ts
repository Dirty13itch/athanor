export type ReportStatus = "draft" | "generated" | "reviewed" | "delivered";

export type ComplianceStandard =
  | "iecc_2021"
  | "iecc_2018"
  | "iecc_2015"
  | "energy_star_v3.1"
  | "energy_star_v3.2"
  | "minnesota_energy_code";

export interface ReportTemplate {
  id: string;
  name: string;
  description: string;
  complianceStandard: ComplianceStandard;
  sections: string[];
}

export interface Report {
  id: string;
  inspectionId: string;
  hersIndex: number | null;
  narrative: string;
  pdfPath: string | null;
  complianceStandard: ComplianceStandard;
  templateId: string;
  status: ReportStatus;
  generatedAt: string | null;
  deliveredAt: string | null;
  recipientEmail: string | null;
  recommendations: ReportRecommendation[];
}

export interface ReportRecommendation {
  id: string;
  category: string;
  description: string;
  estimatedCost: string;
  estimatedSavings: string;
  priority: "high" | "medium" | "low";
}

export interface GenerateReportRequest {
  inspectionId: string;
  templateId?: string;
  complianceStandard?: ComplianceStandard;
}

export interface ReportListItem {
  id: string;
  inspectionId: string;
  address: string;
  hersIndex: number | null;
  status: ReportStatus;
  generatedAt: string | null;
}
