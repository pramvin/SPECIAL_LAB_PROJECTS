"""Token-protecting proxy in front of Ollama. Runs on Kaggle (NOT on the developer's computer).

Ollama has no authentication, so it listens on 127.0.0.1 only and this proxy is what the Cloudflare tunnel exposes.

POST /chat    (Authorization: Bearer $LLM_TOKEN)  body = Ollama /api/chat request; "stream" is forced to false
GET  /health  (no auth)
"""
import hmac
import os

import requests
from fastapi import FastAPI, Header, HTTPException, Request

TOKEN = os.environ["LLM_TOKEN"]
MODEL = os.environ.get("LLM_MODEL", "qwen3:8b")
OLLAMA = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")

app = FastAPI(title="LLM proxy")


@app.get("/health")
def health():
    return {"ok": True, "model": MODEL}


@app.post("/chat")
async def chat(request: Request, authorization: str | None = Header(default=None)):
    if not authorization or not hmac.compare_digest(authorization, f"Bearer {TOKEN}"):
        raise HTTPException(401, "bad token")
    body = await request.json()
    body["model"] = MODEL   # the server decides the model, callers cannot load others
    body["stream"] = False
    r = requests.post(f"{OLLAMA}/api/chat", json=body, timeout=600)
    if r.status_code != 200:
        raise HTTPException(502, r.text[:500])
    return r.json()
