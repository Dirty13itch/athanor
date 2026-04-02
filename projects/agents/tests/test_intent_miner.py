import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


class IntentMinerTest(unittest.IsolatedAsyncioTestCase):
    async def test_creative_quality_uses_bounded_scan_and_batch_reads(self) -> None:
        from athanor_agents import intent_miner

        mock_redis = AsyncMock()
        mock_redis.scan = AsyncMock(
            side_effect=[
                (
                    b"1",
                    [
                        b"athanor:eoq:video_quality:q1:defiant",
                        b"athanor:eoq:video_quality:q2:defiant",
                        b"athanor:eoq:video_quality:q3:defiant",
                    ],
                ),
                (
                    b"0",
                    [b"athanor:eoq:video_quality:q4:defiant"],
                ),
            ]
        )
        mock_redis.mget = AsyncMock(
            side_effect=[
                [
                    b'{"queen_id":"q1","stage":"defiant","score":0.4,"quality":"production"}',
                    b'{"queen_id":"q2","stage":"yielding","score":0.8,"quality":"quick"}',
                ],
            ]
        )

        with (
            patch("athanor_agents.intent_miner.CREATIVE_QUALITY_SCAN_MAX_KEYS", 2),
            patch("athanor_agents.workspace.get_redis", AsyncMock(return_value=mock_redis)),
        ):
            intents = await intent_miner._mine_creative_quality()

        self.assertEqual(2, len(intents))
        self.assertEqual("creative_quality", intents[0].source)
        self.assertIn("Regenerate low-quality video", intents[0].text)
        self.assertIn("Upgrade quick-preview video", intents[1].text)
        scan_call = mock_redis.scan.await_args_list[0]
        self.assertEqual(intent_miner.CREATIVE_QUALITY_SCAN_MATCH, scan_call.kwargs["match"])
        self.assertEqual(intent_miner.CREATIVE_QUALITY_SCAN_COUNT, scan_call.kwargs["count"])
        mock_redis.mget.assert_awaited_once_with(
            [
                b"athanor:eoq:video_quality:q1:defiant",
                b"athanor:eoq:video_quality:q2:defiant",
            ]
        )


if __name__ == "__main__":
    unittest.main()
