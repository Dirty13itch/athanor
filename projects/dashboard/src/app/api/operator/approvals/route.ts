import { NextRequest, NextResponse } from "next/server";
import { loadExecutionReviewFeed } from "@/lib/executive-kernel";

export async function GET(request: NextRequest) {
  const params = new URLSearchParams(request.nextUrl.searchParams);
  const feed = await loadExecutionReviewFeed({
    status: params.get("status"),
    family: params.get("family"),
    limit: 500,
  });
  const approvals = feed.reviews.map((review) => ({
    id: review.id,
    related_run_id: review.related_run_id,
    related_task_id: review.related_task_id,
    requested_action: review.requested_action,
    privilege_class: review.privilege_class,
    reason: review.reason,
    status: review.status,
    requested_at: review.requested_at,
    decided_at: 0,
    decided_by: "",
    task_prompt: review.task_prompt,
    task_agent_id: review.task_agent_id,
    task_priority: review.task_priority,
    task_status: review.task_status,
    task_created_at: 0,
    metadata: review.metadata ?? {},
  }));

  return NextResponse.json({
    available: feed.available,
    degraded: feed.degraded,
    source: feed.source,
    detail: feed.detail,
    approvals,
    count: approvals.length,
  });
}
