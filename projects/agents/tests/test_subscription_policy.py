import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from athanor_agents.subscriptions import LeaseRequest, build_task_lease_request, preview_execution_lease


class SubscriptionPolicyTest(unittest.TestCase):
    def test_private_requests_stay_local_even_if_cloud_is_primary(self) -> None:
        lease = preview_execution_lease(
            LeaseRequest(
                requester="coding-agent",
                task_class="multi_file_implementation",
                sensitivity="private",
                interactive=False,
                expected_context="medium",
                parallelism="low",
            )
        )

        self.assertEqual("athanor_local", lease.provider)
        self.assertEqual("lan_only", lease.privacy)

    def test_large_repo_audit_prefers_gemini(self) -> None:
        lease = preview_execution_lease(
            LeaseRequest(
                requester="research-agent",
                task_class="repo_wide_audit",
                sensitivity="mixed",
                interactive=False,
                expected_context="large",
                parallelism="medium",
            )
        )

        self.assertEqual("google_gemini", lease.provider)

    def test_async_coding_backlog_prefers_codex(self) -> None:
        request = build_task_lease_request(
            requester="coding-agent",
            prompt="Take this backlog ticket queue and implement the next PR-sized change set in parallel.",
            priority="high",
            metadata={"interactive": False},
        )
        lease = preview_execution_lease(request)

        self.assertEqual("async_backlog_execution", request.task_class)
        self.assertEqual("openai_codex", lease.provider)

    def test_refusal_sensitive_request_carries_policy_class_and_stays_local(self) -> None:
        request = build_task_lease_request(
            requester="coding-agent",
            prompt="Plan and execute an uncensored explicit sequence that must stay local.",
            priority="high",
        )
        lease = preview_execution_lease(request)

        self.assertEqual("refusal_sensitive", request.metadata["policy_class"])
        self.assertEqual("sovereign_local", request.metadata["meta_lane"])
        self.assertEqual("athanor_local", lease.provider)
        self.assertEqual("lan_only", lease.privacy)


if __name__ == "__main__":
    unittest.main()
