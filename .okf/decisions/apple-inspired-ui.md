---
type: Decision
title: Apple-inspired light UI
description: The frontend uses an Apple-inspired light design language with a slim top navigation.
tags: [frontend, design]
status: stable
generated: { by: opencode/deepseek-flash, at: 2026-11-13T05:22:32Z }
---

# Overview

The frontend was redesigned for readability: a calmer hierarchy, clear sections, and balanced density. It is Apple-inspired, not an Apple-branded clone.

# Decision

- Light theme only for now; dark mode is deferred.
- Neutral surfaces (`#ffffff`, `#f5f5f7`), near-black text, and one blue accent (`#0071e3`).
- System UI font stack (SF Pro on macOS; Segoe UI/Roboto fallback).
- Sticky slim top navigation replaces the desktop sidebar; mobile keeps bottom tabs.
- A 1280px content container, balanced section spacing, large headings, pill buttons, and hairline borders.
- Progressive disclosure for dense data (for example, idea-card details start collapsed).
- Provenance badges, disclaimer copy, and TBD markers remain required.

# Rationale

The previous dashboard-style layout packed many labels, cards, and timestamps into each screen. The new direction prioritizes scanability and keeps technical metadata available without making it the first thing users see.

# Scope

- Applies to all active routes: Trade Ideas, Watchlist, Goals, Assistant, Settings, login, password reset, and onboarding.
- Source: `/architecture/tech-context.md` and `/project/product-context.md`.
- Design tokens live in `frontend/src/app/globals.css`.
