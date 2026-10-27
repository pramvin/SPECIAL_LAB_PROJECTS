# PlanWise AI

An Intelligent Personalized Agent for Individual Financial Planning — a
responsive frontend prototype built with Next.js, TypeScript, and Tailwind CSS.

## Live app

**https://div-royalty-html-populations.trycloudflare.com**

> This link is served through a temporary Cloudflare Quick Tunnel. It has no
> uptime guarantee and the URL changes whenever the tunnel restarts. For a
> stable local URL, see [Run locally](#run-locally).

## What this is

A frontend-only prototype that turns a user's financial information and goals
into a clearer overview and reviewable next steps. It uses **synthetic example
data only** — no backend, no real accounts, and no financial advice.

Screens:

- **Dashboard** — financial overview, metrics, completeness, agent observation
- **Goals** — goal progress, status, and a create/simulate drawer
- **Assistant** — plan & assistant workspace with visible assumptions
- **Settings & Privacy** — demo-mode controls and data-provenance legend

Every figure is labeled with its provenance (User Input, AI Guidance with
Assumptions, Example Data, or Needs Review). See
[`frontend/frontend-requirements.md`](frontend/frontend-requirements.md) and
[`OVERVIEW.md`](OVERVIEW.md) for scope and open decisions.

## Run locally

```bash
cd frontend
npm install      # first time only
npm run dev
```

Open http://localhost:3000.

## Other commands

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
- Dependency-free SVG charts
- Mock data isolated under `frontend/src/lib/data/`

## Status

Early prototype. Items marked **TBD / Proposed** in `OVERVIEW.md` are not final
product decisions.
