import { proxyOperatorReadJson } from "@/app/api/operator/fail-soft";

export async function GET() {
  return proxyOperatorReadJson("/v1/operator/governance", "Failed to fetch operator governance", {
    current_mode: {
      mode: "feed_unavailable",
    },
    launch_blockers: ["operator_upstream_unavailable"],
    launch_ready: false,
    attention_posture: {
      recommended_mode: "manual_review",
      breaches: ["Operator governance feed is temporarily unavailable from the dashboard runtime."],
    },
  });
}
