"""Laya inference server. Runs on Kaggle (NOT on the developer's computer), behind a Cloudflare tunnel.

POST /analyze  (Authorization: Bearer $LAYA_TOKEN)  {"headlines": [...]}
GET  /health   (no auth)
"""
import hmac
import os
import threading

os.environ.setdefault("USE_TF", "0")  # model card: avoids a TensorFlow deadlock when loading Laya

import laya
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

TOKEN = os.environ["LAYA_TOKEN"]
MODEL = os.environ.get("LAYA_MODEL", "convaiinnovations/laya")
agent = laya.load(MODEL)
lock = threading.Lock()  # one prediction at a time

QUESTIONS = {
    "sentiment": {
        "type": "choice",
        "instructions": "What is the likely effect of this financial news on the stock price?",
        "criteria": {
            "bearish": "negative for the stock price",
            "bullish": "positive for the stock price",
            "neutral": "no clear effect, or purely informational",
        },
    },
    "kind": {
        "type": "choice",
        "instructions": "Is this headline a concrete company event, or generic filler?",
        "criteria": {
            "event": "reports a concrete event: earnings, guidance, a deal, a rating change, a product or legal or regulatory action involving the company",
            "filler": "generic explainer, stock-quote page, promotion, or fund-holding boilerplate",
        },
    },
}


class Req(BaseModel):
    headlines: list[str] = Field(max_length=200)


app = FastAPI(title="Laya server")


@app.get("/health")
def health():
    return {"ok": True, "model": MODEL}


@app.post("/analyze")
def analyze(req: Req, authorization: str | None = Header(default=None)):
    if not authorization or not hmac.compare_digest(authorization, f"Bearer {TOKEN}"):
        raise HTTPException(401, "bad token")
    results = []
    with lock:
        for h in req.headlines:
            a = agent.predict(h[:500], QUESTIONS)["answers"]
            results.append({
                "sentiment": a["sentiment"]["choice"],
                "sentiment_probs": a["sentiment"]["probabilities"],
                "kind": a["kind"]["choice"],
                "kind_probs": a["kind"]["probabilities"],
            })
    return {"model": MODEL, "results": results}
