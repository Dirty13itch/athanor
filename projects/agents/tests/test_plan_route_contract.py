from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from athanor_agents.routes import plans as plan_routes
from athanor_agents.work_pipeline import CycleResult


def _make_client() -> TestClient:
    app = FastAPI()
    app.include_router(plan_routes.router)
    return TestClient(app)


class PlanRouteContractTests(unittest.TestCase):
    def test_pipeline_cycle_requires_operator_envelope(self) -> None:
        client = _make_client()
        with (
            patch("athanor_agents.routes.plans.emit_operator_audit_event", AsyncMock()) as audit,
            patch("athanor_agents.work_pipeline.run_pipeline_cycle", AsyncMock()) as run_cycle,
        ):
            response = client.post("/v1/pipeline/cycle", json={})

        self.assertEqual(400, response.status_code)
        run_cycle.assert_not_awaited()
        audit.assert_awaited_once()
        self.assertEqual("denied", audit.await_args.kwargs["decision"])

    def test_pipeline_cycle_handles_invalid_json_without_500(self) -> None:
        client = _make_client()
        with (
            patch("athanor_agents.routes.plans.emit_operator_audit_event", AsyncMock()) as audit,
            patch("athanor_agents.work_pipeline.run_pipeline_cycle", AsyncMock()) as run_cycle,
        ):
            response = client.post(
                "/v1/pipeline/cycle",
                content="{bad",
                headers={"Content-Type": "application/json"},
            )

        self.assertEqual(400, response.status_code)
        run_cycle.assert_not_awaited()
        audit.assert_awaited_once()
        self.assertEqual("denied", audit.await_args.kwargs["decision"])

    def test_pipeline_cycle_returns_cycle_result(self) -> None:
        client = _make_client()
        result = CycleResult(
            timestamp=123.0,
            intents_mined=10,
            intents_new=4,
            plans_created=3,
            tasks_submitted=2,
            tasks_held=1,
            errors=[],
        )
        with (
            patch("athanor_agents.routes.plans.emit_operator_audit_event", AsyncMock()) as audit,
            patch("athanor_agents.work_pipeline.run_pipeline_cycle", AsyncMock(return_value=result)) as run_cycle,
        ):
            response = client.post(
                "/v1/pipeline/cycle",
                json={
                    "actor": "operator",
                    "session_id": "sess-1",
                    "correlation_id": "corr-1",
                    "reason": "Trigger pipeline cycle",
                },
            )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(10, payload["cycle"]["intents_mined"])
        self.assertEqual(2, payload["cycle"]["tasks_submitted"])
        run_cycle.assert_awaited_once()
        audit.assert_awaited_once()
        self.assertEqual("accepted", audit.await_args.kwargs["decision"])


if __name__ == "__main__":
    unittest.main()
