<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

# PlanWise AI — Agent Guide

Read `../OVERVIEW.md` (product direction) and `frontend-requirements.md` (screen
scope + acceptance criteria) before changing screens or flows. This is a
**prototype** on mock data. A minimal auth + investor-profile backend lives in `../Backend` (see its README); dashboard data is still mock.

## Commands

Run from `frontend/`:

- `npm run dev` — start the dev server (http://localhost:3000)
- `npm run build` — production build (must pass before finishing a task)
- `npm run lint` — ESLint
- `npx tsc --noEmit` — typecheck

There is no test runner configured yet. If tests are added, document them here.

## Hard rules (from OVERVIEW.md §7 and §9)

1. Treat **Usulan / TBD / Kandidat / Open point** as unapproved. Never silently
   promote them into product decisions.
2. Do not invent balances, formulas, data sources, or recommendation reasons.
   All figures must be synthetic and **visibly labeled** (Example Data /
   provenance badge).
3. Do not add bank connections, payments, trading, or external data flows.
4. Never store secrets/API keys in frontend code or send data to services the
   team has not chosen.
5. Keep the view separate from data sources and domain rules so mock data can be
   swapped for an API without rewriting the UI.

## Architecture

- `src/app/` — App Router. Route group `(app)/` wraps pages in the responsive
  `AppShell` (desktop sidebar + header; mobile top bar + bottom nav).
- `src/components/ui/` — reusable primitives (Button, Card, Field, Toggle,
  ProgressBar, RingProgress, LineChart, ProvenanceBadge, NoticeBanner, Icon).
- `src/components/{dashboard,goals,assistant,settings}/` — feature views.
- `src/lib/data/` — mock data modules (the only source of figures).
- `src/lib/format.ts` — currency/percent/date helpers. Keep isolated.
- `src/app/globals.css` — "Sovereign Sanctuary" design tokens (Tailwind v4
  `@theme`). Token names mirror the Stitch HTML exports.

## Conventions

- TypeScript + Tailwind utility classes; no component library.
- Charts are hand-built SVG (`LineChart`) — avoid chart dependencies.
- Apply `tabular-nums` to financial figures.
- Every figure gets a `ProvenanceBadge` (input / ai / example / warning).
- Keep accessibility basics: semantic elements, `aria-*` on custom controls,
  visible focus (already global in `globals.css`).
- Use `@/` import alias.

## When team decisions change

Update `frontend-requirements.md` and/or `../OVERVIEW.md`; do not remove TBD
markers until a decision is actually made.
