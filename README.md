# PlanWise AI

An Intelligent Personalized Agent for Individual Financial Planning — a
responsive frontend prototype (Next.js) with a small FastAPI backend for auth,
onboarding, and example recommendations.

## Local app

**http://localhost:3000** (after starting the backend and frontend below).

## Demo login

| Field | Value |
|---|---|
| Email | `demo@planwise.ai` |
| Password | `planwise123` |

This demo account is seeded automatically when the backend starts, so the
credential above works on a fresh database. You can also create your own account
with any valid email and a password of at least 8 characters.

> Demo only — do not reuse these credentials anywhere real.

## What this is

A prototype that turns a user's information and goals into a clearer overview
and reviewable next steps. It uses **synthetic example data only** — no real
accounts, bank connections, or financial advice.

Screens:

- **Trade ideas** — example recommendations with news and sentiment
- **Goals** — goal progress, status, and a create/simulate drawer
- **Assistant** — plan & assistant workspace with visible assumptions
- **Settings & Privacy** — demo-mode controls and data-provenance legend

Every figure is labeled with its provenance (User Input, AI Guidance with
Assumptions, Example Data, or Needs Review). See
[`frontend/frontend-requirements.md`](frontend/frontend-requirements.md) and
[`OVERVIEW.md`](OVERVIEW.md) for scope and open decisions.

## Run locally

### 1. Backend (FastAPI + SQLite)

```bash
cd Backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --port 8000
```

The frontend proxies `/api/*` to `BACKEND_URL` (default `http://127.0.0.1:8000`).
The demo account is created on first start.

To fetch the real Google News headlines used by the “News sentiment” panel:

```bash
cd Backend
.venv/bin/python -m pipeline.news
```

Sentiment labels appear only after the existing scoring step
(`.venv/bin/python -m pipeline.analyze`) runs against the Kaggle Laya/LLM
gateway. Until then the panel shows the real headlines with “not scored yet” —
it never invents labels.

### 2. Frontend (Next.js)

```bash
cd frontend
npm install      # first time only
npm run dev
```

Open http://localhost:3000. The root redirects to `/login`, then to
`/onboarding` for new accounts.

### Other frontend commands

```bash
cd frontend
npm run build    # production build
npm run start    # serve the production build
npm run lint     # ESLint
npx tsc --noEmit # typecheck
```

## Tech

- Next.js (App Router) + React + TypeScript
- Tailwind CSS v4 with the "Sovereign Sanctuary" design tokens
- FastAPI + SQLite (auth, onboarding, example recommendations)
- Dependency-free SVG charts
- Mock/example data isolated under `frontend/src/lib/data/`

## Status

Early prototype. Items marked **TBD / Proposed** in `OVERVIEW.md` are not final
product decisions.
