"""Tests for context injection module — highest blast radius.

Covers pure formatting/decay functions and async embedding/search paths.
"""

import os
import sys
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


# ---------------------------------------------------------------------------
# Pure function tests — no mocking needed
# ---------------------------------------------------------------------------


class TestTimeDecayWeight(unittest.TestCase):
    """Test _time_decay_weight() linear decay behavior."""

    def _call(self, age_days: float) -> float:
        from athanor_agents.context import _time_decay_weight

        fake_ts = time.time() - (age_days * 86400)
        return _time_decay_weight(int(fake_ts))

    def test_fresh_preference_full_weight(self):
        self.assertAlmostEqual(self._call(0), 1.0, places=2)

    def test_within_full_weight_window(self):
        self.assertAlmostEqual(self._call(3), 1.0, places=2)

    def test_at_full_weight_boundary(self):
        self.assertAlmostEqual(self._call(7), 1.0, places=2)

    def test_midpoint_decay(self):
        # Midpoint between 7 and 90 = 48.5 days
        # progress = (48.5 - 7) / (90 - 7) = 41.5/83 ≈ 0.5
        # weight = 1.0 - 0.5 * 0.75 = 0.625
        weight = self._call(48.5)
        self.assertGreater(weight, 0.5)
        self.assertLess(weight, 0.8)

    def test_at_decay_horizon(self):
        self.assertAlmostEqual(self._call(90), 0.25, places=2)

    def test_beyond_decay_horizon(self):
        self.assertAlmostEqual(self._call(365), 0.25, places=2)


class TestFormatPreferences(unittest.TestCase):
    """Test _format_preferences() output."""

    def test_empty_input(self):
        from athanor_agents.context import _format_preferences

        self.assertEqual(_format_preferences([]), [])

    def test_formats_signal_and_content(self):
        from athanor_agents.context import _format_preferences

        results = [
            {"payload": {"content": "prefers dark mode", "signal_type": "explicit"}},
            {"payload": {"content": "likes terse output", "signal_type": "inferred"}},
        ]
        lines = _format_preferences(results)
        self.assertEqual(len(lines), 2)
        self.assertIn("[explicit]", lines[0])
        self.assertIn("prefers dark mode", lines[0])
        self.assertIn("[inferred]", lines[1])

    def test_skips_empty_content(self):
        from athanor_agents.context import _format_preferences

        results = [{"payload": {"content": "", "signal_type": "explicit"}}]
        self.assertEqual(_format_preferences(results), [])


class TestFormatActivity(unittest.TestCase):
    """Test _format_activity() output."""

    def test_empty_input(self):
        from athanor_agents.context import _format_activity

        self.assertEqual(_format_activity([], "test-agent"), [])

    def test_formats_qa_pairs(self):
        from athanor_agents.context import _format_activity

        results = [
            {
                "payload": {
                    "timestamp": "2026-03-14T12:00:00",
                    "input_summary": "What is vLLM?",
                    "output_summary": "vLLM is an inference engine.",
                }
            }
        ]
        lines = _format_activity(results, "test-agent")
        self.assertEqual(len(lines), 2)
        self.assertIn("Q: What is vLLM?", lines[0])
        self.assertIn("A: vLLM is an inference engine.", lines[1])

    def test_truncates_long_strings(self):
        from athanor_agents.context import _format_activity

        long_input = "x" * 300
        results = [
            {
                "payload": {
                    "timestamp": "2026-03-14T12:00:00",
                    "input_summary": long_input,
                    "output_summary": "",
                }
            }
        ]
        lines = _format_activity(results, "test-agent")
        # input_summary truncated to 120 chars
        self.assertLessEqual(len(lines[0]), 200)


