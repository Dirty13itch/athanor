import sys
import types
import unittest
from unittest.mock import AsyncMock, patch

from athanor_agents.plan_generator import ExecutionPlan, decompose_plan_to_tasks, generate_plan_from_intent
from athanor_agents import plan_generator


ACTIVE_PHASE_ID = "software_core_phase_1"
ACTIVE_ENABLED_AGENTS = [
    "coding-agent",
    "research-agent",
    "knowledge-agent",
    "general-assistant",
]


class PlanGeneratorAutonomyScopeTests(unittest.IsolatedAsyncioTestCase):
    async def test_manual_plans_keep_full_roster_suggestions(self) -> None:
        with (
            patch("athanor_agents.plan_generator._store_plan", AsyncMock()),
            patch("athanor_agents.plan_generator._enhance_plan_with_llm", AsyncMock(return_value=None)),
        ):
            plan = await generate_plan_from_intent(
                intent_source="operator",
                intent_text="Generate a media report and creative image refresh for Plex.",
                metadata={},
            )

        self.assertIn("media-agent", plan.assigned_agents)
        self.assertIn("creative-agent", plan.assigned_agents)
        self.assertFalse(plan.autonomy_managed)
        self.assertIsNone(plan.autonomy_phase_id)
        self.assertIsNone(plan.autonomy_scope_note)

    async def test_autonomy_managed_plans_filter_blocked_agents(self) -> None:
        with (
            patch("athanor_agents.plan_generator._store_plan", AsyncMock()),
            patch("athanor_agents.plan_generator._enhance_plan_with_llm", AsyncMock(return_value=None)),
            patch(
                "athanor_agents.plan_generator._load_active_autonomy_phase_scope",
                return_value=(ACTIVE_PHASE_ID, ACTIVE_ENABLED_AGENTS),
            ),
        ):
            plan = await generate_plan_from_intent(
                intent_source="status_md",
                intent_text="Generate a creative media image refresh for Plex.",
                metadata={"_autonomy_managed": True, "_autonomy_source": "pipeline"},
            )

        self.assertEqual(["general-assistant"], plan.assigned_agents)
        self.assertTrue(plan.autonomy_managed)
        self.assertEqual(ACTIVE_PHASE_ID, plan.autonomy_phase_id)
        self.assertIn("Filtered blocked agents", plan.autonomy_scope_note or "")


class _FakePlanEnhancementResponse:
    def __init__(self, *, status_code: int, payload: dict | None = None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self) -> dict:
        return self._payload


class _FakePlanEnhancementClient:
    def __init__(self, response: _FakePlanEnhancementResponse):
        self.response = response
        self.calls: list[dict] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url: str, *, json: dict, headers: dict | None = None):
        self.calls.append({"url": url, "json": json, "headers": headers or {}})
        return self.response


class PlanEnhancementAuthTests(unittest.IsolatedAsyncioTestCase):
    async def test_plan_enhancement_uses_litellm_bearer_token(self) -> None:
        plan = ExecutionPlan(
            id="plan-auth",
            intent_source="status_md",
            intent_text="Create a short execution plan.",
            title="Auth coverage",
            research_summary="",
            approach="",
            estimated_tasks=1,
            assigned_agents=["general-assistant"],
            status="draft",
        )
        client = _FakePlanEnhancementClient(
            _FakePlanEnhancementResponse(
                status_code=200,
                payload={
                    "choices": [
                        {
                            "message": {
                                "content": '{"research_summary":"ok","approach":"ok","estimated_tasks":1,"risk_level":"low"}'
                            }
                        }
                    ]
                },
            )
        )

        fake_config = types.ModuleType("athanor_agents.config")
        fake_config.settings = types.SimpleNamespace(
            litellm_url="http://litellm.local",
            litellm_api_key="secret-token",
        )
        with (
            patch.dict(sys.modules, {"athanor_agents.config": fake_config}),
            patch("httpx.AsyncClient", return_value=client),
        ):
                enhanced = await plan_generator._enhance_plan_with_llm(plan)

        self.assertIsNotNone(enhanced)
        self.assertEqual(
            {"Authorization": "Bearer secret-token"},
            client.calls[0]["headers"],
        )

    async def test_decompose_plan_rechecks_autonomy_scope(self) -> None:
        mock_redis = AsyncMock()
        plan = ExecutionPlan(
            id="plan-1",
            intent_source="status_md",
            intent_text="Generate a creative media image refresh for Plex.",
            title="Creative media refresh",
            research_summary="Drafted from status intent.",
            approach="Execute via media-agent with 1 task",
            estimated_tasks=1,
            assigned_agents=["media-agent"],
            status="approved",
            autonomy_managed=True,
        )

        with (
            patch("athanor_agents.plan_generator._get_redis", AsyncMock(return_value=mock_redis)),
            patch(
                "athanor_agents.plan_generator._load_active_autonomy_phase_scope",
                return_value=(ACTIVE_PHASE_ID, ACTIVE_ENABLED_AGENTS),
            ),
        ):
            tasks = await decompose_plan_to_tasks(plan)

        self.assertEqual(["general-assistant"], [task["agent"] for task in tasks])
        self.assertEqual(ACTIVE_PHASE_ID, plan.autonomy_phase_id)
        self.assertIn("Filtered blocked agents", plan.autonomy_scope_note or "")
