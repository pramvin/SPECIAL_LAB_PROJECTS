---
name: Sovereign Sanctuary
colors:
  surface: '#faf8ff'
  surface-dim: '#d2d9f4'
  surface-bright: '#faf8ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f3ff'
  surface-container: '#eaedff'
  surface-container-high: '#e2e7ff'
  surface-container-highest: '#dae2fd'
  on-surface: '#131b2e'
  on-surface-variant: '#414844'
  inverse-surface: '#283044'
  inverse-on-surface: '#eef0ff'
  outline: '#717973'
  outline-variant: '#c1c8c2'
  surface-tint: '#3f6653'
  primary: '#012d1d'
  on-primary: '#ffffff'
  primary-container: '#1b4332'
  on-primary-container: '#86af99'
  inverse-primary: '#a5d0b9'
  secondary: '#485f84'
  on-secondary: '#ffffff'
  secondary-container: '#bbd3fd'
  on-secondary-container: '#445a7f'
  tertiary: '#002162'
  on-tertiary: '#ffffff'
  tertiary-container: '#003490'
  on-tertiary-container: '#84a3ff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#c1ecd4'
  primary-fixed-dim: '#a5d0b9'
  on-primary-fixed: '#002114'
  on-primary-fixed-variant: '#274e3d'
  secondary-fixed: '#d5e3ff'
  secondary-fixed-dim: '#b0c7f1'
  on-secondary-fixed: '#001b3c'
  on-secondary-fixed-variant: '#30476a'
  tertiary-fixed: '#dbe1ff'
  tertiary-fixed-dim: '#b4c5ff'
  on-tertiary-fixed: '#00174b'
  on-tertiary-fixed-variant: '#003ea8'
  background: '#faf8ff'
  on-background: '#131b2e'
  surface-variant: '#dae2fd'
typography:
  display-lg:
    fontFamily: Manrope
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  display-lg-mobile:
    fontFamily: Manrope
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.015em
  headline-lg:
    fontFamily: Manrope
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Manrope
    fontSize: 26px
    fontWeight: '600'
    lineHeight: 34px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Manrope
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.005em
  headline-sm:
    fontFamily: Manrope
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  title-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 22px
  body-sm:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  metric-xl:
    fontFamily: Manrope
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.02em
  metric-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 26px
  label-code:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.04em
  label-caps:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.06em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1.5rem
  gutter-mobile: 1rem
  margin: 2rem
  margin-mobile: 1rem
  margin-desktop: 3rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style
The design system articulates an aura of quiet competence, clinical financial clarity, and reassuring stability. Built for individuals and advisors navigating wealth management, forecasting, and holistic fiscal wellness, the design language deliberately shuns the frenetic, game-like saturation of consumer retail trading apps. Instead, it leans into architectural precision and quiet luxury: institutional credibility blended with human warmth.

The aesthetic merges **Corporate / Modern** precision with **Minimalist** discipline:
- **Atmosphere:** Grounded, contemplative, and unhurried. The interface communicates long-term security and calculated discernment.
- **Tone:** Methodical, transparent, and authoritative. Financial metrics never shout; they present with understated conviction.
- **Visual Weight:** Balanced density through structured data surfaces, whisper-light boundaries, and micro-interactions that reassure rather than demand immediate reaction.

## Colors
The palette is calibrated to deliver immediate psychological reassurance and strict adherence to WCAG 2.2 AA (yielding 4.5:1 for body and 3:1 for graphical interface elements).

- **Primary (`#1B4332` - Deep Forest Slate):** Represents stability, sustained growth, and financial anchor points. Used for critical primary actions, prominent balance states, and foundational brand markers.
- **Secondary (`#1D3557` - Deep Navy/Slate):** Infuses institutional authority. Serves as structural framing, deep headers, and structural controls.
- **Tertiary (`#2563EB` - Precision Cobalt):** Reserved specifically for interactive velocity: focused affordances, active navigational indicators, interactive metrics, and system feedback.
- **Neutral Foundation (`#0F172A` - Midnight Slate):** High-contrast textual baseline, supported by neutral tiers:
  - Surface Canvas: `#F8F9FA` (Soft warm porcelain)
  - Surface Substrate: `#FFFFFF` (Crisp container background)
  - Muted Borders: `#E2E8F0` (Architectural boundary line)
  - Low-Contrast Fills: `#F1F5F9` (Subtle track and badge backdrops)
  - Secondary Text: `#475569` (Slate gray at >5:1 contrast against `#FFFFFF`)

### Semantic Badging & Data Provenance Palette
To maintain absolute data integrity and provenance clarity:
- **Verified/User Input:** Background `#F0FDF4`, Border `#BBF7D0`, Text `#166534`.
- **AI Guidance with Assumptions:** Background `#EFF6FF`, Border `#BFDBFE`, Text `#1E40AF`.
- **Illustrative/Example Data:** Background `#F8FAFC`, Border `#CBD5E1`, Text `#475569`.
- **Market Critical/Warning:** Background `#FEF2F2`, Border `#FECACA`, Text `#991B1B`.

## Typography
Typographic discipline prioritizes legibility, financial scanability, and provenance attribution:
- **Numerical Regularity:** All numeric outputs, financial tables, valuations, and delta badges must apply OpenType tabular lining figures (`font-variant-numeric: tabular-nums lining-nums;`). This guarantees that balances and columnar data line up across varying viewports without visual jitter.
- **Hierarchy Structure:**
  - `Manrope` governs primary figures, headlines, and card titles, offering a modern, geometric balance with gentle humanized curves.
  - `Inter` provides utilitarian, high-legibility body copy and form inputs that remain crisp on sub-pixel rendering engines.
  - `JetBrains Mono` handles provenance tags, audit identifiers, timestamp references, and system-level calculation assumptions.

