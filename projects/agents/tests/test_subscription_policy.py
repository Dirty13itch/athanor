import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from athanor_agents.subscriptions import (
    LeaseRequest,
    build_task_lease_request,
    get_provider_catalog_snapshot,
    load_policy,
    preview_execution_lease,
)


class SubscriptionPolicyTest(unittest.TestCase):
    def test_load_policy_requires_canonical_yaml_policy_file(self) -> None:
        policy = load_policy()
        self.assertEqual(
            str(Path(__file__).resolve().parents[1] / "config" / "subscription-routing-policy.yaml"),
            policy["_policy_source"],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            missing_policy_path = Path(tmpdir) / "subscription-routing-policy.yaml"
            with patch("athanor_agents.subscriptions._policy_path", return_value=missing_policy_path):
                with self.assertRaises(FileNotFoundError) as error:
                    load_policy()

        self.assertIn(str(missing_policy_path), str(error.exception))

    def test_provider_catalog_snapshot_enriches_provider_truth(self) -> None:
        catalog = {
            "version": "test-version",
            "official_verified_at": "2026-03-25",
            "source_of_truth": "test-catalog",
            "providers": [
                {
                    "id": "deepseek_api",
                    "label": "DeepSeek API",
                    "category": "api",
                    "access_mode": "api",
                    "execution_modes": ["litellm_proxy"],
                    "state_classes": ["active-api", "configured-unused"],
                    "subscription_product": "DeepSeek API",
                    "monthly_cost_usd": None,
                    "official_pricing_status": "metered",
                    "observed_hosts": ["vault"],
                    "env_contracts": ["DEEPSEEK_API_KEY"],
                    "observed_runtime": {
                        "routing_policy_enabled": False,
                        "active_burn_observed": False,
                        "api_configured": True,
                        "proxy_activity_observed": True,
                        "provider_specific_usage_observed": False,
                    },
                    "evidence": {
                        "kind": "vault_litellm_proxy",
                        "proxy": {
                            "alias": "deepseek",
                            "preferred_models": ["deepseek", "deepseek-chat", "deepseek-reasoner"],
                            "served_model_match_tokens": ["deepseek"],
                            "host": "vault",
                            "last_verified_at": "2026-03-28T06:00:00Z",
                            "source": "scripts/collect_truth_inventory.py",
                        },
                        "provider_specific_usage": {
                            "status": "pending",
                            "last_verified_at": None,
                            "source": "pending_capture",
                            "proof_kind": "litellm_alias_request",
                        },
                    },
                },
                {
                    "id": "moonshot_kimi",
                    "label": "Kimi Code",
                    "category": "subscription",
                    "access_mode": "cli",
                    "execution_modes": ["direct_cli"],
                    "state_classes": ["active-routing", "active-burn"],
                    "subscription_product": "Kimi Membership / Kimi Code",
                    "monthly_cost_usd": None,
                    "official_pricing_status": "official-source-present-cost-unverified",
                    "observed_hosts": ["desk", "dev"],
                    "env_contracts": ["MOONSHOT_API_KEY"],
                    "observed_runtime": {
                        "routing_policy_enabled": True,
                        "active_burn_observed": True,
                        "api_configured": True,
                    },
                    "evidence": {
                        "kind": "cli_subscription",
                        "cli_probe": {
                            "status": "installed",
                            "expected_hosts": ["desk", "dev"],
                            "required_commands": ["kimi"],
                            "last_verified_at": "2026-03-25T19:15:00Z",
                            "source": "config/automation-backbone/tooling-inventory.json",
                        },
                        "billing": {
                            "status": "operator_visible_tier_unverified",
                            "subscribed_tier": None,
                            "verified_monthly_cost_usd": None,
                            "last_verified_at": "2026-03-28",
                            "source": "official_docs_only",
                        },
                    },
                },
                {
                    "id": "zai_glm_coding",
                    "label": "Z.ai GLM Coding",
                    "category": "subscription",
                    "access_mode": "cli",
                    "execution_modes": ["direct_cli", "handoff_bundle"],
                    "state_classes": ["active-routing", "configured-unused"],
                    "subscription_product": "GLM Coding Plan",
                    "monthly_cost_usd": None,
                    "official_pricing_status": "official-source-present-cost-unverified",
                    "observed_hosts": [],
                    "env_contracts": ["ZAI_API_KEY"],
                    "observed_runtime": {
                        "routing_policy_enabled": True,
                        "active_burn_observed": False,
                        "api_configured": True,
                    },
                    "evidence": {
                        "kind": "cli_subscription",
                        "cli_probe": {
                            "status": "missing",
                            "expected_hosts": ["desk", "dev"],
                            "required_commands": ["glm", "zai"],
                            "last_verified_at": "2026-03-25T19:15:00Z",
                            "source": "config/automation-backbone/tooling-inventory.json",
                        },
                        "billing": {
                            "status": "published_tiers_known_subscribed_tier_unverified",
                            "subscribed_tier": None,
                            "verified_monthly_cost_usd": None,
                            "last_verified_at": "2026-03-28",
                            "source": "official_docs",
                        },
                    },
                },
            ],
        }
        tooling = {
            "hosts": [
                {
                    "id": "desk",
                    "tools": [
                        {
                            "provider_id": "zai_glm_coding",
                            "tool_id": "glm",
                            "status": "missing",
                            "version": None,
                        }
                    ],
                }
            ]
        }
        credential_surfaces = {
            "surfaces": [
                {"env_var_names": ["DEEPSEEK_API_KEY", "MOONSHOT_API_KEY", "ZAI_API_KEY"]}
            ]
        }

        with (
            patch("athanor_agents.subscriptions.get_provider_catalog_registry", return_value=catalog),
            patch("athanor_agents.subscriptions.get_tooling_inventory_registry", return_value=tooling),
            patch(
                "athanor_agents.subscriptions.get_credential_surface_registry",
                return_value=credential_surfaces,
            ),
            patch(
                "athanor_agents.subscriptions.get_provider_usage_evidence_artifact",
                return_value={"captures": []},
            ),
        ):
            snapshot = get_provider_catalog_snapshot()

        providers = {entry["id"]: entry for entry in snapshot["providers"]}
        self.assertEqual(
            "vault_proxy_active_no_provider_specific_evidence",
            providers["deepseek_api"]["evidence_posture"],
        )
        self.assertEqual("vault_litellm_proxy", providers["deepseek_api"]["evidence"]["kind"])
        self.assertEqual("metered_api", providers["deepseek_api"]["pricing_truth_label"])
        self.assertEqual("live_burn_observed_cost_unverified", providers["moonshot_kimi"]["evidence_posture"])
        self.assertEqual("operator_visible_tier_unverified", providers["moonshot_kimi"]["evidence"]["billing"]["status"])
        self.assertEqual("flat_rate_unverified", providers["moonshot_kimi"]["pricing_truth_label"])
        self.assertEqual("routing_enabled_without_observed_tool", providers["zai_glm_coding"]["evidence_posture"])
        self.assertEqual("missing", providers["zai_glm_coding"]["evidence"]["cli_probe"]["status"])
        self.assertEqual("flat_rate_unverified", providers["zai_glm_coding"]["pricing_truth_label"])

    def test_provider_catalog_snapshot_uses_provider_usage_capture_status(self) -> None:
        catalog = {
            "version": "test-version",
            "official_verified_at": "2026-03-29",
            "source_of_truth": "test-catalog",
            "providers": [
                {
                    "id": "openai_api",
                    "label": "OpenAI API",
                    "category": "api",
                    "access_mode": "api",
                    "execution_modes": ["litellm_proxy"],
                    "state_classes": ["active-api", "configured-unused"],
                    "subscription_product": "OpenAI API",
                    "monthly_cost_usd": None,
                    "official_pricing_status": "metered",
                    "observed_hosts": ["vault"],
                    "env_contracts": ["OPENAI_API_KEY"],
                    "observed_runtime": {
                        "routing_policy_enabled": False,
                        "active_burn_observed": False,
                        "api_configured": True,
                        "proxy_activity_observed": True,
                        "provider_specific_usage_observed": False,
                    },
                    "evidence": {
                        "kind": "vault_litellm_proxy",
                        "proxy": {
                            "alias": "gpt",
                            "preferred_models": ["gpt", "gpt-5-mini"],
                            "served_model_match_tokens": ["gpt", "o4"],
                            "host": "vault",
                            "last_verified_at": "2026-03-29T03:42:59Z",
                            "source": "scripts/collect_truth_inventory.py",
                        },
                        "provider_specific_usage": {
                            "status": "pending",
                            "last_verified_at": None,
                            "source": "pending_capture",
                            "proof_kind": "litellm_model_completion",
                        },
                    },
                }
            ],
        }
        with (
            patch("athanor_agents.subscriptions.get_provider_catalog_registry", return_value=catalog),
            patch("athanor_agents.subscriptions.get_tooling_inventory_registry", return_value={"hosts": []}),
            patch("athanor_agents.subscriptions.get_credential_surface_registry", return_value={"surfaces": []}),
            patch(
                "athanor_agents.subscriptions.get_provider_usage_evidence_artifact",
                return_value={
                    "captures": [
                        {
                            "provider_id": "openai_api",
                            "status": "auth_failed",
                            "alias": "gpt",
                            "requested_model": "gpt-5-mini",
                            "response_model": None,
                            "matched_by": "preferred_exact",
                            "http_status": 500,
                            "error_snippet": "OPENAI_API_KEY missing",
                            "proof_kind": "litellm_model_completion",
                            "observed_at": "2026-03-29T03:42:59Z",
                            "source": "vault-litellm-live-probe",
                            "request_surface": "POST http://vault/v1/chat/completions",
                        }
                    ]
                },
            ),
        ):
            snapshot = get_provider_catalog_snapshot()

        provider = snapshot["providers"][0]
        self.assertEqual("vault_provider_specific_auth_failed", provider["evidence_posture"])
        self.assertEqual("auth_failed", provider["provider_usage_capture"]["status"])

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

    def test_private_agent_defaults_use_canonical_private_automation_class(self) -> None:
        policy = load_policy()

        self.assertIn("private_automation", policy["task_classes"])
        self.assertNotIn("private_internal_automation", policy["task_classes"])

        for agent_id in (
            "general-assistant",
            "knowledge-agent",
            "home-agent",
            "media-agent",
            "stash-agent",
            "data-curator",
        ):
            self.assertEqual("private_automation", policy["agents"][agent_id]["default_task_class"])

        request = build_task_lease_request(
            requester="general-assistant",
            prompt="Refresh internal home context and summarize changes.",
            metadata={"interactive": False},
        )
        lease = preview_execution_lease(request)

        self.assertEqual("private_automation", request.task_class)
        self.assertEqual("athanor_local", lease.provider)

    def test_knowledge_agent_background_work_keeps_private_local_execution_hints(self) -> None:
        request = build_task_lease_request(
            requester="knowledge-agent",
            prompt="Review the indexed knowledge gaps and summarize them.",
            metadata={"interactive": False},
        )
        lease = preview_execution_lease(request)

        self.assertEqual("private_automation", request.task_class)
        self.assertEqual("private", request.sensitivity)
        self.assertEqual("small", request.expected_context)
        self.assertEqual("athanor_local", lease.provider)

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

    def test_async_coding_backlog_prefers_glm_bulk_lane(self) -> None:
        request = build_task_lease_request(
            requester="coding-agent",
            prompt="Take this backlog ticket queue and implement the next PR-sized change set in parallel.",
            priority="high",
            metadata={"interactive": False},
        )
        lease = preview_execution_lease(request)

        self.assertEqual("async_backlog_execution", request.task_class)
        self.assertEqual("zai_glm_coding", lease.provider)

    def test_bulk_transform_prefers_glm_when_observed_lane_is_ready(self) -> None:
        lease = preview_execution_lease(
            LeaseRequest(
                requester="coding-agent",
                task_class="cheap_bulk_transform",
                sensitivity="repo_internal",
                interactive=False,
                expected_context="medium",
                parallelism="medium",
            )
        )

        self.assertEqual("zai_glm_coding", lease.provider)
        self.assertEqual("live_burn_observed_cost_unverified", lease.metadata["provider_evidence_posture"])
        self.assertEqual("ordinary_auto", lease.metadata["provider_routing_posture"])

    def test_multi_file_fallback_keeps_glm_when_ordinary_auto(self) -> None:
        lease = preview_execution_lease(
            LeaseRequest(
                requester="coding-agent",
                task_class="multi_file_implementation",
                sensitivity="repo_internal",
                interactive=False,
                expected_context="medium",
                parallelism="low",
            )
        )

        self.assertEqual("openai_codex", lease.provider)
        self.assertIn("zai_glm_coding", lease.fallback)

    def test_allow_handoff_only_keeps_glm_in_fallback_pool(self) -> None:
        policy = {
            "version": 1,
            "providers": {
                "zai_glm_coding": {
                    "enabled": True,
                    "category": "subscription",
                    "routing_posture": "governed_handoff_only",
                    "routing_reason": "missing_cli_evidence",
                    "role": "standby_bulk_overflow",
                    "privacy": "cloud",
                    "reserve": "burn_for_bulk",
                },
                "google_gemini": {
                    "enabled": True,
                    "category": "subscription",
                    "routing_posture": "ordinary_auto",
                    "routing_reason": "verified_cli_or_recent_burn",
                    "role": "large_context_auditor",
                    "privacy": "cloud",
                    "reserve": "burn_early",
                },
            },
            "task_classes": {
                "cheap_bulk_transform": {
                    "primary": ["zai_glm_coding"],
                    "fallback": ["google_gemini"],
                }
            },
            "agents": {
                "coding-agent": {
                    "allowed_providers": ["zai_glm_coding", "google_gemini"],
                }
            },
        }
        catalog = {
            "providers": [
                {
                    "id": "zai_glm_coding",
                    "access_mode": "cli",
                    "execution_modes": ["direct_cli", "handoff_bundle"],
                    "env_contracts": ["ZAI_API_KEY"],
                    "observed_runtime": {
                        "routing_policy_enabled": True,
                        "active_burn_observed": False,
                        "api_configured": True,
                    },
                    "evidence": {
                        "kind": "cli_subscription",
                        "cli_probe": {
                            "status": "missing",
                            "expected_hosts": ["desk", "dev"],
                            "required_commands": ["glm", "zai"],
                            "last_verified_at": "2026-03-25T19:15:00Z",
                            "source": "config/automation-backbone/tooling-inventory.json",
                        },
                        "billing": {
                            "status": "published_tiers_known_subscribed_tier_unverified",
                            "subscribed_tier": None,
                            "verified_monthly_cost_usd": None,
                            "last_verified_at": "2026-03-28",
                            "source": "official_docs",
                        },
                    },
                },
                {
                    "id": "google_gemini",
                    "access_mode": "cli",
                    "execution_modes": ["direct_cli", "handoff_bundle"],
                    "env_contracts": ["GEMINI_API_KEY"],
                    "observed_runtime": {
                        "routing_policy_enabled": True,
                        "active_burn_observed": True,
                        "api_configured": True,
                    },
                    "evidence": {
                        "kind": "cli_subscription",
                        "cli_probe": {
                            "status": "installed",
                            "expected_hosts": ["desk"],
                            "required_commands": ["gemini"],
                            "last_verified_at": "2026-03-25T19:15:00Z",
                            "source": "config/automation-backbone/tooling-inventory.json",
                        },
                        "billing": {
                            "status": "verified",
                            "subscribed_tier": "Google AI Pro",
                            "verified_monthly_cost_usd": 20,
                            "last_verified_at": "2026-03-28",
                            "source": "official_docs",
                        },
                    },
                },
            ]
        }
        tooling = {
            "hosts": [
                {
                    "id": "desk",
                    "tools": [
                        {"provider_id": "zai_glm_coding", "tool_id": "glm", "status": "missing"},
                        {"provider_id": "google_gemini", "tool_id": "gemini", "status": "installed"},
                    ],
                }
            ]
        }
        credential_surfaces = {"surfaces": [{"env_var_names": ["ZAI_API_KEY", "GEMINI_API_KEY"]}]}

        with (
            patch("athanor_agents.subscriptions.load_policy", return_value=policy),
            patch("athanor_agents.subscriptions.get_provider_catalog_registry", return_value=catalog),
            patch("athanor_agents.subscriptions.get_tooling_inventory_registry", return_value=tooling),
            patch(
                "athanor_agents.subscriptions.get_credential_surface_registry",
                return_value=credential_surfaces,
            ),
        ):
            lease = preview_execution_lease(
                LeaseRequest(
                    requester="coding-agent",
                    task_class="cheap_bulk_transform",
                    sensitivity="repo_internal",
                    interactive=False,
                    expected_context="medium",
                    parallelism="medium",
                    metadata={"allow_handoff_only": True},
                )
            )

        self.assertEqual("google_gemini", lease.provider)
        self.assertIn("zai_glm_coding", lease.fallback)
        self.assertEqual([], lease.metadata["excluded_handoff_only_providers"])
        self.assertEqual("ordinary_auto", lease.metadata["provider_routing_posture"])

    def test_policy_declared_handoff_only_excludes_provider_even_if_cli_is_installed(self) -> None:
        policy = {
            "version": 1,
            "providers": {
                "zai_glm_coding": {
                    "enabled": True,
                    "category": "subscription",
                    "routing_posture": "governed_handoff_only",
                    "routing_reason": "operator_parked",
                    "role": "standby_bulk_overflow",
                    "privacy": "cloud",
                    "reserve": "burn_for_bulk",
                },
                "google_gemini": {
                    "enabled": True,
                    "category": "subscription",
                    "routing_posture": "ordinary_auto",
                    "routing_reason": "verified_cli_or_recent_burn",
                    "role": "large_context_auditor",
                    "privacy": "cloud",
                    "reserve": "burn_early",
                },
            },
            "task_classes": {
                "cheap_bulk_transform": {
                    "primary": ["zai_glm_coding"],
                    "fallback": ["google_gemini"],
                }
            },
            "agents": {
                "coding-agent": {
                    "allowed_providers": ["zai_glm_coding", "google_gemini"],
                }
            },
        }
        catalog = {
            "providers": [
                {
                    "id": "zai_glm_coding",
                    "access_mode": "cli",
                    "execution_modes": ["direct_cli", "handoff_bundle"],
                    "state_classes": ["configured-unused"],
                    "env_contracts": ["ZAI_API_KEY"],
                    "observed_runtime": {
                        "routing_policy_enabled": False,
                        "active_burn_observed": False,
                        "api_configured": True,
                    },
                    "evidence": {
                        "kind": "cli_subscription",
                        "cli_probe": {
                            "status": "installed",
                            "expected_hosts": ["desk"],
                            "required_commands": ["glm"],
                            "last_verified_at": "2026-03-25T19:15:00Z",
                            "source": "config/automation-backbone/tooling-inventory.json",
                        },
                        "billing": {
                            "status": "published_tiers_known_subscribed_tier_unverified",
                            "subscribed_tier": None,
                            "verified_monthly_cost_usd": None,
                            "last_verified_at": "2026-03-28",
                            "source": "official_docs",
                        },
                    },
                },
                {
                    "id": "google_gemini",
                    "access_mode": "cli",
                    "execution_modes": ["direct_cli", "handoff_bundle"],
                    "state_classes": ["active-routing", "active-burn"],
                    "env_contracts": ["GEMINI_API_KEY"],
                    "observed_runtime": {
                        "routing_policy_enabled": True,
                        "active_burn_observed": True,
                        "api_configured": True,
                    },
                    "evidence": {
                        "kind": "cli_subscription",
                        "cli_probe": {
                            "status": "installed",
                            "expected_hosts": ["desk"],
                            "required_commands": ["gemini"],
                            "last_verified_at": "2026-03-25T19:15:00Z",
                            "source": "config/automation-backbone/tooling-inventory.json",
                        },
                        "billing": {
                            "status": "verified",
                            "subscribed_tier": "Google AI Pro",
                            "verified_monthly_cost_usd": 20,
                            "last_verified_at": "2026-03-28",
                            "source": "official_docs",
                        },
                    },
                },
            ]
        }
        tooling = {
            "hosts": [
                {
                    "id": "desk",
                    "tools": [
                        {"provider_id": "zai_glm_coding", "tool_id": "glm", "status": "installed"},
                        {"provider_id": "google_gemini", "tool_id": "gemini", "status": "installed"},
                    ],
                }
            ]
        }
        credential_surfaces = {"surfaces": [{"env_var_names": ["ZAI_API_KEY", "GEMINI_API_KEY"]}]}

        with (
            patch("athanor_agents.subscriptions.load_policy", return_value=policy),
            patch("athanor_agents.subscriptions.get_provider_catalog_registry", return_value=catalog),
            patch("athanor_agents.subscriptions.get_tooling_inventory_registry", return_value=tooling),
            patch(
                "athanor_agents.subscriptions.get_credential_surface_registry",
                return_value=credential_surfaces,
            ),
        ):
            lease = preview_execution_lease(
                LeaseRequest(
                    requester="coding-agent",
                    task_class="cheap_bulk_transform",
                    sensitivity="repo_internal",
                    interactive=False,
                    expected_context="medium",
                    parallelism="medium",
                )
            )

        self.assertEqual("google_gemini", lease.provider)
        self.assertNotIn("zai_glm_coding", lease.fallback)
        self.assertEqual(["zai_glm_coding"], lease.metadata["excluded_handoff_only_providers"])

    def test_preview_execution_lease_forces_sovereign_project_work_local(self) -> None:
        lease = preview_execution_lease(
            LeaseRequest(
                requester="coding-agent",
                task_class="multi_file_implementation",
                sensitivity="adult_sensitive",
                metadata={
                    "project_id": "eoq",
                    "policy_class": "sovereign_only",
                    "meta_lane": "sovereign_local",
                },
            )
        )

        self.assertEqual("athanor_local", lease.provider)
        self.assertNotIn("openai_codex", lease.fallback)
        self.assertTrue(lease.metadata["force_local_only"])


if __name__ == "__main__":
    unittest.main()
