import { NextResponse } from "next/server";
import type { DashboardAnalytics, ApiResult } from "@/types";

// GET /api/analytics/dashboard — Aggregated analytics for the dashboard
export async function GET() {
  // TODO: Aggregate queries against PostgreSQL
  const analytics: DashboardAnalytics = {
    jobs_by_status: {
      draft: 0,
      submitted: 0,
      reported: 0,
      delivered: 0,
    },
    total_jobs: 0,
    avg_hers_index: null,
    avg_hers_by_builder: [],
    common_failures: {
      blower_door_fail_rate: 0,
      avg_cfm50: 0,
      avg_ach50: 0,
      avg_duct_leakage: 0,
    },
    revenue: {
      total: 0,
      this_month: 0,
      rate_per_job: 350, // Default rate
    },
  };

  return NextResponse.json(
    { data: analytics } satisfies ApiResult<DashboardAnalytics>
  );
}
