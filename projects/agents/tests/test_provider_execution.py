import unittest
from unittest.mock import AsyncMock, patch

from athanor_agents.provider_execution import (
    HANDOFFS_KEY,
    build_provider_execution_snapshot,
    create_handoff_bundle,
    execute_provider_request,
    list_handoff_bundles,
    record_handoff_outcome,
)
from athanor_agents.proving_ground import (
    build_proving_ground_snapshot,
    run_proving_ground,
)
from athanor_agents.subscriptions import list_execution_leases


class FakeRedis:
    def __init__(self) -> None:
        self.hashes: dict[str, dict[str, str]] = {}
        self.lists: dict[str, list[str]] = {}

    async def hset(self, key: str, field: str, value: str) -> None:
        self.hashes.setdefault(key, {})[field] = value

    async def hgetall(self, key: str) -> dict[str, str]:
        return dict(self.hashes.get(key, {}))

    async def hget(self, key: str, field: str) -> str | None:
        return self.hashes.get(key, {}).get(field)

    async def lpush(self, key: str, value: str) -> None:
        self.lists.setdefault(key, []).insert(0, value)

    async def ltrim(self, key: str, start: int, end: int) -> None:
        values = self.lists.get(key, [])
        if not values:
            return
        self.lists[key] = values[start : end + 1]

    async def lrange(self, key: str, start: int, end: int) -> list[str]:
        values = self.lists.get(key, [])
        if end == -1:
            return values[start:]
        return values[start : end + 1]


class FakeImprovementEngine:
    def __init__(self) -> None:
        self.loaded = False
        self.benchmarks = type("Benchmarks", (), {"results": []})()

    async def load(self) -> None:
        self.loaded = True

    async def get_improvement_summary(self) -> dict:
        return {
            "total_proposals": 2,
            "pending": 1,
            "validated": 1,
            "deployed": 0,
            "failed": 0,
            "archive_entries": 0,
            "benchmark_results": len(self.benchmarks.results),
            "latest_baseline": {},
            "last_cycle": {
                "timestamp": "2026-03-12T07:00:00Z",
                "benchmarks": {"passed": 2, "total": 2, "pass_rate": 1.0},
                "patterns_consumed": 1,
                "proposals_generated": 1,
                "errors": [],
            },
        }

    async def run_benchmark_suite(self) -> dict:
        return {
            "timestamp": "2026-03-12T07:05:00Z",
            "passed": 2,
            "total": 2,
            "pass_rate": 1.0,
            "results": [],
            "comparison": {},
        }


