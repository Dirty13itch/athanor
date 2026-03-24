"""Corrective RAG — iterative retrieval with quality grading.

Implements CRAG pattern for the knowledge agent:
1. Retrieve documents (hybrid search: vector + keyword)
2. Grade relevance via LLM (RELEVANT / IRRELEVANT / AMBIGUOUS)
3. If insufficient relevant docs → rewrite query → re-retrieve (max 3 iterations)
4. Return graded, filtered results with confidence

Does NOT generate answers — the agent LLM handles that. This module
only improves the retrieval quality before the agent sees the documents.

Ported from: reference/hydra/src/hydra_tools/agentic_rag.py
Adapted for Athanor: LiteLLM via langchain, hybrid_search, no Prometheus,
no Graphiti (uses Qdrant + Neo4j directly).
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum

import httpx

from .config import settings

logger = logging.getLogger(__name__)

_QDRANT_URL = settings.qdrant_url
_LLM_BASE_URL = settings.llm_base_url
_LLM_API_KEY = settings.llm_api_key

# CRAG configuration
MAX_ITERATIONS = 3
MIN_RELEVANT_DOCS = 2
INITIAL_TOP_K = 8
GRADING_MODEL = "fast"  # Use fast model for grading (cheap, parallel)


class RelevanceGrade(str, Enum):
    RELEVANT = "relevant"
    IRRELEVANT = "irrelevant"
    AMBIGUOUS = "ambiguous"


@dataclass
class GradedDocument:
    """A retrieved document with its relevance grade."""
    content: str
    source: str
    score: float
    grade: RelevanceGrade
    reasoning: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class CRAGResult:
    """Result of a CRAG retrieval cycle."""
    query: str
    documents: list[GradedDocument]
    iterations: int
    rewritten_queries: list[str]
    relevant_count: int
    total_retrieved: int
    latency_ms: float

    @property
    def has_relevant_docs(self) -> bool:
        return self.relevant_count >= MIN_RELEVANT_DOCS

    def relevant_texts(self, limit: int = 5) -> list[str]:
        """Get text content of relevant documents for prompt injection."""
        relevant = [d for d in self.documents if d.grade == RelevanceGrade.RELEVANT]
        return [d.content for d in relevant[:limit]]

    def to_search_output(self) -> str:
        """Format as search_knowledge-compatible text output."""
        relevant = [d for d in self.documents if d.grade == RelevanceGrade.RELEVANT]
        if not relevant:
            ambiguous = [d for d in self.documents if d.grade == RelevanceGrade.AMBIGUOUS]
            relevant = ambiguous  # Fall back to ambiguous if no relevant

        if not relevant:
            return f"No relevant documents found for: {self.query} (searched {self.iterations} iteration(s))"

        lines = []
        for i, d in enumerate(relevant, 1):
            source = d.metadata.get("source", d.source)
            title = d.metadata.get("title", source)
            lines.append(f"[{i}] {title} (score: {d.score:.3f}, source: {source})")
            lines.append(f"    {d.content[:600]}")
            lines.append("")

        if self.iterations > 1:
            lines.append(f"(Retrieved after {self.iterations} iterations, {self.relevant_count} relevant docs)")

        return "\n".join(lines)


async def _get_embedding(client: httpx.AsyncClient, text: str) -> list[float]:
    """Get embedding vector via LiteLLM."""
    resp = await client.post(
        f"{_LLM_BASE_URL}/embeddings",
        json={"model": "embedding", "input": text},
        headers={"Authorization": f"Bearer {_LLM_API_KEY}"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]


async def _retrieve(
    client: httpx.AsyncClient,
    query: str,
    collection: str,
    limit: int = INITIAL_TOP_K,
) -> list[dict]:
    """Retrieve documents using hybrid search."""
    from .hybrid_search import hybrid_search

    vector = await _get_embedding(client, query)
    return await hybrid_search(
        client=client,
        collection=collection,
        vector=vector,
        query_text=query,
        limit=limit,
    )


async def _grade_document(
    client: httpx.AsyncClient,
    query: str,
    doc: dict,
) -> GradedDocument:
    """Grade a single document for relevance using LLM."""
    content = doc.get("payload", {}).get("text", "")
    if not content:
        content = doc.get("payload", {}).get("content", "")
    content_preview = content[:1500]

    prompt = (
        "Grade this document's relevance to the query. "
        "Respond with ONLY a JSON object: "
        '{"grade": "RELEVANT|IRRELEVANT|AMBIGUOUS", "reason": "brief explanation"}\n\n'
        f"Query: {query}\n\n"
        f"Document: {content_preview}"
    )

    try:
        resp = await client.post(
            f"{_LLM_BASE_URL}/chat/completions",
            json={
                "model": GRADING_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "max_tokens": 100,
            },
            headers={"Authorization": f"Bearer {_LLM_API_KEY}"},
            timeout=30,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"]

        # Extract JSON from response
        json_start = text.find("{")
        json_end = text.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            parsed = json.loads(text[json_start:json_end])
            grade_str = parsed.get("grade", "AMBIGUOUS").upper()
            reasoning = parsed.get("reason", "")

            grade = {
                "RELEVANT": RelevanceGrade.RELEVANT,
                "IRRELEVANT": RelevanceGrade.IRRELEVANT,
            }.get(grade_str, RelevanceGrade.AMBIGUOUS)

            return GradedDocument(
                content=content,
                source=doc.get("_source", "vector"),
                score=doc.get("score", 0),
                grade=grade,
                reasoning=reasoning,
                metadata=doc.get("payload", {}),
            )
    except Exception as e:
        logger.debug("Document grading failed: %s", e)

    # Default to ambiguous on failure
    return GradedDocument(
        content=content,
        source=doc.get("_source", "vector"),
        score=doc.get("score", 0),
        grade=RelevanceGrade.AMBIGUOUS,
        reasoning="grading failed",
        metadata=doc.get("payload", {}),
    )


async def _rewrite_query(
    client: httpx.AsyncClient,
    original_query: str,
    graded_docs: list[GradedDocument],
) -> str:
    """Rewrite query to improve retrieval."""
    doc_summaries = "\n".join(
        f"- [{d.grade.value}] {d.content[:100]}"
        for d in graded_docs[:3]
    ) if graded_docs else "No documents found."

    prompt = (
        "The original query didn't find enough relevant documents. "
        "Rewrite it to find better results. Respond with ONLY the new query.\n\n"
        f"Original: {original_query}\n\n"
        f"Retrieved docs:\n{doc_summaries}"
    )

    try:
        resp = await client.post(
            f"{_LLM_BASE_URL}/chat/completions",
            json={
                "model": GRADING_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 100,
            },
            headers={"Authorization": f"Bearer {_LLM_API_KEY}"},
            timeout=20,
        )
        resp.raise_for_status()
        new_query = resp.json()["choices"][0]["message"]["content"].strip()
        if new_query and len(new_query) > 5:
            return new_query
    except Exception as e:
        logger.debug("Query rewriting failed: %s", e)

    return original_query


async def corrective_search(
    query: str,
    collection: str = "knowledge",
    max_iterations: int = MAX_ITERATIONS,
) -> CRAGResult:
    """Execute a corrective RAG search cycle.

    Retrieves documents, grades them for relevance, and rewrites the query
    if insufficient relevant docs are found. Returns graded results.

    Args:
        query: The search query.
        collection: Qdrant collection to search.
        max_iterations: Max retrieval attempts (default 3).

    Returns:
        CRAGResult with graded documents and metadata.
    """
    start = time.monotonic()
    current_query = query
    all_graded: list[GradedDocument] = []
    rewritten_queries: list[str] = []

    async with httpx.AsyncClient() as client:
        for iteration in range(1, max_iterations + 1):
            logger.debug("CRAG iteration %d: %s", iteration, current_query[:80])

            # Step 1: Retrieve
            raw_docs = await _retrieve(client, current_query, collection)
            if not raw_docs:
                if iteration == 1:
                    # Try broader query on first empty result
                    current_query = await _rewrite_query(client, query, [])
                    rewritten_queries.append(current_query)
                    continue
                break

            # Step 2: Grade in parallel
            grade_tasks = [
                _grade_document(client, query, doc) for doc in raw_docs
            ]
            graded = await asyncio.gather(*grade_tasks, return_exceptions=True)

            for result in graded:
                if isinstance(result, GradedDocument):
                    all_graded.append(result)

            # Step 3: Check if we have enough relevant docs
            relevant_count = sum(
                1 for d in all_graded if d.grade == RelevanceGrade.RELEVANT
            )

            if relevant_count >= MIN_RELEVANT_DOCS:
                break

            # Not enough — rewrite and retry
            if iteration < max_iterations:
                current_query = await _rewrite_query(
                    client, query, all_graded[-len(raw_docs):]
                )
                rewritten_queries.append(current_query)

    latency_ms = (time.monotonic() - start) * 1000
    relevant_count = sum(1 for d in all_graded if d.grade == RelevanceGrade.RELEVANT)

    result = CRAGResult(
        query=query,
        documents=all_graded,
        iterations=len(rewritten_queries) + 1,
        rewritten_queries=rewritten_queries,
        relevant_count=relevant_count,
        total_retrieved=len(all_graded),
        latency_ms=latency_ms,
    )

    logger.info(
        "CRAG: %d relevant/%d total in %d iterations (%.0fms) for: %s",
        relevant_count, len(all_graded), result.iterations,
        latency_ms, query[:60],
    )

    return result