class TestFormatKnowledge(unittest.TestCase):
    """Test _format_knowledge() output."""

    def test_empty_input(self):
        from athanor_agents.context import _format_knowledge

        self.assertEqual(_format_knowledge([]), [])

    def test_formats_title_score_text(self):
        from athanor_agents.context import _format_knowledge

        results = [
            {
                "payload": {"title": "GPU Guide", "text": "Use TP=4 for large models."},
                "score": 0.85,
            }
        ]
        lines = _format_knowledge(results)
        self.assertEqual(len(lines), 1)
        self.assertIn("**GPU Guide**", lines[0])
        self.assertIn("0.85", lines[0])

    def test_falls_back_to_source_for_title(self):
        from athanor_agents.context import _format_knowledge

        results = [
            {
                "payload": {"source": "docs/vllm.md", "text": "content here"},
                "score": 0.5,
            }
        ]
        lines = _format_knowledge(results)
        self.assertIn("docs/vllm.md", lines[0])


class TestFormatPersonalData(unittest.TestCase):
    """Test _format_personal_data() output."""

    def test_empty_input(self):
        from athanor_agents.context import _format_personal_data

        self.assertEqual(_format_personal_data([]), [])

    def test_formats_with_data_type(self):
        from athanor_agents.context import _format_personal_data

        results = [
            {
                "payload": {
                    "title": "Notes.md",
                    "text": "My meeting notes",
                    "data_type": "document",
                },
                "score": 0.7,
            }
        ]
        lines = _format_personal_data(results)
        self.assertEqual(len(lines), 1)
        self.assertIn("[document]", lines[0])
        self.assertIn("**Notes.md**", lines[0])


class TestFormatConversations(unittest.TestCase):
    """Test _format_conversations() output."""

    def test_empty_input(self):
        from athanor_agents.context import _format_conversations

        self.assertEqual(_format_conversations([]), [])

    def test_formats_user_and_response(self):
        from athanor_agents.context import _format_conversations

        results = [
            {
                "payload": {
                    "timestamp": "2026-03-14T10:00:00",
                    "user_message": "How do I deploy?",
                    "assistant_response": "Use ansible.",
                }
            }
        ]
        lines = _format_conversations(results)
        self.assertEqual(len(lines), 2)
        self.assertIn("User: How do I deploy?", lines[0])
        self.assertIn("Response: Use ansible.", lines[1])


class TestFormatPatterns(unittest.TestCase):
    """Test _format_patterns() output."""

    def test_empty_input(self):
        from athanor_agents.context import _format_patterns

        self.assertEqual(_format_patterns([]), [])

    def test_failure_cluster(self):
        from athanor_agents.context import _format_patterns

        patterns = [{"type": "failure_cluster", "count": 5}]
        lines = _format_patterns(patterns)
        self.assertEqual(len(lines), 1)
        self.assertIn("failed 5 tasks", lines[0])

    def test_negative_feedback_trend(self):
        from athanor_agents.context import _format_patterns

        patterns = [{"type": "negative_feedback_trend", "thumbs_down": 8, "thumbs_up": 2}]
        lines = _format_patterns(patterns)
        self.assertIn("8 negative", lines[0])

    def test_task_throughput_perfect(self):
        from athanor_agents.context import _format_patterns

        patterns = [{"type": "task_throughput", "success_rate": 1.0}]
        lines = _format_patterns(patterns)
        # Perfect rate produces no output
        self.assertEqual(lines, [])


