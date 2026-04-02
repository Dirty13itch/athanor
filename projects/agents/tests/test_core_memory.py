import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from athanor_agents.core_memory import (  # noqa: E402
    CORE_MEMORY_KEY_PREFIX,
    DEFAULT_PERSONAS,
    get_core_memory,
    seed_core_memories,
)


class _FakeRedis:
    def __init__(self, store: dict[str, str | bytes]) -> None:
        self.store = dict(store)

    async def get(self, key: str):
        return self.store.get(key)

    async def set(self, key: str, value: str) -> None:
        self.store[key] = value


class CoreMemoryContractTest(unittest.IsolatedAsyncioTestCase):
    async def test_get_core_memory_returns_default_copy_for_invalid_json(self) -> None:
        redis = _FakeRedis(
            {
                f"{CORE_MEMORY_KEY_PREFIX}media-agent": "{not-json",
            }
        )

        with patch("athanor_agents.core_memory._get_redis", return_value=redis):
            memory = await get_core_memory("media-agent")

        self.assertEqual(DEFAULT_PERSONAS["media-agent"], memory)
        self.assertIsNot(DEFAULT_PERSONAS["media-agent"], memory)

        memory["bio"] = "mutated"
        self.assertNotEqual("mutated", DEFAULT_PERSONAS["media-agent"]["bio"])

    async def test_seed_core_memories_repairs_invalid_existing_payloads(self) -> None:
        store: dict[str, str] = {}
        for agent_name, persona in DEFAULT_PERSONAS.items():
            store[f"{CORE_MEMORY_KEY_PREFIX}{agent_name}"] = json.dumps(persona)
        store[f"{CORE_MEMORY_KEY_PREFIX}media-agent"] = "{not-json"

        redis = _FakeRedis(store)

        with patch("athanor_agents.core_memory._get_redis", return_value=redis):
            mutated = await seed_core_memories()

        self.assertEqual(1, mutated)
        repaired = json.loads(redis.store[f"{CORE_MEMORY_KEY_PREFIX}media-agent"])
        self.assertEqual(DEFAULT_PERSONAS["media-agent"], repaired)


if __name__ == "__main__":
    unittest.main()
