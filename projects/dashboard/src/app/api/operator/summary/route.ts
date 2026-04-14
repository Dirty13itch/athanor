import { proxyOperatorReadJson } from "@/app/api/operator/fail-soft";

export async function GET() {
  return proxyOperatorReadJson("/v1/operator/summary", "Failed to fetch operator work summary", {
    tasks: {
      pending_approval: 0,
      failed_actionable: 0,
      stale_lease: 0,
      failed_historical_repaired: 0,
    },
  }, 25_000);
}
