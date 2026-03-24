import { NextResponse } from "next/server";
import { queryOne } from "@/lib/db";
import { ULRICH_FIXTURE_MODE } from "@/lib/fixture-mode";

type ReportRow = {
  id: string;
  inspection_id: string;
  narrative: string | null;
  hers_index: number | null;
  compliance_standard: string;
  status: string;
  generated_at: string | null;
  recommendations: unknown[];
};

type InspectionRow = {
  address: string;
  builder: string;
  inspector: string;
  sqft: number | null;
  stories: number | null;
  foundation_type: string | null;
  blower_cfm50: number | null;
  blower_ach50: number | null;
  blower_pass_fail: boolean | null;
  duct_cfm25_total: number | null;
  duct_cfm25_outside: number | null;
  insulation: Array<{ location: string; rValue: number; type: string; depth: number }>;
  windows: Array<{ location: string; uFactor: number; shgc: number; frameType: string }>;
  hvac_systems: Array<{ systemType: string; model: string; capacity: string; efficiencyRating: string }>;
};

/**
 * GET /api/reports/:id/pdf
 *
 * Returns a print-ready HTML document for the report.
 * Open in browser and print to PDF, or use with a headless browser.
 */
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;

  if (ULRICH_FIXTURE_MODE) {
    return new Response(buildHtml("123 Fixture Lane", "Test Builder", "Shaun", "This is a fixture report narrative.", null, null), {
      headers: { "Content-Type": "text/html; charset=utf-8" },
    });
  }

  const report = await queryOne<ReportRow>(
    `SELECT * FROM reports WHERE id = $1`,
    [id],
  );

  if (!report) {
    return NextResponse.json({ error: "Report not found" }, { status: 404 });
  }

  const inspection = await queryOne<InspectionRow>(
    `SELECT * FROM inspections WHERE id = $1`,
    [report.inspection_id],
  );

  if (!inspection) {
    return NextResponse.json({ error: "Inspection not found" }, { status: 404 });
  }

  const html = buildHtml(
    inspection.address,
    inspection.builder,
    inspection.inspector,
    report.narrative ?? "No narrative generated.",
    inspection,
    report,
  );

  return new Response(html, {
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Content-Disposition": `inline; filename="report-${id}.html"`,
    },
  });
}

