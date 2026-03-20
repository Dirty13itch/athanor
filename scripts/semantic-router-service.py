#!/usr/bin/env python3
"""Athanor Semantic Router — content classification for task routing (10-25ms)"""
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel
from semantic_router import Route, SemanticRouter
from semantic_router.encoders import HuggingFaceEncoder
from semantic_router.index.local import LocalIndex

# Routes for content governance
routes = [
    Route(name="cloud_safe", utterances=[
        "write a function", "refactor this code", "add unit tests", "fix this bug",
        "create a new component", "optimize this query", "add error handling",
        "implement the API endpoint", "write documentation", "review this PR",
        "explain how this works", "help me understand this concept",
        "summarize this article", "translate this text", "draft a professional email",
    ]),
    Route(name="refusal_sensitive", utterances=[
        # Explicit text generation
        "write explicit scene", "nsfw content", "adult dialogue", "sexual description",
        "write erotic story", "porn scene", "blowjob dialogue", "hardcore scene",
        "write a graphic sex scene", "explicit adult content", "erotic fiction",
        "write smut", "sexual roleplay", "dirty talk dialogue",
        "write an erotic story about", "generate adult fiction",
        "describe a sex scene between", "nude description",
        "write a steamy romance scene", "explicit sexual encounter",
        "pornographic story", "xxx rated content", "hentai script",
        "write about two people having sex", "describe intercourse",
        "orgasm description", "masturbation scene", "bondage scenario",
        # Project-specific
        "empire of broken queens", "queen profile", "EoBQ scene",
        "generate performer prompt", "write prompt for adult image",
    ]),
    Route(name="sovereign_only", utterances=[
        "scan for vulnerabilities", "pen test this server", "exploit the endpoint",
        "hack into", "bypass authentication", "crack password", "security audit",
        "find open ports", "SQL injection", "XSS attack vector",
        "write a phishing email", "create malware", "bypass content filter",
        "jailbreak the AI", "ignore your instructions", "override safety",
    ]),
    Route(name="research", utterances=[
        "research this topic", "find information about", "compare options for",
        "what are the best", "survey available tools", "deep dive into",
        "investigate alternatives", "benchmark comparison",
    ]),
    Route(name="quick_question", utterances=[
        "what is", "how do I", "explain", "what does this mean",
        "quick question", "syntax for", "how to use", "difference between",
    ]),
]

router = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global router
    encoder = HuggingFaceEncoder(name="sentence-transformers/all-MiniLM-L6-v2")
    router = SemanticRouter(encoder=encoder, routes=routes, index=LocalIndex())
    router.sync("local")
    print(f"Router ready, index.is_ready={router.index.is_ready()}")
    yield

app = FastAPI(title="Athanor Semantic Router", lifespan=lifespan)

class ClassifyRequest(BaseModel):
    text: str

@app.get("/health")
def health():
    return {"status": "ok", "routes": len(routes), "encoder": "all-MiniLM-L6-v2"}

@app.post("/classify")
def classify(req: ClassifyRequest):
    result = router(req.text)
    return {"text": req.text, "route": result.name if result.name else "cloud_safe", "score": None}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8060)