class TestBuildContextMessage(unittest.TestCase):
    """Test _build_context_message() assembly logic."""

    def test_empty_inputs_returns_empty(self):
        from athanor_agents.context import _build_context_message

        result = _build_context_message([], [], [], "test-agent")
        self.assertEqual(result, "")

    def test_includes_header(self):
        from athanor_agents.context import _build_context_message

        result = _build_context_message(
            ["- pref1"], [], [], "test-agent"
        )
        self.assertIn("# Contextual Memory (auto-injected)", result)

    def test_includes_preferences_section(self):
        from athanor_agents.context import _build_context_message

        result = _build_context_message(
            ["- likes dark mode"], [], [], "test-agent"
        )
        self.assertIn("## Your Stored Preferences", result)
        self.assertIn("likes dark mode", result)

    def test_includes_activity_section(self):
        from athanor_agents.context import _build_context_message

        result = _build_context_message(
            [], ["- [2026] Q: test"], [], "my-agent"
        )
        self.assertIn("## Recent Interactions (my-agent)", result)

    def test_includes_knowledge_section(self):
        from athanor_agents.context import _build_context_message

        result = _build_context_message(
            [], [], ["- **Doc** (0.9): text"], "test-agent"
        )
        self.assertIn("## Relevant Documentation", result)

    def test_includes_goals_section(self):
        from athanor_agents.context import _build_context_message

        result = _build_context_message(
            [], [], [], "test-agent",
            goal_lines=["- Deploy new model"],
        )
        self.assertIn("## Active Goals", result)
        self.assertIn("Deploy new model", result)

    def test_includes_skill_context(self):
        from athanor_agents.context import _build_context_message

        result = _build_context_message(
            [], [], [], "test-agent",
            skill_context="## Relevant Skills\n### Search then Synthesize",
        )
        self.assertIn("Search then Synthesize", result)

    def test_includes_convention_lines(self):
        from athanor_agents.context import _build_context_message

        result = _build_context_message(
            [], [], [], "test-agent",
            convention_lines=["- Always use async"],
        )
        self.assertIn("## Learned Conventions", result)

    def test_truncation_at_max_chars(self):
        from athanor_agents.context import _build_context_message, MAX_CONTEXT_CHARS

        # Create content larger than budget
        big_prefs = [f"- preference item {i} " + "x" * 200 for i in range(50)]
        result = _build_context_message(big_prefs, [], [], "test-agent")
        self.assertLessEqual(len(result), MAX_CONTEXT_CHARS + 50)  # small margin for truncation suffix
        self.assertIn("[context truncated]", result)

    def test_section_ordering(self):
        from athanor_agents.context import _build_context_message

        result = _build_context_message(
            pref_lines=["- pref"],
            activity_lines=["- activity"],
            knowledge_lines=["- knowledge"],
            agent_name="test",
            goal_lines=["- goal"],
            convention_lines=["- convention"],
        )
        # Goals should appear before preferences
        goal_pos = result.index("## Active Goals")
        pref_pos = result.index("## Your Stored Preferences")
        activity_pos = result.index("## Recent Interactions")
        knowledge_pos = result.index("## Relevant Documentation")
        self.assertLess(goal_pos, pref_pos)
        self.assertLess(pref_pos, activity_pos)
        self.assertLess(activity_pos, knowledge_pos)

    def test_cst_line_included(self):
        from athanor_agents.context import _build_context_message

        result = _build_context_message(
            [], [], [], "test-agent",
            cst_line="Focus: high, Energy: medium",
        )
        self.assertIn("## Cognitive State", result)
        self.assertIn("Focus: high", result)

    def test_graph_related_section(self):
        from athanor_agents.context import _build_context_message

        result = _build_context_message(
            [], [], [], "test-agent",
            graph_related_lines=["- [research] **Doc** (`docs/x.md`)"],
        )
        self.assertIn("## Related Documentation (graph)", result)

    def test_personal_data_section(self):
        from athanor_agents.context import _build_context_message

        result = _build_context_message(
            [], [], [], "test-agent",
            personal_data_lines=["- **Notes** (0.8): content"],
        )
        self.assertIn("## Personal Data", result)

    def test_conversations_section(self):
        from athanor_agents.context import _build_context_message

        result = _build_context_message(
            [], [], [], "my-agent",
            conversation_lines=["- [2026] User: hello"],
        )
        self.assertIn("## Previous Conversations (my-agent)", result)


