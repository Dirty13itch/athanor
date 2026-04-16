"""Research tools — web search, page fetching, knowledge search."""

import httpx
from langchain_core.tools import tool

from ..config import settings
from ..services import registry

_QDRANT_URL = settings.qdrant_url
_EMBEDDING_URL = registry.litellm_openai_url
_EMBEDDING_KEY = settings.litellm_api_key


def _get_embedding(text: str) -> list[float]:
    """Get embedding vector from the embedding model via LiteLLM."""
    resp = httpx.post(
        f"{_EMBEDDING_URL}/embeddings",
        json={"model": "embedding", "input": text},
        headers={"Authorization": f"Bearer {_EMBEDDING_KEY}"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]


@tool
def web_search(query: str, max_results: int = 8) -> str:
    """Search the web using DuckDuckGo. Returns titles, URLs, and snippets for top results.

    Use this to find current information about any topic. Good for:
    - Latest software releases and changelogs
    - Technical documentation and tutorials
    - News and announcements
    - Comparisons and benchmarks
    """
    from ddgs import DDGS

    try:
        results = DDGS().text(query, max_results=max_results)
        if not results:
            return f"No results found for: {query}"

        lines = []
        for i, r in enumerate(results, 1):
            lines.append(f"[{i}] {r.get('title', 'Untitled')}")
            lines.append(f"    URL: {r.get('href', 'N/A')}")
            lines.append(f"    {r.get('body', 'No snippet')}")
            lines.append("")
        return "\n".join(lines)
    except Exception as e:
        return f"Search error: {e}"


@tool
def fetch_page(url: str, max_chars: int = 8000) -> str:
    """Fetch a web page and extract its text content. Returns cleaned text.

    Use this after web_search to read the full content of a promising result.
    Strips HTML, scripts, and styles. Truncates to max_chars.
    """
    try:
        resp = httpx.get(
            url,
            timeout=15,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; AthanorResearch/1.0)"},
        )
        resp.raise_for_status()

        from html.parser import HTMLParser

        class TextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.parts: list[str] = []
                self._skip = False
                self._skip_tags = {"script", "style", "nav", "footer", "header"}

            def handle_starttag(self, tag, attrs):
                if tag in self._skip_tags:
                    self._skip = True

            def handle_endtag(self, tag):
                if tag in self._skip_tags:
                    self._skip = False

            def handle_data(self, data):
                if not self._skip:
                    text = data.strip()
                    if text:
                        self.parts.append(text)

        parser = TextExtractor()
        parser.feed(resp.text)
        text = "\n".join(parser.parts)

        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[...truncated]"

        return f"Content from {url}:\n\n{text}" if text else f"No readable text content at {url}"
    except Exception as e:
        return f"Failed to fetch {url}: {e}"


@tool
def search_knowledge(query: str, collection: str = "knowledge", limit: int = 5) -> str:
    """Search the Athanor knowledge base using semantic (vector) search.

    Searches indexed documents in Qdrant. Good for:
    - Finding relevant Athanor documentation
    - Checking if something was previously researched
    - Cross-referencing existing knowledge
    """
    try:
        vector = _get_embedding(query)

        resp = httpx.post(
            f"{_QDRANT_URL}/collections/{collection}/points/search",
            json={
                "vector": vector,
                "limit": limit,
                "with_payload": True,
            },
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json().get("result", [])

        if not results:
            return f"No matches found in {collection} for: {query}"

        lines = []
        for i, r in enumerate(results, 1):
            score = r.get("score", 0)
            payload = r.get("payload", {})
            title = payload.get("title", payload.get("source", "Unknown"))
            text = payload.get("text", payload.get("content", ""))[:500]
            lines.append(f"[{i}] {title} (score: {score:.3f})")
            lines.append(f"    {text}")
            lines.append("")
        return "\n".join(lines)
    except Exception as e:
        return f"Knowledge search error: {e}"


@tool
def query_infrastructure(cypher_query: str) -> str:
    """Query the Athanor infrastructure graph using Cypher (Neo4j).

    The graph contains: Node, Service, Agent, Project entities with
    RUNS_ON, DEPENDS_ON, ROUTES_TO, MANAGES, USES relationships.

    Example queries:
    - "MATCH (s:Service)-[:RUNS_ON]->(n:Node {name: 'node1'}) RETURN s.name"
    - "MATCH (s:Service)-[:DEPENDS_ON]->(t:Service) RETURN s.name, t.name"
    - "MATCH (n) RETURN labels(n), n.name LIMIT 20"
    """
    try:
        resp = httpx.post(
            registry.neo4j_commit_url,
            json={"statements": [{"statement": cypher_query}]},
            auth=registry.neo4j_auth,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        errors = data.get("errors", [])
        if errors:
            return f"Cypher error: {errors[0].get('message', 'Unknown error')}"

        results = data.get("results", [{}])[0]
        columns = results.get("columns", [])
        rows = results.get("data", [])

        if not rows:
            return "Query returned no results."

        lines = [" | ".join(columns)]
        lines.append("-" * len(lines[0]))
        for row in rows[:50]:
            values = [str(v) for v in row.get("row", [])]
            lines.append(" | ".join(values))

        return "\n".join(lines)
    except Exception as e:
        return f"Graph query error: {e}"


from .knowledge import search_signals

RESEARCH_TOOLS = [web_search, fetch_page, search_knowledge, query_infrastructure, search_signals]
