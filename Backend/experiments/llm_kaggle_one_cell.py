# One cell: install Ollama, check the GPU, pull the model, start the gateway + Cloudflare tunnel.
# Generated from Backend/llm_server/server.py by the assistant. Needs: Accelerator = GPU T4, Internet = On.
import os, re, secrets, shutil, subprocess, sys, time, urllib.request

MODEL = "qwen3:8b"   # ~5-6 GB in VRAM at Q4
OLLAMA = "http://127.0.0.1:11434"

def sh(cmd):
    subprocess.run(cmd, shell=True, check=True)

sh("pip install -q fastapi uvicorn requests")
sh("apt-get update -qq && apt-get install -y -qq zstd pciutils")   # zstd: the Ollama installer needs it; pciutils: GPU detection
if subprocess.run("nvidia-smi -L", shell=True).returncode != 0:
    raise SystemExit("No GPU visible. Settings > Accelerator > GPU T4, then restart the session.")
if not shutil.which("ollama"):
    sh("curl -fsSL https://ollama.com/install.sh | sh")

def up(url):
    try:
        urllib.request.urlopen(url, timeout=5)
        return True
    except Exception:
        return False

ollama = subprocess.Popen(["ollama", "serve"], env=dict(os.environ, OLLAMA_HOST="127.0.0.1:11434"),
                          stdout=open("ollama.log", "w"), stderr=subprocess.STDOUT)
for _ in range(60):   # wait until the Ollama API answers before pulling
    if up(OLLAMA + "/api/tags"):
        break
    time.sleep(1)
else:
    print(open("ollama.log").read()[-3000:])
    raise SystemExit("ollama did not start")
sh(f"ollama pull {MODEL}")   # ~5 GB the first time

# warm-up + proof that the model sits on the GPU (PROCESSOR column should say 100% GPU)
import json
req = urllib.request.Request(OLLAMA + "/api/generate", json.dumps({"model": MODEL, "prompt": "hi", "stream": False, "think": False}).encode(),
                             {"Content-Type": "application/json"})
urllib.request.urlopen(req, timeout=300).read()
sh("ollama ps")

SERVER_CODE = r'''
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


app = FastAPI(title="LLM gateway")


@app.get("/health")
def health():
    return {"ok": True, "model": MODEL}


@app.post("/chat")
def chat(req: Req, authorization: str | None = Header(default=None)):
    if not authorization or not hmac.compare_digest(authorization, f"Bearer {TOKEN}"):
        raise HTTPException(401, "bad token")
    body = {"model": MODEL, "messages": req.messages, "stream": False, "think": False}
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
'''
open("server.py", "w").write(SERVER_CODE)

PORT = 8765
TOKEN = secrets.token_urlsafe(24)   # new random password every run; the tunnel URL is public, this is what protects it
env = dict(os.environ, LLM_TOKEN=TOKEN, LLM_MODEL=MODEL)
server = subprocess.Popen([sys.executable, "-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", str(PORT)],
                          env=env, stdout=open("server.log", "w"), stderr=subprocess.STDOUT)

def up(url):
    try:
        urllib.request.urlopen(url, timeout=5)
        return True
    except Exception:
        return False

t0 = time.time()
while not up(f"http://127.0.0.1:{PORT}/health"):
    if server.poll() is not None:
        print(open("server.log").read()[-3000:])
        raise SystemExit("LLM gateway crashed (log above)")
    if time.time() - t0 > 600:
        raise SystemExit("LLM gateway did not start within 10 minutes")
    time.sleep(3)
print(f"LLM gateway up after {time.time() - t0:.0f}s")

cf = "/tmp/cloudflared"
if not os.path.exists(cf):
    urllib.request.urlretrieve("https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64", cf)
    os.chmod(cf, 0o755)
tun = subprocess.Popen([cf, "tunnel", "--url", f"http://127.0.0.1:{PORT}", "--no-autoupdate"],
                       stdout=open("tunnel.log", "w"), stderr=subprocess.STDOUT)
URL = None
for _ in range(60):
    m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", open("tunnel.log").read())
    if m:
        URL = m.group(0)
        break
    time.sleep(2)
if not URL:
    print(open("tunnel.log").read()[-2000:])
    raise SystemExit("no tunnel URL")
for _ in range(30):   # wait until the public URL actually answers
    if up(URL + "/health"):
        break
    time.sleep(2)

print("=" * 60)
print("LLM_URL=" + URL)
print("LLM_TOKEN=" + TOKEN)
print("=" * 60)
print("Put both lines in Backend/.env. Keep this cell running; stopping the notebook closes the link.")

end = time.time() + 11 * 3600
beat = 0
while time.time() < end:
    if server.poll() is not None or tun.poll() is not None:
        print("a process died; restart the notebook")
        break
    time.sleep(60)
    beat += 1
    if beat % 30 == 0:
        print(f"still serving, {beat // 60}h{beat % 60:02d}m")