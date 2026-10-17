# OVERVIEW — An Intelligent Personalized Agent for Individual Financial Planning

> **Working Draft (Subject to Change).** This document provides an overview of the initial project ideas and directions for the team and Opencode. Features, priorities, and technology stack labeled as **Proposed** are not final decisions yet. Update the relevant sections once the results of team discussions are available.

## 1. Executive Summary

**An Intelligent Personalized Agent for Individual Financial Planning** is a product concept designed to help individuals understand their financial condition, set goals, and receive tailored planning guidance based on the information they provide.

The proposed user experience combines a financial overview dashboard, goal management, next-step plans, and—if approved by the team—a conversational assistant. The system must explain the underlying information or assumptions behind its guidance. Users remain in full control to review, correct, or ignore any recommendations.

**One-sentence version:** A personal financial planning application that helps users transform their financial information and goals into a clearer picture with easy-to-review actionable steps.

## 2. Project Status & Information

### What Is Known

- Project name/concept: **An Intelligent Personalized Agent For Individual Financial Planning**.
- The team is currently discussing which features to include.
- Initial development begins on the frontend: designs are created using Stitch AI and implemented with the assistance of Opencode.
- This document serves as an initial overview, not an approved final specification.

### Proposals Requiring Confirmation

- **Primary Users:** Individuals who want to understand their finances and manage one or more financial goals.
- **Initial Platform:** Responsive web application, not a native iOS/Android app.
- **MVP Focus:** Dashboard, financial goals, a minimal input/onboarding flow, and a plan view or assistant if deemed a core project feature.
- **Financial Calculations:** Owned and processed by the backend/domain logic and reviewed by the team; the frontend only renders results and assists with input validation, rather than serving as the source of truth for calculations.
- **Initial Data Source:** Likely manual input or clearly labeled demo data. Financial account integrations are not assumed.

### Undecided Items

Target audience and country/region; currency; displayed financial metrics; calculation formulas; final feature set; boundaries of AI guidance; authentication; privacy/data retention; branding; and final tech stack.

## 3. Problem and Opportunity — Project Hypothesis

As an initial hypothesis, many people struggle to aggregate their financial information, track progress toward goals, and determine clear next steps. This application aims to help by presenting information in a structured manner and offering actionable guidance based on available data.

This hypothesis **has not been validated through user research**. Do not treat it as research findings or add unverified marketing claims about users.

## 4. Product Goals — Proposed

1. Help users organize and understand their personal financial information.
2. Assist users in setting and tracking financial goals.
3. Provide relevant, transparent, and user-reviewable guidance.
4. Build an easy-to-understand, inclusive experience that respects the sensitivity of financial data.

Product success criteria and evaluation metrics remain to be determined with the team.

## 5. Envisioned User Experience

1. Users understand the application's purpose before being prompted for personal data.
2. Users sign in or explore a demo mode, depending on the team's decision.
3. Users configure basic preferences and enter the minimum required data for selected features.
4. The dashboard presents available information along with missing data indicators—without defaulting missing data to zero.
5. Users create or review a goal.
6. Users review a plan or interact with the conversational assistant if included in the MVP.
7. Users view system-provided explanations/assumptions, correct inputs, and decide whether to follow suggested steps.
8. Users manage preference settings and privacy controls supported by the application.

## 6. Candidate Product Areas

The following list contains **ideas for discussion**, not an approved feature backlog.

| Area | Objective | Initial Status |
|---|---|---|
| Onboarding & Preferences | Explain the product, set basic preferences, and request only necessary data. | Proposed MVP; required fields and consent TBD. |
| Dashboard | Display financial summaries, goal progress, and relevant actions. | Proposed MVP; metrics/formulas TBD. |
| Financial Goals | Create, view, and update goals. | Proposed MVP; categories and rules TBD. |
| Personalized Plan | Show recommendations/next steps with available context. | MVP Candidate; boundary rules and domain logic need approval. |
| Conversational Assistant | Allow users to ask questions and receive context-aware responses. | MVP Candidate; pending confirmation as a core feature. |
| Profile & Privacy | Manage user preferences and information controls supported by backend capabilities. | Proposed if accounts/personal data are stored. |
| Budgeting & Transactions | Track detailed expenses and financial activity. | Not included until data sources and benefits are confirmed. |
| Bank/Investment Connections | Import data directly from financial institutions. | Excluded from MVP; requires separate review and approval. |

## 7. Product Boundaries and Trust Principles