class TestAgentContextConfig(unittest.TestCase):
    """Test per-agent context configuration."""

    def test_all_known_agents_have_config(self):
        from athanor_agents.context import AGENT_CONTEXT_CONFIG

        expected_agents = {
            "general-assistant", "media-agent", "home-agent",
            "research-agent", "creative-agent", "knowledge-agent",
            "coding-agent", "data-curator",
        }
        self.assertTrue(expected_agents.issubset(set(AGENT_CONTEXT_CONFIG.keys())))

    def test_media_agent_no_knowledge(self):
        from athanor_agents.context import AGENT_CONTEXT_CONFIG

        self.assertEqual(AGENT_CONTEXT_CONFIG["media-agent"]["knowledge_limit"], 0)

    def test_default_config_exists(self):
        from athanor_agents.context import _DEFAULT_CONFIG

        self.assertIn("prefs_limit", _DEFAULT_CONFIG)
        self.assertIn("activity_limit", _DEFAULT_CONFIG)

    def test_unknown_agent_gets_default(self):
        from athanor_agents.context import AGENT_CONTEXT_CONFIG, _DEFAULT_CONFIG

        config = AGENT_CONTEXT_CONFIG.get("nonexistent-agent", _DEFAULT_CONFIG)
        self.assertEqual(config, _DEFAULT_CONFIG)


# ---------------------------------------------------------------------------
# Async tests — mock external dependencies
# ---------------------------------------------------------------------------


class TestGetEmbeddingAsync(unittest.IsolatedAsyncioTestCase):
    """Test _get_embedding_async() with mocked httpx."""

    async def test_returns_embedding_vector(self):
        from athanor_agents.context import _get_embedding_async

        fake_vector = [0.1] * 384
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "data": [{"embedding": fake_vector}]
        }

        with patch.object(
            sys.modules["athanor_agents.context"],
            "_async_client",
        ) as mock_client:
            mock_client.post = AsyncMock(return_value=mock_response)
            result = await _get_embedding_async("test query")

        self.assertEqual(result, fake_vector)
        mock_client.post.assert_called_once()

    async def test_truncates_input_to_2000_chars(self):
        from athanor_agents.context import _get_embedding_async

        fake_vector = [0.1] * 384
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"data": [{"embedding": fake_vector}]}

        with patch.object(
            sys.modules["athanor_agents.context"],
            "_async_client",
        ) as mock_client:
            mock_client.post = AsyncMock(return_value=mock_response)
            await _get_embedding_async("x" * 5000)

        call_args = mock_client.post.call_args
        sent_input = call_args[1]["json"]["input"]
        self.assertLessEqual(len(sent_input), 2000)


class TestSearchCollection(unittest.IsolatedAsyncioTestCase):
    """Test _search_collection() with mocked httpx."""

    async def test_returns_results(self):
        from athanor_agents.context import _search_collection

        fake_results = [
            {"id": 1, "score": 0.9, "payload": {"content": "test"}}
        ]
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"result": fake_results}

        with patch.object(
            sys.modules["athanor_agents.context"],
            "_async_client",
        ) as mock_client:
            mock_client.post = AsyncMock(return_value=mock_response)
            result = await _search_collection(
                "preferences", [0.1] * 384, limit=3
            )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["score"], 0.9)

    async def test_zero_limit_returns_empty(self):
        from athanor_agents.context import _search_collection

        result = await _search_collection("preferences", [0.1], limit=0)
        self.assertEqual(result, [])

    async def test_connection_error_returns_empty(self):
        from athanor_agents.context import _search_collection

        with patch.object(
            sys.modules["athanor_agents.context"],
            "_async_client",
        ) as mock_client:
            mock_client.post = AsyncMock(side_effect=Exception("Connection refused"))
            result = await _search_collection("preferences", [0.1], limit=3)

        self.assertEqual(result, [])

    async def test_includes_filter_in_body(self):
        from athanor_agents.context import _search_collection

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"result": []}

        test_filter = {"must": [{"key": "agent", "match": {"value": "test"}}]}

        with patch.object(
            sys.modules["athanor_agents.context"],
            "_async_client",
        ) as mock_client:
            mock_client.post = AsyncMock(return_value=mock_response)
            await _search_collection(
                "preferences", [0.1], limit=5, filter_dict=test_filter
            )

        call_body = mock_client.post.call_args[1]["json"]
        self.assertEqual(call_body["filter"], test_filter)


