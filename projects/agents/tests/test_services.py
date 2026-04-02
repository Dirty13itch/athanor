from __future__ import annotations

import unittest

from athanor_agents.services import prometheus_host_regex


class PrometheusHostRegexTests(unittest.TestCase):
    def test_prometheus_host_regex_uses_promql_safe_dot_matching(self) -> None:
        regex = prometheus_host_regex("192.168.1.244", "192.168.1.225")
        self.assertEqual("192[.]168[.]1[.]244|192[.]168[.]1[.]225", regex)
        self.assertNotIn(r"\.", regex)


if __name__ == "__main__":
    unittest.main()
