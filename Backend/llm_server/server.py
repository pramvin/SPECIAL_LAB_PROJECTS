"""LLM gateway. Runs on Kaggle (NOT on the developer's computer), in front of a local Ollama, behind a Cloudflare tunnel.

POST /chat    (Authorization: Bearer $LLM_TOKEN)  {"messages": [...], "format": <json schema>, "options": {...}}
GET  /health  (no auth)

Thin on purpose: prompts, schemas and validation live in Backend/pipeline/llm.py so they are versioned with the repo.
"""
import hmac
import os

import requests
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

TOKEN = os.environ["LLM_TOKEN"]
MODEL = os.environ.get("LLM_MODEL", "qwen3:8b")
OLLAMA = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")


class Req(BaseModel):
    messages: list[dict] = Field(max_length=20)
    format: dict | str | None = None   # JSON schema, or "json"
    options: dict | None = None        # e.g. {"temperature": 0, "num_ctx": 8192}
    think: bool = False                # qwen3 reasoning mode; off by default (fast, stable JSON)


app = FastAPI(title="LLM gateway")


@app.get("/health")
def health():
    return {"ok": True, "model": MODEL}


@app.post("/chat")
def chat(req: Req, authorization: str | None = Header(default=None)):
    if not authorization or not hmac.compare_digest(authorization, f"Bearer {TOKEN}"):
        raise HTTPException(401, "bad token")
    body = {"model": MODEL, "messages": req.messages, "stream": False, "think": req.think}
    if req.format:
        body["format"] = req.format
    if req.options:
        body["options"] = req.options
    r = requests.post(f"{OLLAMA}/api/chat", json=body, timeout=280)
    if r.status_code != 200:
        raise HTTPException(502, f"ollama: {r.text[:300]}")
    j = r.json()
    return {
        "model": MODEL,
        "content": j["message"]["content"],
        "tokens_in": j.get("prompt_eval_count"),
        "tokens_out": j.get("eval_count"),
    }
