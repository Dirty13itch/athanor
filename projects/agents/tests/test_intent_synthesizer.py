from __future__ import annotations

import unittest
from unittest.mock import patch

import httpx

from athanor_agents import intent_synthesizer


class _FakeLLMClient:
    def __init__(self, *, timeout: float, calls: list[dict], effect):
        self.timeout = timeout
        self.calls = calls
        self.effect = effect

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url: str, *, json: dict, headers: dict | None = None):
        self.calls.append(
            {
                "timeout": self.timeout,
                "url": url,
                "json": json,
                "headers": headers or {},
            }
        )
        if isinstance(self.effect, Exception):
            raise self.effect
        return self.effect


class _FakeAsyncClientFactory:
    def __init__(self, effects: list[object]):
        self.effects = list(effects)
        self.calls: list[dict] = []

    def __call__(self, *, timeout: float):
        effect = self.effects.pop(0)
        return _FakeLLMClient(timeout=timeout, calls=self.calls, effect=effect)


class IntentSynthesizerFallbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_call_llm_raw_uses_heuristic_fallback_after_timeout(self) -> None:
        factory = _FakeAsyncClientFactory([httpx.TimeoutException("primary timed out")])
        owner_profile = {
            "domains": {
                "infrastructure": {
                    "momentum": "idle",
                    "interest": 0.5,
                    "status": "active",
                    "gaps": ["Audit routing drift"],
                    "agents": ["general-assistant", "coding-agent"],
                },
                "creative": {
                    "momentum": "active",
                    "interest": 0.9,
                    "status": "active",
                    "gaps": ["Ship a new visual experiment"],
                    "agents": ["creative-agent"],
                },
            },
            "capacity": {
                "agents_idle": ["creative-agent", "general-assistant"],
            },
        }

        original_url = intent_synthesizer.settings.litellm_url
        original_key = intent_synthesizer.settings.litellm_api_key
        original_model = intent_synthesizer.settings.llm_model
        intent_synthesizer.settings.litellm_url = "http://litellm.local"
        intent_synthesizer.settings.litellm_api_key = "secret-token"
        intent_synthesizer.settings.llm_model = "reasoning"
        try:
            with patch("httpx.AsyncClient", new=factory):
                proposals = await intent_synthesizer._call_llm_raw(
                    "Generate strategic intents.",
                    owner_profile=owner_profile,
                )
        finally:
            intent_synthesizer.settings.litellm_url = original_url
            intent_synthesizer.settings.litellm_api_key = original_key
            intent_synthesizer.settings.llm_model = original_model

        self.assertEqual(2, len(proposals))
        self.assertEqual("reasoning", factory.calls[0]["json"]["model"])
        self.assertEqual(45, factory.calls[0]["timeout"])
        self.assertEqual(
            {"Authorization": "Bearer secret-token"},
            factory.calls[0]["headers"],
        )
        self.assertEqual("creative-agent", proposals[0]["agent"])
        self.assertTrue(proposals[0]["explore"])


if __name__ == "__main__":
    unittest.main()