class ProviderExecutionTests(unittest.IsolatedAsyncioTestCase):
    async def test_list_handoff_bundles_sorts_iso_and_unix_timestamps(self) -> None:
        fake_redis = FakeRedis()
        await fake_redis.hset(
            HANDOFFS_KEY,
            "older",
            '{"id":"older","requester":"coding-agent","created_at":1710000000}',
        )
        await fake_redis.hset(
            HANDOFFS_KEY,
            "newer",
            '{"id":"newer","requester":"coding-agent","created_at":"2026-03-24T16:32:47Z"}',
        )
        with patch("athanor_agents.provider_execution._get_redis", AsyncMock(return_value=fake_redis)):
            bundles = await list_handoff_bundles(limit=5, serialize=False)

        self.assertEqual(["newer", "older"], [bundle["id"] for bundle in bundles])

    async def test_meta_lane_requester_is_blocked_from_creating_handoff_bundle(self) -> None:
        fake_redis = FakeRedis()
        with (
            patch("athanor_agents.provider_execution._get_redis", AsyncMock(return_value=fake_redis)),
            patch("athanor_agents.subscriptions._get_redis", AsyncMock(return_value=fake_redis)),
        ):
            with self.assertRaises(PermissionError):
                await create_handoff_bundle(
                    requester="frontier_cloud",
                    prompt="Plan the next implementation batch.",
                    task_class="multi_file_implementation",
                )

    async def test_hybrid_handoff_bundle_uses_abstract_prompt_and_normalized_workload(self) -> None:
        fake_redis = FakeRedis()
        with (
            patch("athanor_agents.provider_execution._get_redis", AsyncMock(return_value=fake_redis)),
            patch("athanor_agents.subscriptions._get_redis", AsyncMock(return_value=fake_redis)),
            patch("athanor_agents.provider_execution._resolve_command", return_value=None),
        ):
            bundle = await create_handoff_bundle(
                requester="research-agent",
                prompt="Outline first, then review the repo structure without raw private details.",
                task_class="repo_wide_audit",
            )

        self.assertEqual("hybrid_abstractable", bundle["policy_class"])
        self.assertEqual("frontier_cloud", bundle["meta_lane"])
        self.assertEqual("abstracted", bundle["prompt_mode"])
        self.assertTrue(bundle["abstract_prompt"])
        self.assertEqual("repo_audit", bundle["plan_packet"]["workload_class"])
        self.assertTrue(any("routing posture" in note for note in bundle["notes"]))
        self.assertIsInstance(bundle["created_at"], str)

    async def test_provider_execution_snapshot_reports_all_configured_adapters(self) -> None:
        fake_redis = FakeRedis()
        with (
            patch("athanor_agents.provider_execution._get_redis", AsyncMock(return_value=fake_redis)),
            patch("athanor_agents.subscriptions._get_redis", AsyncMock(return_value=fake_redis)),
            patch("athanor_agents.provider_execution._resolve_command", return_value=None),
            patch(
                "athanor_agents.provider_execution.list_execution_leases",
                AsyncMock(return_value=[{"id": "lease-1", "provider": "athanor_local", "requester": "coding-agent"}]),
            ),
        ):
            snapshot = await build_provider_execution_snapshot(limit=5)

        providers = {entry["provider"] for entry in snapshot["adapters"]}
        self.assertIn("athanor_local", providers)
        self.assertIn("anthropic_claude_code", providers)
        self.assertIn("google_gemini", providers)
        local_entry = next(entry for entry in snapshot["adapters"] if entry["provider"] == "athanor_local")
        self.assertEqual("local_runtime", local_entry["execution_mode"])
        self.assertIn("provider_posture", snapshot)
        self.assertIn("provider_state_counts", snapshot)
        self.assertIn("catalog_version", snapshot)
        self.assertIn("catalog_source", snapshot)
        glm_posture = next(entry for entry in snapshot["provider_posture"] if entry["provider"] == "zai_glm_coding")
        self.assertEqual("governed_handoff_only", glm_posture["routing_posture"])
        self.assertIn("policy_governed_handoff_only", glm_posture["state_reasons"])
        self.assertGreaterEqual(
            snapshot["provider_state_counts"].get("handoff_only", 0)
            + snapshot["provider_state_counts"].get("degraded", 0),
            1,
        )

    async def test_bridge_execution_respects_catalog_allowed_execution_modes(self) -> None:
        fake_redis = FakeRedis()
        catalog = {
            "version": "test-catalog",
            "source_of_truth": "test-provider-catalog",
            "providers": [
                {
                    "id": "google_gemini",
                    "label": "Gemini CLI",
                    "access_mode": "cli",
                    "execution_modes": ["direct_cli", "handoff_bundle"],
                    "state_classes": ["active-routing"],
                    "cli_commands": ["gemini"],
                    "notes": ["Catalog keeps Gemini direct-or-handoff only."],
                }
            ],
        }
        with (
            patch("athanor_agents.provider_execution._get_redis", AsyncMock(return_value=fake_redis)),
            patch("athanor_agents.subscriptions._get_redis", AsyncMock(return_value=fake_redis)),
            patch("athanor_agents.provider_execution._resolve_command", return_value=None),
            patch("athanor_agents.provider_execution._bridge_enabled", return_value=True),
            patch("athanor_agents.provider_execution.get_provider_catalog_snapshot", return_value=catalog),
            patch(
                "athanor_agents.provider_execution._fetch_bridge_provider_snapshot",
                AsyncMock(
                    return_value={
                        "providers": {
                            "google_gemini": {
                                "provider": "google_gemini",
                                "adapter_available": True,
                                "probe_detail": "Bridge claimed Gemini was directly executable.",
                            }
                        },
                        "bridge_status": "available",
                        "detail": "Bridge ok.",
                        "bridge_url": "http://desk:9011",
                    }
                ),
            ),
            patch("athanor_agents.provider_execution.list_handoff_bundles", AsyncMock(return_value=[])),
            patch("athanor_agents.provider_execution.list_handoff_events", AsyncMock(return_value=[])),
            patch("athanor_agents.provider_execution.list_execution_leases", AsyncMock(return_value=[])),
        ):
            snapshot = await build_provider_execution_snapshot(limit=5)

        gemini = next(entry for entry in snapshot["adapters"] if entry["provider"] == "google_gemini")
        self.assertEqual("handoff_bundle", gemini["execution_mode"])
        self.assertFalse(gemini["adapter_available"])
        self.assertIn("handoff_bundle", gemini["catalog_execution_modes"])
        self.assertIn(
            "provider catalog keeps this lane handoff-only",
            " ".join(gemini["notes"]).lower(),
        )

    async def test_execute_provider_request_uses_bridge_when_bridge_reports_provider(self) -> None:
        fake_redis = FakeRedis()
        with (
            patch("athanor_agents.provider_execution._get_redis", AsyncMock(return_value=fake_redis)),
            patch("athanor_agents.subscriptions._get_redis", AsyncMock(return_value=fake_redis)),
            patch("athanor_agents.provider_execution._resolve_command", return_value=None),
            patch("athanor_agents.provider_execution._bridge_enabled", return_value=True),
            patch(
                "athanor_agents.provider_execution.get_provider_catalog_snapshot",
                return_value={
                    "version": "catalog-v1",
                    "source_of_truth": "provider-catalog.json",
                    "providers": [
                        {
                            "id": "anthropic_claude_code",
                            "access_mode": "cli",
                            "execution_modes": ["direct_cli", "bridge_cli", "handoff_bundle"],
                            "state_classes": ["active-routing"],
                            "cli_commands": ["claude"],
                            "notes": [],
                        },
                        {
                            "id": "openai_codex",
                            "access_mode": "cli",
                            "execution_modes": ["direct_cli", "bridge_cli", "handoff_bundle"],
                            "state_classes": ["active-routing"],
                            "cli_commands": ["codex"],
                            "notes": [],
                        },
                    ],
                },
            ),
            patch(
                "athanor_agents.provider_execution._fetch_bridge_provider_snapshot",
                AsyncMock(
                    return_value={
                        "providers": {
                            "openai_codex": {
                                "provider": "openai_codex",
                                "adapter_available": True,
                                "probe_detail": "Bridge probe ok.",
                            },
                            "anthropic_claude_code": {
                                "provider": "anthropic_claude_code",
                                "adapter_available": True,
                                "probe_detail": "Bridge probe ok.",
                            }
                        },
                        "bridge_status": "available",
                        "detail": "Bridge ok.",
                        "bridge_url": "http://desk:9011",
                    }
                ),
            ),
            patch(
                "athanor_agents.provider_execution._execute_via_bridge",
                AsyncMock(
                    return_value={
                        "ok": True,
                        "duration_ms": 321,
                        "summary": "Bridge execution completed.",
                        "stdout": "\n".join(
                            [
                                "Review the next safe implementation batch.",
                                "TurnBegin(user_input='Review the next safe implementation batch.')",
                                "TextPart(type='text', text='BRIDGE_DONE')",
                                "StatusUpdate(message_id='msg-1')",
                            ]
                        ),
                        "stderr": "",
                    }
                ),
            ),
        ):
            result = await execute_provider_request(
                requester="coding-agent",
                prompt="Review the next safe implementation batch.",
                task_class="multi_file_implementation",
            )

        self.assertEqual("completed", result["status"])
        self.assertEqual("bridge_cli", result["adapter"]["execution_mode"])
        self.assertEqual("completed", result["handoff"]["status"])
        self.assertEqual("BRIDGE_DONE", result["handoff"]["result_summary"])
        self.assertEqual(1, len(result["handoff"]["execution_attempts"]))
        self.assertEqual("BRIDGE_DONE", result["handoff"]["last_execution"]["summary"])
        self.assertTrue(
            any(ref["label"] == "activity" for ref in result["handoff"]["artifact_refs"])
        )
        self.assertTrue(
            any(ref["label"] == "history" for ref in result["handoff"]["artifact_refs"])
        )

    async def test_provider_execution_snapshot_reports_direct_and_handoff_counts(self) -> None:
        fake_redis = FakeRedis()
        with (
            patch("athanor_agents.provider_execution._get_redis", AsyncMock(return_value=fake_redis)),
            patch("athanor_agents.subscriptions._get_redis", AsyncMock(return_value=fake_redis)),
            patch("athanor_agents.provider_execution._resolve_command", return_value=None),
            patch(
                "athanor_agents.provider_execution.list_handoff_bundles",
                AsyncMock(
                    return_value=[
                        {"id": "handoff-1", "execution_mode": "bridge_cli", "status": "completed"},
                        {"id": "handoff-2", "execution_mode": "handoff_bundle", "status": "pending"},
                    ]
                ),
            ),
            patch("athanor_agents.provider_execution.list_handoff_events", AsyncMock(return_value=[])),
            patch("athanor_agents.provider_execution.list_execution_leases", AsyncMock(return_value=[])),
        ):
            snapshot = await build_provider_execution_snapshot(limit=5)

        self.assertEqual(2, snapshot["total_handoffs"])
        self.assertEqual(1, snapshot["direct_execution_count"])
        self.assertEqual(1, snapshot["handoff_only_count"])

    async def test_execute_provider_request_falls_back_to_handoff_after_direct_failure(self) -> None:
        fake_redis = FakeRedis()
        with (
            patch("athanor_agents.provider_execution._get_redis", AsyncMock(return_value=fake_redis)),
            patch("athanor_agents.subscriptions._get_redis", AsyncMock(return_value=fake_redis)),
            patch("athanor_agents.provider_execution._resolve_command", return_value="claude"),
            patch(
                "athanor_agents.provider_execution._probe_command",
                return_value={
                    "ok": True,
                    "status": "available",
                    "detail": "Probe ok.",
                    "checked_at": 1.0,
                },
            ),
            patch(
                "athanor_agents.provider_execution._run_direct_cli",
                AsyncMock(
                    return_value={
                        "ok": False,
                        "duration_ms": 222,
                        "summary": "Direct execution failed.",
                        "stderr": "simulated failure",
                    }
                ),
            ),
        ):
            result = await execute_provider_request(
                requester="coding-agent",
                prompt="Implement the next multi-file batch.",
                task_class="multi_file_implementation",
            )

        self.assertEqual("fallback_to_handoff", result["status"])
        self.assertEqual("direct_cli", result["adapter"]["execution_mode"])
        self.assertEqual("handoff_bundle", result["handoff"]["execution_mode"])
        self.assertEqual("direct_cli", result["handoff"]["fallback_from_execution_mode"])
        self.assertIn("simulated failure", result["handoff"]["fallback_reason"])
        self.assertIn("downgraded to handoff mode", " ".join(result["handoff"]["notes"]))

    async def test_record_handoff_outcome_serializes_timestamps_and_updates_linked_lease(self) -> None:
        fake_redis = FakeRedis()
        with (
            patch("athanor_agents.provider_execution._get_redis", AsyncMock(return_value=fake_redis)),
            patch("athanor_agents.subscriptions._get_redis", AsyncMock(return_value=fake_redis)),
            patch("athanor_agents.provider_execution._resolve_command", return_value=None),
        ):
            bundle = await create_handoff_bundle(
                requester="coding-agent",
                prompt="Review the next implementation batch.",
                task_class="multi_file_implementation",
                serialize=False,
            )
            updated = await record_handoff_outcome(
                handoff_id=str(bundle["id"]),
                outcome="completed",
                result_summary="Provider execution completed.",
                execution_details={
                    "ok": True,
                    "summary": "Provider execution completed.",
                    "duration_ms": 123,
                },
            )
            leases = await list_execution_leases(limit=5)

        self.assertEqual("completed", updated["status"])
        self.assertIsInstance(updated["completed_at"], str)
        self.assertEqual("Provider execution completed.", updated["last_execution"]["summary"])
        self.assertEqual("completed", leases[0]["outcome"])


