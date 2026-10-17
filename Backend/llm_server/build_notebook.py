"""Generate experiments/ollama_server_kaggle.ipynb from llm_server/proxy.py.

Run from Backend/ after editing proxy.py:  python3 llm_server/build_notebook.py
"""
import json
import os

HERE = os.path.dirname(__file__)

INTRO = """# Ollama LLM server (Kaggle + Cloudflare tunnel)

Run all cells. The last cell prints `LLM_URL`, `LLM_TOKEN` and `LLM_MODEL`, then keeps running (that keeps the link alive).
Settings: Accelerator = GPU T4 x2 (one T4 is enough for the default model), Internet = On.

Ollama listens on 127.0.0.1 only; the tunnel exposes a small proxy that requires the random token.
A new URL and token are made each time this notebook starts. Do not share this notebook's output publicly.
This is a separate notebook from `colony-models-eval`; do not paste this into that one."""

INSTALL = """import os, subprocess, time, urllib.request
MODEL = "qwen3:8b"   # change here; ~5-6 GB in VRAM at the default Q4 quantisation
subprocess.run("apt-get install -y -qq zstd pciutils lshw", shell=True, check=True)   # the Ollama installer needs zstd (not on Kaggle by default)
subprocess.run("curl -fsSL https://ollama.com/install.sh | sh", shell=True, check=True)
ollama = subprocess.Popen(["ollama", "serve"], env=dict(os.environ, OLLAMA_HOST="127.0.0.1:11434"),
                          stdout=open("ollama.log", "w"), stderr=subprocess.STDOUT)
for _ in range(60):   # `ollama pull` fails if the server is not accepting connections yet
    try:
        urllib.request.urlopen("http://127.0.0.1:11434", timeout=2)
        break
    except Exception:
        time.sleep(1)
subprocess.run(["ollama", "pull", MODEL], check=True)"""

PIP = "%pip install -q fastapi uvicorn requests"

RUN = '''import re, secrets, sys, time, urllib.request

PORT = 8766
TOKEN = secrets.token_urlsafe(24)   # new random password every run; the tunnel URL is public, this is what protects it
env = dict(os.environ, LLM_TOKEN=TOKEN, LLM_MODEL=MODEL)
server = subprocess.Popen([sys.executable, "-m", "uvicorn", "proxy:app", "--host", "127.0.0.1", "--port", str(PORT)],
                          env=env, stdout=open("proxy.log", "w"), stderr=subprocess.STDOUT)

def up(url):
    try:
        urllib.request.urlopen(url, timeout=5)
        return True
    except Exception:
        return False

t0 = time.time()
while not up(f"http://127.0.0.1:{PORT}/health"):
    if server.poll() is not None:
        print(open("proxy.log").read()[-3000:])
        raise SystemExit("proxy crashed (log above)")
    if time.time() - t0 > 120:
        raise SystemExit("proxy did not start within 2 minutes")
    time.sleep(2)

cf = "/tmp/cloudflared"
if not os.path.exists(cf):
    urllib.request.urlretrieve("https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64", cf)
    os.chmod(cf, 0o755)
tun = subprocess.Popen([cf, "tunnel", "--url", f"http://127.0.0.1:{PORT}", "--no-autoupdate"],
                       stdout=open("tunnel.log", "w"), stderr=subprocess.STDOUT)
URL = None
for _ in range(60):
    m = re.search(r"https://[a-z0-9-]+\\.trycloudflare\\.com", open("tunnel.log").read())
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
print("LLM_MODEL=" + MODEL)
print("=" * 60)
print("Put the lines in Backend/.env. Keep this cell running; stopping the notebook closes the link.")

end = time.time() + 11 * 3600
beat = 0
while time.time() < end:
    if server.poll() is not None or tun.poll() is not None or ollama.poll() is not None:
        print("a process died; restart the notebook")
        break
    time.sleep(60)
    beat += 1
    if beat % 30 == 0:
        print(f"still serving, {beat // 60}h{beat % 60:02d}m")'''


def code(src):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": src.splitlines(True)}


proxy = open(os.path.join(HERE, "proxy.py")).read()
nb = {
    "cells": [
        {"cell_type": "markdown", "metadata": {}, "source": INTRO.splitlines(True)},
        code(PIP),
        code(INSTALL),
        code("%%writefile proxy.py\n" + proxy),
        code(RUN),
    ],
    "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                 "language_info": {"name": "python"}},
    "nbformat": 4,
    "nbformat_minor": 5,
}
out = os.path.join(HERE, "..", "experiments", "ollama_server_kaggle.ipynb")
json.dump(nb, open(out, "w"), indent=1)
print("wrote", os.path.normpath(out))
