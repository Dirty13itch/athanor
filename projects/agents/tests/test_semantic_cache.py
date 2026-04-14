import unittest
from unittest.mock import AsyncMock, MagicMock, patch


class TestSemanticCacheEmbeddings(unittest.IsolatedAsyncioTestCase):
    async def test_embed_returns_none_when_embedding_breaker_is_open(self):
        from athanor_agents.semantic_cache import SemanticCache

        cache = SemanticCache()
        cache._client = MagicMock()
        cache._client.post = AsyncMock()

        with patch("athanor_agents.semantic_cache.get_circuit_breakers") as mock_breakers:
            mock_breakers.return_value.execute_with_breaker = AsyncMock(return_value=None)
            result = await cache._embed("hello world")

        cache._client.post.assert_not_called()
        self.assertIsNone(result)

    async def test_embed_uses_shorter_timeout_and_returns_vector(self):
        from athanor_agents.semantic_cache import SEMANTIC_CACHE_EMBED_TIMEOUT, SemanticCache

        cache = SemanticCache()
        response = MagicMock()
        response.raise_for_status = MagicMock()
        response.json.return_value = {"data": [{"embedding": [0.1, 0.2, 0.3]}]}
        cache._client = MagicMock()
        cache._client.post = AsyncMock(return_value=response)

        async def _execute_with_breaker(_service, operation, fallback=None):
            return await operation()

        with patch("athanor_agents.semantic_cache.get_circuit_breakers") as mock_breakers:
            mock_breakers.return_value.execute_with_breaker = AsyncMock(side_effect=_execute_with_breaker)
            result = await cache._embed("hello world")

        self.assertEqual([0.1, 0.2, 0.3], result)
        cache._client.post.assert_awaited_once()
        self.assertEqual(
            SEMANTIC_CACHE_EMBED_TIMEOUT,
            cache._client.post.await_args.kwargs["timeout"],
        )