class ProvingGroundTests(unittest.IsolatedAsyncioTestCase):
    async def test_proving_ground_snapshot_bridges_registry_and_runtime_summary(self) -> None:
        engine = FakeImprovementEngine()
        with (
            patch(
                "athanor_agents.proving_ground.get_model_proving_ground",
                return_value={
                    "version": "2026-03-12",
                    "status": "implemented_not_live",
                    "purpose": "Test proving ground",
                    "evaluation_dimensions": ["functional_quality"],
                    "corpora": [{"id": "golden_tasks"}],
                    "pipeline_phases": ["benchmark", "canary"],
                    "promotion_path": ["offline_eval", "operator_review"],
                    "rollback_rule": "keep old champion",
                },
            ),
            patch(
                "athanor_agents.proving_ground.get_model_role_registry",
                return_value={
                    "roles": [
                        {
                            "id": "frontier_supervisor",
                            "label": "Frontier supervisor",
                            "plane": "frontier_cloud",
                            "status": "live",
                            "champion": "Claude",
                            "challengers": ["Gemini"],
                            "workload_classes": ["architecture_planning"],
                        }
                    ]
                },
            ),
            patch("athanor_agents.proving_ground.get_improvement_engine", return_value=engine),
        ):
            snapshot = await build_proving_ground_snapshot()

        self.assertEqual("implemented_not_live", snapshot["status"])
        self.assertEqual("Test proving ground", snapshot["purpose"])
        self.assertEqual(1, len(snapshot["lane_coverage"]))
        self.assertEqual("frontier_supervisor", snapshot["lane_coverage"][0]["role_id"])
        self.assertEqual(1, snapshot["improvement_summary"]["pending"])
        self.assertIn("promotion_controls", snapshot)

    async def test_run_proving_ground_marks_snapshot_live_and_includes_benchmark_summary(self) -> None:
        engine = FakeImprovementEngine()
        with (
            patch(
                "athanor_agents.proving_ground.get_model_proving_ground",
                return_value={
                    "version": "2026-03-12",
                    "status": "implemented_not_live",
                    "purpose": "Test proving ground",
                    "evaluation_dimensions": ["functional_quality"],
                    "corpora": [],
                    "pipeline_phases": ["benchmark"],
                    "promotion_path": ["offline_eval"],
                    "rollback_rule": "keep old champion",
                },
            ),
            patch("athanor_agents.proving_ground.get_model_role_registry", return_value={"roles": []}),
            patch("athanor_agents.proving_ground.get_improvement_engine", return_value=engine),
        ):
            snapshot = await run_proving_ground()

        self.assertEqual("live", snapshot["status"])
        self.assertEqual(2, snapshot["latest_benchmark_run"]["passed"])
        self.assertEqual(2, snapshot["latest_benchmark_run"]["total"])


if __name__ == "__main__":
    unittest.main()
