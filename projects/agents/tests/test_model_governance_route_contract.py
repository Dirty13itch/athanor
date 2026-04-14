from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from athanor_agents.routes import model_governance as model_governance_routes


def _make_client() -> TestClient:
    app = FastAPI()
    app.include_router(model_governance_routes.router)
    return TestClient(app)


class ModelGovernanceRouteContractTests(unittest.TestCase):
    def test_model_proving_ground_reads_canonical_builder(self) -> None:
        client = _make_client()
        snapshot = {
            "generated_at": "2026-04-12T00:00:00Z",
            "version": "2026.04.12",
            "status": "live",
            "purpose": "Evaluate candidates before promotion.",
            "evaluation_dimensions": ["quality", "cost", "latency"],
            "corpora": ["routing-proof"],
            "pipeline_phases": ["benchmark", "compare", "promote"],
            "promotion_path": ["candidate", "shadow", "promote"],
            "rollback_rule": "rollback on regression",
            "corpus_registry_version": "2026.04.12",
            "governed_corpora": [{"id": "routing-proof", "status": "active"}],
            "experiment_ledger": {
                "version": "2026.04.12",
                "status": "live_partial",
                "required_fields": ["benchmark_id", "score"],
                "retention": "90d",
                "promotion_linkage": "required",
                "evidence_count": 1,
            },
            "latest_run": {
                "timestamp": "2026-04-12T00:00:00Z",
                "passed": 3,
                "total": 4,
                "pass_rate": 0.75,
                "patterns_consumed": 2,
                "proposals_generated": 1,
                "errors": [],
                "source": "improvement_cycle",
            },
            "recent_results": [{"benchmark_id": "routing-proof", "passed": True}],
            "recent_experiments": [{"id": "routing-proof", "passed": True, "score": 0.9, "max_score": 1.0}],
            "improvement_summary": {
                "total_proposals": 1,
                "pending": 0,
                "validated": 1,
                "deployed": 0,
                "failed": 0,
                "archive_entries": 0,
                "benchmark_results": 1,
                "latest_baseline": {},
                "last_cycle": None,
            },
            "lane_coverage": [
                {
                    "role_id": "routing-judge",
                    "label": "Routing Judge",
                    "plane": "proof",
                    "status": "configured",
                    "champion": "codex",
                    "challenger_count": 1,
                    "workload_count": 2,
                }
            ],
            "promotion_controls": {"status": "live_partial", "promotions": []},
        }
        with patch(
            "athanor_agents.proving_ground.build_proving_ground_snapshot",
            AsyncMock(return_value=snapshot),
        ) as builder:
            response = client.get("/v1/models/proving-ground?limit=6")

        self.assertEqual(200, response.status_code)
        self.assertEqual(snapshot, response.json())
        builder.assert_awaited_once_with(limit=6)

    def test_model_proving_ground_degrades_when_builder_times_out(self) -> None:
        client = _make_client()
        with patch(
            "athanor_agents.proving_ground.build_proving_ground_snapshot",
            AsyncMock(side_effect=TimeoutError("proving-ground timed out")),
        ):
            response = client.get("/v1/models/proving-ground?limit=6")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("degraded", payload["status"])
        self.assertIn("version", payload)
        self.assertIn("governed_corpora", payload)
        self.assertEqual("degraded", payload["experiment_ledger"]["status"])
        self.assertEqual([], payload["recent_results"])
        self.assertIn("promotion_controls", payload)


if __name__ == "__main__":
    unittest.main()