class TestSearchKnowledgeContext(unittest.IsolatedAsyncioTestCase):
    """Test GraphRAG-first knowledge search with fallback."""

    async def test_graphrag_results_skip_legacy_fallback(self):
        from athanor_agents.context import _search_knowledge_context

        graphrag_hits = [
            {
                "id": "chunk-1",
                "payload": {"title": "GraphRAG Doc", "source": "docs/x.md", "text": "context"},
                "score": 0.91,
            }
        ]

        with patch.object(
            sys.modules["athanor_agents.context"],
            "query_hybrid_knowledge",
            AsyncMock(return_value=MagicMock(results=graphrag_hits, route="hybrid", warnings=["vector path unavailable"])),
        ) as mock_graphrag, patch.object(
            sys.modules["athanor_agents.context"],
            "_hybrid_search_collection",
            AsyncMock(),
        ) as mock_legacy:
            knowledge, graph_related, meta = await _search_knowledge_context(
                [0.1] * 4, "dashboard routing", 3
            )

        self.assertEqual(knowledge, graphrag_hits)
        self.assertEqual(graph_related, [])
        self.assertEqual(meta["backend"], "graphrag")
        self.assertEqual(meta["route"], "hybrid")
        self.assertIn("vector path unavailable", meta["warnings"])
        mock_graphrag.assert_awaited_once()
        mock_legacy.assert_not_awaited()

    async def test_graphrag_failure_falls_back_to_legacy_path(self):
        from athanor_agents.context import _search_knowledge_context

        legacy_hits = [
            {"payload": {"source": "docs/fallback.md", "text": "fallback knowledge"}, "score": 0.7}
        ]
        related_hits = [{"source": "docs/related.md", "title": "Related"}]
        fake_graph_module = MagicMock(expand_knowledge_graph=AsyncMock(return_value=related_hits))

        with patch.object(
            sys.modules["athanor_agents.context"],
            "query_hybrid_knowledge",
            AsyncMock(side_effect=RuntimeError("service down")),
        ), patch.object(
            sys.modules["athanor_agents.context"],
            "_hybrid_search_collection",
            AsyncMock(return_value=legacy_hits),
        ) as mock_legacy, patch.dict(
            sys.modules,
            {"athanor_agents.graph_context": fake_graph_module},
        ):
            knowledge, graph_related, meta = await _search_knowledge_context(
                [0.1] * 4, "dashboard routing", 3
            )

        self.assertEqual(knowledge, legacy_hits)
        self.assertEqual(graph_related, related_hits)
        self.assertEqual(meta["backend"], "legacy_fallback")
        self.assertEqual(meta["route"], "hybrid_search")
        self.assertIn("graphrag_unavailable:RuntimeError", meta["warnings"])
        mock_legacy.assert_awaited_once()

    async def test_graphrag_timeout_warning_falls_back_to_legacy_path(self):
        from athanor_agents.context import _search_knowledge_context

        graphrag_hits = [
            {
                "id": "chunk-1",
                "payload": {"title": "GraphRAG Doc", "source": "docs/x.md", "text": "context"},
                "score": 0.91,
            }
        ]
        legacy_hits = [
            {"payload": {"source": "docs/fallback.md", "text": "fallback knowledge"}, "score": 0.7}
        ]

        with patch.object(
            sys.modules["athanor_agents.context"],
            "query_hybrid_knowledge",
            AsyncMock(
                return_value=MagicMock(
                    results=graphrag_hits,
                    route="graph_fallback",
                    warnings=["vector path unavailable: ReadTimeout"],
                )
            ),
        ), patch.object(
            sys.modules["athanor_agents.context"],
            "_hybrid_search_collection",
            AsyncMock(return_value=legacy_hits),
        ) as mock_legacy:
            knowledge, graph_related, meta = await _search_knowledge_context(
                [0.1] * 4, "dashboard routing", 3
            )

        self.assertEqual(knowledge, legacy_hits)
        self.assertEqual(graph_related, [])
        self.assertEqual(meta["backend"], "legacy_fallback")
        self.assertEqual(meta["route"], "hybrid_search")
        self.assertIn("vector path unavailable: ReadTimeout", meta["warnings"])
        self.assertIn("graphrag_degraded_timeout_fallback", meta["warnings"])
        self.assertNotIn("graphrag_empty_result", meta["warnings"])
        mock_legacy.assert_awaited_once()


