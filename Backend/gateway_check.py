"""Quick check of the 9arm gateway with the key in Backend/.env. Run: .venv/bin/python gateway_check.py"""
import time
import requests
from agents import config
from agents.llm_client import OpenAICompatLLM

config.load_env()
s = config.llm_settings()
print("model:", s["model"], "| key set:", bool(s["api_key"]))

# 1) raw request, same as curl
for i in range(2):
    t = time.time()
    r = requests.post(s["base_url"] + "/chat/completions",
                      json={"model": s["model"], "messages": [{"role": "user", "content": "Hello"}]},
                      headers={"Authorization": "Bearer " + s["api_key"]}, timeout=120)
    print(f"raw {i}: HTTP {r.status_code} in {time.time()-t:.1f}s")

# 2) through our own client class (JSON mode, system prompt, what the agents use)
llm = OpenAICompatLLM(s["base_url"], s["api_key"], s["model"])
for i in range(2):
    t = time.time()
    try:
        out = llm.chat_json("market", "Output one JSON object only.",
                            'Return {"signal":"neutral","summary":"hello"}')
        print(f"client {i}: OK in {time.time()-t:.1f}s data={out['data']} tokens={out['tokens_in']}/{out['tokens_out']}")
    except Exception as e:
        print(f"client {i}: FAIL in {time.time()-t:.1f}s {type(e).__name__}: {str(e)[:200]}")
