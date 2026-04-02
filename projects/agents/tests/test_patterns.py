import unittest


class TestPatternTimestamps(unittest.IsolatedAsyncioTestCase):
    def test_coerce_timestamp_accepts_numeric_strings(self):
        from athanor_agents.patterns import _coerce_timestamp

        self.assertEqual(1775138059.0, _coerce_timestamp("1775138059"))
        self.assertEqual(1775138059.5, _coerce_timestamp("1775138059.5"))
        self.assertIsNone(_coerce_timestamp(""))
        self.assertIsNone(_coerce_timestamp("not-a-timestamp"))

    async def test_detect_home_routine_handles_string_timestamps(self):
        from athanor_agents.patterns import _detect_agent_behavioral_patterns

        report = {"patterns": [], "recommendations": []}
        activity = [
            {"agent": "home-agent", "timestamp": "1775138059"},
            {"agent": "home-agent", "timestamp": "1775138060"},
            {"agent": "home-agent", "timestamp": "1775138061"},
            {"agent": "home-agent", "timestamp": "1775138062"},
            {"agent": "home-agent", "timestamp": "1775138063"},
        ]

        await _detect_agent_behavioral_patterns(report, activity, events=[])

        home_pattern = next(
            pattern for pattern in report["patterns"] if pattern["type"] == "home_routine"
        )
        self.assertEqual("home-agent", home_pattern["agent"])
        self.assertEqual(5, home_pattern["activity_count"])
        self.assertTrue(home_pattern["peak_hours"])


if __name__ == "__main__":
    unittest.main()