class TestScrollActivity(unittest.IsolatedAsyncioTestCase):
    """Test _scroll_activity() with mocked httpx."""

    async def test_returns_sorted_by_timestamp_desc(self):
        from athanor_agents.context import _scroll_activity

        fake_points = [
            {"payload": {"timestamp_unix": 1000, "agent": "test"}},
            {"payload": {"timestamp_unix": 3000, "agent": "test"}},
            {"payload": {"timestamp_unix": 2000, "agent": "test"}},
        ]
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"result": {"points": fake_points}}

        with patch.object(
            sys.modules["athanor_agents.context"],
            "_async_client",
        ) as mock_client:
            mock_client.post = AsyncMock(return_value=mock_response)
            result = await _scroll_activity("test", limit=3)

        self.assertEqual(len(result), 3)
        # Should be sorted descending by timestamp_unix
        timestamps = [p["payload"]["timestamp_unix"] for p in result]
        self.assertEqual(timestamps, [3000, 2000, 1000])

    async def test_zero_limit_returns_empty(self):
        from athanor_agents.context import _scroll_activity

        result = await _scroll_activity("test", limit=0)
        self.assertEqual(result, [])


class TestEnrichContext(unittest.IsolatedAsyncioTestCase):
    """Test enrich_context() end-to-end with all external deps mocked."""

    async def test_short_message_returns_empty(self):
        from athanor_agents.context import enrich_context

        result = await enrich_context("general-assistant", "hi")
        self.assertEqual(result, "")

    async def test_embedding_failure_returns_empty(self):
        from athanor_agents.context import enrich_context

        with patch.object(
            sys.modules["athanor_agents.context"],
            "_async_client",
        ) as mock_client:
            mock_client.post = AsyncMock(side_effect=Exception("embedding down"))
            result = await enrich_context("general-assistant", "What is the GPU status?")

        self.assertEqual(result, "")

    async def test_embedding_breaker_open_returns_empty_without_upstream_call(self):
        from athanor_agents.context import enrich_context

        with (
            patch("athanor_agents.context.get_circuit_breakers") as mock_breakers,
            patch.object(sys.modules["athanor_agents.context"], "_async_client") as mock_client,
        ):
            mock_breakers.return_value.execute_with_breaker = AsyncMock(return_value=[])
            result = await enrich_context("general-assistant", "What is the GPU status?")

        mock_client.post.assert_not_called()
        self.assertEqual(result, "")


class TestGetLatencyStats(unittest.TestCase):
    """Test get_latency_stats() with the ring buffer."""

    def test_empty_buffer_returns_zero_count(self):
        from athanor_agents.context import get_latency_stats, _latency_records

        _latency_records.clear()
        stats = get_latency_stats()
        self.assertEqual(stats["count"], 0)

    def test_populated_buffer_returns_stats(self):
        from athanor_agents.context import get_latency_stats, _latency_records

        _latency_records.clear()
        for i in range(10):
            _latency_records.append({
                "agent": "test-agent",
                "elapsed_ms": (i + 1) * 10,
                "hits": 3,
                "ts": time.time(),
            })

        stats = get_latency_stats()
        self.assertEqual(stats["count"], 10)
        self.assertIn("avg_ms", stats)
        self.assertIn("p50_ms", stats)
        self.assertIn("p95_ms", stats)
        self.assertIn("by_agent", stats)
        self.assertIn("test-agent", stats["by_agent"])


if __name__ == "__main__":
    unittest.main()