## Layout & Spacing
The layout follows a fluid-responsive 12-column architectural grid on desktop, scaling to 8 columns on tablet and 4 columns on mobile viewports.

- **Breakpoints:**
  - `mobile`: `< 768px` (4 columns, `margin-mobile: 1rem`, `gutter-mobile: 1rem`)
  - `tablet`: `768px - 1024px` (8 columns, `margin: 2rem`, `gutter: 1.5rem`)
  - `desktop`: `> 1024px` (12 columns, max-content container width `1280px`, `margin-desktop: 3rem`)

- **Rhythm & Whitespace Philosophy:** Spacing strictly adheres to an 8px cadence (interleaved with 4px micro-steps). Data tables and financial records prioritize horizontal scan lines with spacious top and bottom breathing room (`space-md` inner padding) to reduce visual cognitive fatigue during sustained analytical tasks.

## Elevation & Depth
Depth is produced through disciplined **tonal layering** paired with crisp **low-contrast outlines**, rather than aggressive skeuomorphic drops.

- **Layer 0 (Canvas Base):** `#F8F9FA`. Recessed global background canvas.
- **Layer 1 (Card & Module Surfaces):** Solid `#FFFFFF` bordered with a 1px continuous hairline of `#E2E8F0`. No ambient shadow at resting state; structural separation is driven by color value step-downs.
- **Layer 2 (Interactive Floating Elements / Popovers / Flyouts):** Solid `#FFFFFF` encased in a 1px `#CBD5E1` border, accompanied by an ultra-subtle, slate-tinted ambient shadow: `0 4px 20px -2px rgba(15, 23, 42, 0.05), 0 2px 6px -1px rgba(15, 23, 42, 0.03)`.
- **Focus Affirmation:** To meet WCAG 2.2 AA non-text contrast requirements, all interactive elements receive a sharp, outward double-ring focus state: a 2px inner gap (`#FFFFFF`) surrounded by a 2px solid active cobalt stroke (`#2563EB`). Outlines are never suppressed via `outline: none` without this replacement.

## Shapes
A tailored `Soft` architectural curvature (`roundedness: 1`) reflects geometric seriousness and corporate accountability:
- **Base Components (Inputs, Buttons, Cells):** `0.25rem` (4px). Provides sharp, dependable edges that preserve grid geometry.
- **Containers & Structured Cards (`rounded-lg`):** `0.5rem` (8px). Softens the outer containment barrier while keeping data modules tightly aligned.
- **Modals & Elevated Drawers (`rounded-xl`):** `0.75rem` (12px).
- **Provenance Badges & Pills:** Explicit full radius (`9999px`) to create an immediate shape-distinction between actionable inputs (squared) and contextual status meta-labels (pill-shaped).

## Components

### Buttons
- **Primary:** Background `#1B4332`, Text `#FFFFFF`, Border: none, Radius: `0.25rem`. Hover state transitions to `#143326`. Padding: `0.625rem 1.25rem`. Typography: `Inter` Medium 14px.
- **Secondary / Outline:** Background `transparent`, Text `#1D3557`, Border: 1px solid `#CBD5E1`. Hover: `#F1F5F9`.
- **Subtle / Ghost:** Background `transparent`, Text `#475569`. Hover: `#F8FAFC`, Text `#0F172A`.

### Provenance Badges (Data Integrity Pills)
Small pill components (`padding: 2px 10px`, radius `9999px`, font `label-code` in `JetBrains Mono` 11px uppercase) placed adjacent to calculations:
- **User Input:** `#F0FDF4` fill, `#BBF7D0` stroke, `#166534` text. Prefix icon: miniature edit glyph.
- **AI Guidance with Assumptions:** `#EFF6FF` fill, `#BFDBFE` stroke, `#1E40AF` text. Prefix icon: subtle geometric spark glyph.
- **Example Data:** `#F8FAFC` fill, `#CBD5E1` stroke, `#475569` text. Prefix icon: informational outline glyph.

### Form Inputs & Select Fields
- Base state: Height 40px, Background `#FFFFFF`, Border 1px solid `#CBD5E1`, Radius `0.25rem`, Padding `0 0.75rem`. Text `body-md` (`#0F172A`).
- Placeholder text: `#94A3B8`.
- Focus state: Border color `#2563EB`, Box-shadow `0 0 0 3px rgba(37, 99, 235, 0.15)`.
- Error state: Border color `#DC2626`, accompanied by an accessible error description below in `#DC2626`.

### Cards & Analytical Panels
- Structural framework: Background `#FFFFFF`, Border: 1px solid `#E2E8F0`, Radius `0.5rem`.
- Padding: Desktop `space-lg` (24px), Mobile `space-md` (16px).
- Sub-headers inside cards use subtle border dividers: `border-bottom: 1px solid #F1F5F9`.

### Data Lists & Financial Ledger Rows
- Layout: Alternating or clean-lined row containers with `border-bottom: 1px solid #F1F5F9`.
- Metric columns must right-align and strictly utilize `tabular-nums` for seamless vertical visual scanning.
- Interactive hover: Subtle transition to `#F8FAFC` over 120ms ease.

### Checkboxes & Radios
- Size: 18px x 18px.
- Unchecked: Border 1.5px solid `#94A3B8`, background `#FFFFFF`.
- Checked: Background `#1B4332`, Border `#1B4332`, checkmark icon in `#FFFFFF`.
- Focus ring: Outward 2px offset ring in `#2563EB`.