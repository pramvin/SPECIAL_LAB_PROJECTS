# Frontend Requirements — PlanWise AI Prototype

> Working document. Scope follows `../OVERVIEW.md`. Items marked **TBD /
> Usulan / Kandidat / Open point** are **not approved** and must not be
> treated as final decisions.

## 1. Purpose & stage

Frontend-only prototype of **An Intelligent Personalized Agent for Individual
Financial Planning**. The web app renders synthetic example data and validates
layout, navigation, states, and the trust/provenance model. No backend, no API
contract, no real accounts.

- **Locale/currency:** English, USD (team decision for this prototype).
- **Account model:** Demo mode only. Single synthetic profile, no auth.
- **Platform:** Responsive web (desktop sidebar layout; mobile top bar + bottom
  tab navigation). Single link, adaptive by viewport.
- **Data:** Manual/synthetic only, visibly labeled. Bank connections excluded.

## 2. Routes

| Route | Screen | Status |
|---|---|---|
| `/` | Dashboard — Financial Overview | Implemented |
| `/goals` | Financial Goals (+ create/simulate drawer) | Implemented |
| `/assistant` | Plan & Assistant workspace | Implemented |
| `/settings` | Settings & Privacy | Basic; flagged TBD (no Stitch mock) |

Route group `src/app/(app)/` applies the responsive `AppShell`.

## 3. Screen requirements

### 3.1 Dashboard
- Prototype notice banner and input-completeness banner (75%, 2 items).
- Portfolio snapshot header with source bar, mask action, and audit label.
- Four metric cards: Net Worth, Monthly Cash Surplus, Emergency Reserve, DTI.
- Agent observation card (AI draft) with inspectable assumptions.
- Completeness & Sources checklist with a "Needs Review" state.
- Active goals summary and a Strategy card.
- Regulatory / non-advisory notice footer.

### 3.2 Goals
- Header with total saved, tabs (Active / Paused / Archived), Create Goal.
- Portfolio velocity + combined target + aggregate funded summary band.
- Goal cards: progress ring, current/target, monthly contribution, target date,
  status (On Track / Behind), and a rebalance recommendation when behind.
- Incomplete custom-goal draft card with per-step completion.
- Create-goal drawer with **validation** (target amount must exceed initial
  deposit) and a calculation-source disclosure.
- Advisory guideline card (illustrative, not personalized advice).

### 3.3 Assistant
- Header disclaimer (not certified financial advice).
- Scenario bar + New / Export / Clear actions.
- Suggested analytical inquiries.
- Transcript: user bubble + generated-guidance card containing verification
  badge, headline, stats, assumptions & data sources, caveat, rationale, and
  Apply / Challenge actions.
- Synthesizing state and a composer with safety notice.
- Right rail: Model Inputs (live parameters) and Goal Target Summary with a
  portfolio-impact chart.

### 3.4 Settings & Privacy
- Profile summary (synthetic).
- Privacy controls; unsupported items visibly marked **TBD** and inert.
- Data-provenance legend.
- Open points list (auth, bank feeds, retention/consent, AI boundaries).

## 4. Cross-cutting requirements

- **Provenance:** every figure carries a badge — User Input, AI Guidance with
  Assumptions, Example Data, or Needs Review (OVERVIEW.md §7).
- **States:** loading / empty / error / success patterns for data surfaces
  (empty tab state and drawer validation implemented; others documented).
- **Responsive:** mobile `< 768px`, tablet `768–1024px`, desktop `> 1024px`.
- **Accessibility:** semantic landmarks, `aria-*` on roles/switches/tabs,
  visible focus rings (WCAG 2.2 AA target).
- **Numerics:** tabular figures on all financial values.
- **No fabricated claims:** no encryption/deletion/AI-training claims until the
  system and copy are confirmed.

## 5. Design system

Sovereign Sanctuary tokens in `src/app/globals.css` (Tailwind v4 `@theme`):
colors, radii, named spacing, and typography mirror the Stitch exports.
Fonts: Manrope (headings/metrics), Inter (body), JetBrains Mono (labels).
Charts: dependency-free SVG (`LineChart`).

## 6. Acceptance criteria

- [x] All four routes render at mobile / tablet / desktop widths.
- [x] Navigation reflects the active route (sidebar + bottom tabs).
- [x] Every displayed figure is labeled example/provenance data.
- [x] Goal create form shows a validation error and cannot save while invalid.
- [x] `npx tsc --noEmit` passes.
- [x] `npm run lint` passes with no errors/warnings.
- [x] `npm run build` succeeds.

## 7. Open points (TBD — do not implement without a decision)

1. Primary user, country/region, and locale beyond the prototype's USD/en.
2. Whether the product is account-based or demo-only long term.
3. Financial metrics shown and who owns/tests the formulas (backend).
4. Goal fields, progress rules, and categories.
5. Whether the conversational assistant is a core product feature and its
   guidance boundaries.
6. Privacy, retention, deletion, and consent requirements.
7. Brand, supported browsers, and accessibility target level.
8. Real authentication and data persistence.
