#!/usr/bin/env python3
"""Athanor Semantic Router -- content classification for task routing (10-25ms)."""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from semantic_router import Route, SemanticRouter
from semantic_router.encoders import HuggingFaceEncoder
from semantic_router.index.local import LocalIndex

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from service_contract import build_health_snapshot, dependency_record


routes = [
    Route(
        name="cloud_safe",
        utterances=[
            "write a function",
            "refactor this code",
            "add unit tests",
            "fix this bug",
            "create a new component",
            "optimize this query",
            "add error handling",
            "implement the API endpoint",
            "write documentation",
            "review this PR",
            "explain how this works",
            "help me understand this concept",
            "summarize this article",
            "translate this text",
            "draft a professional email",
        ],
    ),
    Route(
        name="refusal_sensitive",
        utterances=[
            "write explicit scene",
            "nsfw content",
            "adult dialogue",
            "sexual description",
            "write erotic story",
            "porn scene",
            "blowjob dialogue",
            "hardcore scene",
            "write a graphic sex scene",
            "explicit adult content",
            "erotic fiction",
            "write smut",
            "sexual roleplay",
            "dirty talk dialogue",
            "write an erotic story about",
            "generate adult fiction",
            "describe a sex scene between",
            "nude description",
            "write a steamy romance scene",
            "explicit sexual encounter",
            "pornographic story",
            "xxx rated content",
            "hentai script",
            "write about two people having sex",
            "describe intercourse",
            "orgasm description",
            "masturbation scene",
            "bondage scenario",
            "empire of broken queens",
            "queen profile",
            "EoBQ scene",
            "generate performer prompt",
            "write prompt for adult image",
        ],
    ),
    Route(
        name="sovereign_only",
        utterances=[
            "scan for vulnerabilities",
            "pen test this server",
            "exploit the endpoint",
            "hack into",
            "bypass authentication",
            "crack password",
            "security audit",
            "find open ports",
            "SQL injection",
            "XSS attack vector",
            "write a phishing email",
            "create malware",
            "bypass content filter",
            "jailbreak the AI",
            "ignore your instructions",
            "override safety",
        ],
    ),
    Route(
        name="research",
        utterances=[
            "research this topic",
            "find information about",
            "compare options for",
            "what are the best",
            "survey available tools",
            "deep dive into",
            "investigate alternatives",
            "benchmark comparison",
        ],
    ),
    Route(
        name="quick_question",
        utterances=[
            "what is",
            "how do I",
            "explain",
            "what does this mean",
            "quick question",
            "syntax for",
            "how to use",
            "difference between",
        ],
    ),
]


SERVICE_NAME = "semantic-router"
SERVICE_VERSION = "0.1.0"
SERVICE_STARTED_AT = datetime.now(timezone.utc).isoformat()
ENCODER_NAME = "sentence-transformers/all-MiniLM-L6-v2"

router: SemanticRouter | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global router
    encoder = HuggingFaceEncoder(name=ENCODER_NAME)
    router = SemanticRouter(encoder=encoder, routes=routes, index=LocalIndex())
    router.sync("local")
    print(f"Router ready, index.is_ready={router.index.is_ready()}")
    yield


app = FastAPI(title="Athanor Semantic Router", version=SERVICE_VERSION, lifespan=lifespan)


def build_semantic_router_health_snapshot() -> dict:
    checked_at = datetime.now(timezone.utc).isoformat()
    router_ready = bool(router and router.index.is_ready())
    dependencies = [
        dependency_record(
            "semantic_index",
            status="healthy" if router_ready else "degraded",
            detail=(
                f"Semantic index ready with {len(routes)} route families"
                if router_ready
                else "Semantic router index not ready"
            ),
            last_checked_at=checked_at,
        ),
        dependency_record(
            "encoder_model",
            status="healthy" if router is not None else "degraded",
            detail=ENCODER_NAME,
            required=False,
            last_checked_at=checked_at,
        ),
    ]
    return build_health_snapshot(
        service=SERVICE_NAME,
        version=app.version,
        auth_class="internal_only",
        dependencies=dependencies,
        started_at=SERVICE_STARTED_AT,
        actions_allowed=[],
        route_count=len(routes),
        encoder=ENCODER_NAME,
    )


class ClassifyRequest(BaseModel):
    text: str


@app.get("/health")
def health():
    snapshot = build_semantic_router_health_snapshot()
    snapshot["routes"] = len(routes)
    return snapshot


@app.post("/classify")
def classify(req: ClassifyRequest):
    if router is None or not router.index.is_ready():
        raise HTTPException(status_code=503, detail="Semantic router index is not ready")
    result = router(req.text)
    return {
        "text": req.text,
        "route": result.name if result.name else "cloud_safe",
        "score": None,
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8060)