function buildHtml(
  address: string,
  builder: string,
  inspector: string,
  narrative: string,
  inspection: InspectionRow | null,
  report: ReportRow | null,
): string {
  const date = report?.generated_at
    ? new Date(report.generated_at).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })
    : new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });

  const recs = (report?.recommendations ?? []) as Array<{
    category: string; description: string; estimatedCost: string;
    estimatedSavings: string; priority: string;
  }>;

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Energy Inspection Report — ${escapeHtml(address)}</title>
  <style>
    @page { margin: 0.75in; size: letter; }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; font-size: 11pt; line-height: 1.5; color: #1a1a1a; }
    .header { text-align: center; border-bottom: 2px solid #2d6a4f; padding-bottom: 16px; margin-bottom: 24px; }
    .header h1 { font-size: 20pt; color: #2d6a4f; margin-bottom: 4px; }
    .header .subtitle { font-size: 11pt; color: #666; }
    .meta { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 24px; }
    .meta-item { padding: 8px 12px; background: #f8f9fa; border-radius: 4px; }
    .meta-label { font-size: 9pt; text-transform: uppercase; letter-spacing: 0.05em; color: #666; }
    .meta-value { font-weight: 600; }
    h2 { font-size: 14pt; color: #2d6a4f; border-bottom: 1px solid #dee2e6; padding-bottom: 4px; margin: 20px 0 12px; }
    .narrative { white-space: pre-wrap; margin-bottom: 24px; }
    table { width: 100%; border-collapse: collapse; margin-bottom: 16px; font-size: 10pt; }
    th { background: #2d6a4f; color: white; padding: 6px 10px; text-align: left; font-weight: 600; }
    td { padding: 6px 10px; border-bottom: 1px solid #dee2e6; }
    tr:nth-child(even) td { background: #f8f9fa; }
    .test-result { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 12px; }
    .test-item { padding: 8px; background: #f8f9fa; border-radius: 4px; }
    .pass { color: #2d6a4f; font-weight: 700; }
    .fail { color: #d32f2f; font-weight: 700; }
    .footer { margin-top: 32px; padding-top: 12px; border-top: 1px solid #dee2e6; text-align: center; font-size: 9pt; color: #999; }
    .rec { padding: 8px 12px; margin-bottom: 8px; border-left: 3px solid; border-radius: 2px; }
    .rec-high { border-color: #d32f2f; background: #fef2f2; }
    .rec-medium { border-color: #f59e0b; background: #fffbeb; }
    .rec-low { border-color: #2d6a4f; background: #f0fdf4; }
    @media print { body { font-size: 10pt; } .no-print { display: none; } }
  </style>
</head>
<body>
  <div class="no-print" style="padding:8px 16px;background:#2d6a4f;color:white;text-align:center">
    <button onclick="window.print()" style="background:white;color:#2d6a4f;border:none;padding:8px 24px;border-radius:4px;cursor:pointer;font-weight:600">Print / Save as PDF</button>
  </div>

  <div class="header">
    <h1>Ulrich Energy</h1>
    <div class="subtitle">Residential Energy Inspection Report</div>
  </div>

  <div class="meta">
    <div class="meta-item"><div class="meta-label">Property</div><div class="meta-value">${escapeHtml(address)}</div></div>
    <div class="meta-item"><div class="meta-label">Builder</div><div class="meta-value">${escapeHtml(builder)}</div></div>
    <div class="meta-item"><div class="meta-label">Inspector</div><div class="meta-value">${escapeHtml(inspector)}</div></div>
    <div class="meta-item"><div class="meta-label">Report Date</div><div class="meta-value">${date}</div></div>
    ${report?.hers_index != null ? `<div class="meta-item"><div class="meta-label">HERS Index</div><div class="meta-value">${report.hers_index}</div></div>` : ""}
    ${report?.compliance_standard ? `<div class="meta-item"><div class="meta-label">Standard</div><div class="meta-value">${escapeHtml(report.compliance_standard.replace(/_/g, " "))}</div></div>` : ""}
  </div>

  <h2>Executive Summary</h2>
  <div class="narrative">${escapeHtml(narrative)}</div>

  ${inspection?.blower_cfm50 != null ? `
  <h2>Blower Door Test Results</h2>
  <div class="test-result">
    <div class="test-item"><div class="meta-label">CFM50</div><div class="meta-value">${inspection.blower_cfm50}</div></div>
    <div class="test-item"><div class="meta-label">ACH50</div><div class="meta-value">${inspection.blower_ach50 ?? "—"}</div></div>
    <div class="test-item"><div class="meta-label">Result</div><div class="meta-value ${inspection.blower_pass_fail ? "pass" : "fail"}">${inspection.blower_pass_fail ? "PASS" : "FAIL"}</div></div>
  </div>` : ""}

  ${inspection?.duct_cfm25_total != null ? `
  <h2>Duct Leakage Test Results</h2>
  <div class="test-result">
    <div class="test-item"><div class="meta-label">CFM25 Total</div><div class="meta-value">${inspection.duct_cfm25_total}</div></div>
    <div class="test-item"><div class="meta-label">CFM25 Outside</div><div class="meta-value">${inspection.duct_cfm25_outside ?? "—"}</div></div>
  </div>` : ""}

  ${(inspection?.insulation ?? []).length > 0 ? `
  <h2>Insulation</h2>
  <table>
    <tr><th>Location</th><th>R-Value</th><th>Type</th><th>Depth</th></tr>
    ${(inspection?.insulation ?? []).map(i => `<tr><td>${escapeHtml(i.location)}</td><td>R-${i.rValue}</td><td>${escapeHtml(i.type.replace(/_/g, " "))}</td><td>${i.depth}"</td></tr>`).join("")}
  </table>` : ""}

  ${(inspection?.windows ?? []).length > 0 ? `
  <h2>Windows</h2>
  <table>
    <tr><th>Location</th><th>U-Factor</th><th>SHGC</th><th>Frame</th></tr>
    ${(inspection?.windows ?? []).map(w => `<tr><td>${escapeHtml(w.location)}</td><td>${w.uFactor}</td><td>${w.shgc}</td><td>${escapeHtml(w.frameType)}</td></tr>`).join("")}
  </table>` : ""}

  ${(inspection?.hvac_systems ?? []).length > 0 ? `
  <h2>HVAC Systems</h2>
  <table>
    <tr><th>Type</th><th>Model</th><th>Capacity</th><th>Efficiency</th></tr>
    ${(inspection?.hvac_systems ?? []).map(h => `<tr><td>${escapeHtml(h.systemType.replace(/_/g, " "))}</td><td>${escapeHtml(h.model)}</td><td>${escapeHtml(h.capacity)}</td><td>${escapeHtml(h.efficiencyRating)}</td></tr>`).join("")}
  </table>` : ""}

  ${recs.length > 0 ? `
  <h2>Recommendations</h2>
  ${recs.map(r => `<div class="rec rec-${r.priority}"><strong>${escapeHtml(r.category)}</strong> — ${escapeHtml(r.description)}<br><span style="font-size:9pt;color:#666">Est. cost: ${escapeHtml(r.estimatedCost)} | Est. savings: ${escapeHtml(r.estimatedSavings)}</span></div>`).join("")}` : ""}

  <div class="footer">
    Generated by Ulrich Energy Inspection System &middot; ${date}
  </div>
</body>
</html>`;
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