- Do not guarantee financial outcomes, returns, savings, or goal success.
- Do not fabricate balances, metrics, formulas, data sources, or rationale for recommendations.
- Clearly distinguish between **facts**, **user inputs**, **sample data**, and **AI-generated guidance**.
- If data or assumptions are missing, display an "unknown" status or request clarification; do not mask gaps with placeholder numbers.
- All figures in mockups must be clearly marked as **Sample Data** or an equivalent label.
- Avoid security/privacy claims such as "encrypted," "permanently deleted," or "not used for AI training" until system behavior and exact wording are confirmed.
- Do not include bank integrations, buying/selling financial products, payment processing, or transaction execution without explicit team approval.
- Privacy copy, disclaimers, and AI usage boundaries must be approved by the product owner and relevant stakeholders before being used as final text.

## 8. Initial Technology Recommendations

The following stack reflects initial discussions and **should not be considered a final decision**.

| Layer | Initial Recommendation | Notes |
|---|---|---|
| Frontend | **Next.js + React + TypeScript** | Suitable foundation for a scalable web app. Use reusable components and responsive design. A React + TypeScript SPA is also viable for a simpler prototype. |
| Styling/UI | Design tokens & accessible components; Tailwind CSS optional | Choose the approach the team is most familiar with. No specific UI library is mandatory. |
| Backend | **Python + FastAPI** | Initial recommendation for productivity and seamless data/AI integration. Rust can be selected if team experience or performance demands justify it. |
| Database | **PostgreSQL** | Initial recommendation for multi-user apps with structured data. MySQL is also valid. SQLite is suited for local prototyping, not as a default assumption for production. |
| Architecture | Start with a single modular backend service | Avoid microservices before a clear need arises. Critical financial calculations must have clear domain rules and test coverage. |

**Note:** For the current frontend phase, do not build backend integrations or establish unagreed API contracts. Use clearly labeled mock data that can be easily swapped for real API data later.

## 9. Guidelines for Opencode

When working on this project repository:

1. Use this file for product context and read `frontend-requirements.md` before building screens or frontend flows.
2. Treat labels like **Proposed**, **TBD**, **Candidate**, and **Open point** as unapproved items. Do not silently convert them into product decisions.
3. If technical assumptions are necessary to make the prototype functional, choose the simplest, easily replaceable options and document them in comments or documentation.
4. Do not generate fake financial formulas, advice, or personal data presented as real. Use clearly labeled synthetic data for demos.
5. Do not store secrets/API keys in frontend code or transmit data to unvetted external services.
6. Decouple UI components from data sources and domain logic so mock data can be swapped without rewriting the UI.
7. Implement reusable components, loading/empty/error/success states, responsive layouts, and basic accessibility from the start.
8. Make incremental changes: explain affected files/features, implement a small portion, and run available checks (lint, typecheck, test, or build).
9. Avoid introducing unnecessary scope, large dependencies, or external integrations without explicit justification.
10. Update this document and/or `frontend-requirements.md` whenever team decisions alter scope or direction; do not remove TBD markers prematurely.

## 10. Suggested Development Phases

### Phase 1 — Alignment & Confirmation

- Agree on target users, country/locale, MVP goals, and whether the deliverable is a prototype or functional app.
- Define required user inputs, displayed metrics, and assistant boundaries.
- Select the specific screens for the initial release.

### Phase 2 — Stitch Design

- Create primary flows and key screens, including mobile and desktop variants.
- Use placeholders and labeled sample data.
- Review navigation structure, forms, data visualizations, and UI states with the team.

### Phase 3 — Frontend Implementation

- Set up project foundation, routing, design tokens, core components, and responsive layouts.
- Implement agreed-upon screens using mock data.
- Implement input validation and UI states (loading, empty, error, and success).

### Phase 4 — Backend Integration & Testing

- Define API contracts and calculation ownership prior to integration.
- Progressively replace mock data with backend API endpoints.
- Test primary user journeys, accessibility, currency/date formatting, UI security, and responsiveness.

## 11. Key Decisions Required from the Team

Before freezing the MVP scope, the team should decide on:

1. Who is the primary user, and in which country/region will the app launch?
2. Is the immediate target a Stitch prototype, an interactive frontend prototype, or a fully backed product?
3. What data must users provide, and where does it originate?
4. Which financial metrics will be displayed, and who defines/tests the calculation logic?
5. Are financial goals a core feature? What are their required fields and progress rules?
6. Is the conversational assistant a core feature? What boundaries govern its advice?
7. Will the product require user accounts or offer a guest/demo mode?
8. What privacy, data retention, deletion, and consent requirements apply?
9. What languages, branding, currencies, browsers, and accessibility standards must be supported?

These questions can be expanded or refined following team discussions. For complete frontend requirements and acceptance criteria, refer to `frontend-requirements.md`.

---

## Document Maintenance

- Replace **Proposed** text once agreed upon by the team.
- Update status to **Decided** only when a concrete decision has been made.
- Remove rejected features or relocate them to an "Out of Scope" section.
- Record dates/versions and key decisions below to track changes over time.

### Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-10-02 | Initial draft providing project context for the team and Opencode. |