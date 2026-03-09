import { NextResponse } from "next/server";
import { queryOne, query } from "@/lib/db";

type StatusRow = {
  status: string;
  count: string;
};

type HersBuilderRow = {
  builder: string;
  avg_hers: string;
  count: string;
};

type BlowerRow = {
  total: string;
  failed: string;
  avg_cfm50: string;
  avg_ach50: string;
};

type DuctRow = {
  avg_cfm25_total: string;
};

type HersRow = {
  avg_hers: string;
};

export async function GET() {
  try {
    const [statusRows, hersRow, hersByBuilder, blowerRow, ductRow] = await Promise.all([
      query<StatusRow>(
        `SELECT status, COUNT(*)::text AS count FROM inspections GROUP BY status`,
      ),
      queryOne<HersRow>(
        `SELECT AVG(hers_index)::text AS avg_hers FROM inspections WHERE hers_index IS NOT NULL`,
      ),
      query<HersBuilderRow>(
        `SELECT builder, AVG(hers_index)::text AS avg_hers, COUNT(*)::text AS count
         FROM inspections
         WHERE hers_index IS NOT NULL
         GROUP BY builder
         ORDER BY COUNT(*) DESC
         LIMIT 10`,
      ),
      queryOne<BlowerRow>(
        `SELECT COUNT(*)::text AS total,
                COUNT(*) FILTER (WHERE blower_pass_fail = false)::text AS failed,
                AVG(blower_cfm50)::text AS avg_cfm50,
                AVG(blower_ach50)::text AS avg_ach50
         FROM inspections
         WHERE blower_cfm50 IS NOT NULL`,
      ),
      queryOne<DuctRow>(
        `SELECT AVG(duct_cfm25_total)::text AS avg_cfm25_total
         FROM inspections
         WHERE duct_cfm25_total IS NOT NULL`,
      ),
    ]);

    // Build status distribution
    const byStatus: Record<string, number> = {};
    for (const r of statusRows) {
      byStatus[r.status] = parseInt(r.count, 10);
    }
    const totalInspections = Object.values(byStatus).reduce((a, b) => a + b, 0);

    const blowerTotal = parseInt(blowerRow?.total ?? "0", 10);
    const blowerFailed = parseInt(blowerRow?.failed ?? "0", 10);

    const completedCount = (byStatus["complete"] ?? 0) + (byStatus["submitted"] ?? 0);
    const RATE_PER_INSPECTION = 350;
    const thisMonthRevenue = completedCount * RATE_PER_INSPECTION;

    return NextResponse.json({
      data: {
        inspections_by_status: byStatus,
        total_inspections: totalInspections,
        avg_hers_index: hersRow?.avg_hers ? parseFloat(hersRow.avg_hers) : null,
        avg_hers_by_builder: hersByBuilder.map((r) => ({
          builder: r.builder,
          avg_hers: parseFloat(r.avg_hers),
          count: parseInt(r.count, 10),
        })),
        blower_door: {
          total_tests: blowerTotal,
          fail_rate: blowerTotal > 0 ? blowerFailed / blowerTotal : 0,
          avg_cfm50: blowerRow?.avg_cfm50 ? parseFloat(blowerRow.avg_cfm50) : null,
          avg_ach50: blowerRow?.avg_ach50 ? parseFloat(blowerRow.avg_ach50) : null,
        },
        duct_leakage: {
          avg_cfm25_total: ductRow?.avg_cfm25_total
            ? parseFloat(ductRow.avg_cfm25_total)
            : null,
        },
        revenue: {
          rate_per_inspection: RATE_PER_INSPECTION,
          completed_count: completedCount,
          estimated_this_month: thisMonthRevenue,
        },
      },
    });
  } catch (err) {
    console.error("GET /api/analytics/dashboard error:", err);
    return NextResponse.json({ error: "Database error" }, { status: 500 });
  }
}
