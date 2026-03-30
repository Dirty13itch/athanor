"""Qwen3Guard Content Classifier Service v2
Uses proper chat template for classification.
Port: 8740 on DEV
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from pydantic import BaseModel

SERVICE_STARTED_AT = datetime.now(timezone.utc).isoformat()

MODEL_PATH = os.environ.get("GUARD_MODEL_PATH", os.path.expanduser("~/models/qwen3guard-gen"))

classifier_pipe = None
model_last_error: str | None = None
model_checked_at: str | None = None


class ClassifyRequest(BaseModel):
    text: str


class ClassifyResponse(BaseModel):
    classification: str
    category: str
    confidence: float
    route: str


def build_classifier_pipeline(model_path: str):
    from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
    import torch

    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        torch_dtype=torch.float32,
        device_map="cpu",
        trust_remote_code=True,
    )
    model.eval()
    return pipeline("text-generation", model=model, tokenizer=tokenizer, device="cpu")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global classifier_pipe, model_last_error, model_checked_at
    model_checked_at = datetime.now(timezone.utc).isoformat()
    try:
        classifier_pipe = build_classifier_pipeline(MODEL_PATH)
        model_last_error = None
    except Exception as exc:
        classifier_pipe = None
        model_last_error = str(exc)
    try:
        yield
    finally:
        classifier_pipe = None


app = FastAPI(title="Qwen3Guard Classifier", version="0.2.0", lifespan=lifespan)


@app.get("/health")
async def health():
    model_loaded = classifier_pipe is not None
    return {
        "service": "classifier",
        "version": app.version,
        "status": "healthy" if model_loaded else "degraded",
        "auth_class": "read-only",
        "dependencies": [
            {
                "id": "guard-model",
                "status": "healthy" if model_loaded else "down",
                "required": True,
                "last_checked_at": model_checked_at or SERVICE_STARTED_AT,
                "detail": f"loaded from {MODEL_PATH}" if model_loaded else (model_last_error or f"failed to load {MODEL_PATH}"),
            }
        ],
        "last_error": None if model_loaded else model_last_error,
        "started_at": SERVICE_STARTED_AT,
        "actions_allowed": [],
        "model_loaded": model_loaded,
    }


@app.post("/classify", response_model=ClassifyResponse)
async def classify(req: ClassifyRequest):
    if classifier_pipe is None:
        return ClassifyResponse(classification="safe", category="none", confidence=0.0, route="cloud")

    messages = [{"role": "user", "content": req.text}]

    result = classifier_pipe(
        messages,
        max_new_tokens=50,
        do_sample=False,
        return_full_text=False,
    )

    response = result[0]["generated_text"].strip().lower() if result else ""

    if "unsafe" in response:
        category = "general"
        for cat in ["violence", "sexual", "hate", "self-harm", "illegal", "privacy"]:
            if cat in response:
                category = cat
                break
        return ClassifyResponse(
            classification="unsafe",
            category=category,
            confidence=0.9,
            route="sovereign",
        )
    if "controvers" in response:
        return ClassifyResponse(
            classification="controversial",
            category="sensitive",
            confidence=0.7,
            route="caution",
        )
    return ClassifyResponse(
        classification="safe",
        category="none",
        confidence=0.9,
        route="cloud",
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8740)
