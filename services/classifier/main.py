"""Qwen3Guard Content Classifier Service v2
Uses proper chat template for classification.
Port: 8740 on DEV
"""
import os
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import torch

app = FastAPI(title="Qwen3Guard Classifier", version="0.2.0")

MODEL_PATH = os.environ.get("GUARD_MODEL_PATH", os.path.expanduser("~/models/qwen3guard-gen"))

classifier_pipe = None

class ClassifyRequest(BaseModel):
    text: str

class ClassifyResponse(BaseModel):
    classification: str
    category: str
    confidence: float
    route: str

@app.on_event("startup")
async def load_model():
    global classifier_pipe
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        torch_dtype=torch.float32,
        device_map="cpu",
        trust_remote_code=True
    )
    model.eval()
    classifier_pipe = pipeline("text-generation", model=model, tokenizer=tokenizer, device="cpu")

@app.get("/health")
async def health():
    return {"status": "ok", "model_loaded": classifier_pipe is not None, "version": "0.2.0"}

@app.post("/classify", response_model=ClassifyResponse)
async def classify(req: ClassifyRequest):
    if classifier_pipe is None:
        return ClassifyResponse(classification="safe", category="none", confidence=0.0, route="cloud")
    
    # Use chat template (Qwen3Guard expects user message format)
    messages = [{"role": "user", "content": req.text}]
    
    result = classifier_pipe(
        messages,
        max_new_tokens=50,
        do_sample=False,
        return_full_text=False
    )
    
    response = result[0]["generated_text"].strip().lower() if result else ""
    
    # Parse guard output
    if "unsafe" in response:
        # Try to extract category
        category = "general"
        for cat in ["violence", "sexual", "hate", "self-harm", "illegal", "privacy"]:
            if cat in response:
                category = cat
                break
        return ClassifyResponse(
            classification="unsafe",
            category=category,
            confidence=0.9,
            route="sovereign"
        )
    elif "controvers" in response:
        return ClassifyResponse(
            classification="controversial",
            category="sensitive",
            confidence=0.7,
            route="caution"
        )
    else:
        return ClassifyResponse(
            classification="safe",
            category="none",
            confidence=0.9,
            route="cloud"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8740)
