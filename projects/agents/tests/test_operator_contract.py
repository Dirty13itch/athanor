import unittest
from unittest.mock import AsyncMock, patch


class FakeRedis:
    def __init__(self) -> None:
        self.stream_entries: list[tuple[str, dict[str, str]]] = []

    async def xadd(self, stream: str, mapping: dict[str, str], maxlen: int | None = None, approximate: bool = False):
        self.stream_entries.append((stream, dict(mapping)))
        return "1-0"


class OperatorContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_admin_action_requires_reason(self) -> None:
        from fastapi import HTTPException

        from athanor_agents.operator_contract import require_operator_action

        with self.assertRaises(HTTPException) as ctx:
            require_operator_action(
                {
                    "actor": "test-suite",
                    "session_id": "session-123",
                    "correlation_id": "corr-123",
                },
                action_class="admin",
            )

        self.assertEqual(400, ctx.exception.status_code)
        self.assertIn("reason is required", str(ctx.exception.detail))

    async def test_emit_operator_audit_event_writes_stream_entry(self) -> None:
        from athanor_agents.operator_contract import build_operator_action, emit_operator_audit_event

        fake_redis = FakeRedis()
        action = build_operator_action(
            {
                "actor": "test-suite",
                "session_id": "session-123",
                "correlation_id": "corr-123",
                "reason": "Operator verification",
            }
        )

        with patch("athanor_agents.operator_contract.get_redis", AsyncMock(return_value=fake_redis)):
            await emit_operator_audit_event(
                service="agent-server",
                route="/v1/governor/pause",
                action_class="admin",
                decision="accepted",
                status_code=200,
                action=action,
                detail="Paused global scope",
                target="global",
                metadata={"scope": "global"},
            )

        self.assertEqual(1, len(fake_redis.stream_entries))
        stream, mapping = fake_redis.stream_entries[0]
        self.assertEqual("athanor:operator:audit", stream)
        self.assertEqual("agent-server", mapping["service"])
        self.assertEqual("accepted", mapping["decision"])
        self.assertEqual("test-suite", mapping["actor"])
        self.assertEqual("global", mapping["target"])
