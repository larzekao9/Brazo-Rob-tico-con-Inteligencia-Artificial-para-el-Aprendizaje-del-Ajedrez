---
name: Neural Grandmaster
colors:
  surface: '#f8f9ff'
  surface-dim: '#cbdbf5'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d3e4fe'
  on-surface: '#0b1c30'
  on-surface-variant: '#3e4943'
  inverse-surface: '#213145'
  inverse-on-surface: '#eaf1ff'
  outline: '#6e7a73'
  outline-variant: '#bdc9c1'
  surface-tint: '#006c4c'
  primary: '#006446'
  on-primary: '#ffffff'
  primary-container: '#087f5b'
  on-primary-container: '#cfffe5'
  inverse-primary: '#78d9af'
  secondary: '#006875'
  on-secondary: '#ffffff'
  secondary-container: '#2ce6ff'
  on-secondary-container: '#00636f'
  tertiary: '#7b4d00'
  on-tertiary: '#ffffff'
  tertiary-container: '#9c6300'
  on-tertiary-container: '#fff2e7'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#94f6ca'
  primary-fixed-dim: '#78d9af'
  on-primary-fixed: '#002115'
  on-primary-fixed-variant: '#005139'
  secondary-fixed: '#9cefff'
  secondary-fixed-dim: '#01daf3'
  on-secondary-fixed: '#001f24'
  on-secondary-fixed-variant: '#004f58'
  tertiary-fixed: '#ffddb8'
  tertiary-fixed-dim: '#ffb95f'
  on-tertiary-fixed: '#2a1700'
  on-tertiary-fixed-variant: '#653e00'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  display-lg:
    fontFamily: Space Grotesk
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.03em
  display-lg-mobile:
    fontFamily: Space Grotesk
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 34px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Space Grotesk
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Space Grotesk
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 26px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Space Grotesk
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
  body-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '500'
    lineHeight: 24px
  body-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  telemetry-lg:
    fontFamily: JetBrains Mono
    fontSize: 18px
    fontWeight: '700'
    lineHeight: 22px
    letterSpacing: -0.02em
  telemetry-md:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 18px
  telemetry-sm:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.04em
  label-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 11px
    fontWeight: '700'
    lineHeight: 14px
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-sm: 0.75rem
  margin: 1rem
  margin-sm: 0.75rem
  margin-lg: 1.5rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1rem
  space-xl: 1.5rem
---

## Brand & Style

This design system establishes a high-performance fusion between classic grandmaster discipline and computational intelligence. Tailored for mobile-first chess players, coaches, and neural-engine analysts, the interface rejects the dark-mode trope of conventional deep-tech tools in favor of an ultra-clean, clinical white canvas (#ffffff / #f8fafc). This airy environment allows the mind to focus entirely on calculation, spatial intuition, and probabilistic analysis without visual fatigue.

The aesthetic philosophy balances **Clinical Precision** and **Tactile Glassmorphism**:
- **Intelligent Emerald Anchor**: Rooted in computational mastery, deliberate planning, and calm analytical execution.
- **Electric Cyan Synapses**: Dynamic accents communicate active AI calculations, engine top-choice paths, neural network evaluations, and real-time candidate move validations.
- **Precision Glass on Pure White**: Frosted, semi-translucent utility cards, tactical floating sheets, and crisp slate structural borders deliver depth without heavy, muddy shadows.
- **Tactile Feedback**: Surfaces feel calibrated and physical—crisp touch targets designed specifically for dynamic one-handed mobile play and rapid move input.

## Colors

The color architecture is built for strict hierarchical separation between structural canvas, board strategy, neural engine calculations, and game urgency:

- **Primary (`#087F5B` Emerald)**: Represents authority, accurate moves, winning positional play, and primary execution triggers. Paired with `#DFF5E9` (Soft Mint Container) for safe territory, engine agreement indicators, and passive highlights.
- **Secondary (`#00DAF3` Electric Cyan / Deep Tech)**: Represents the neural engine core. Used for AI engine recommendations, win-probability deltas, best-move arrows, synaptic analysis graphs, and live deep-scan telemetry.
- **Tertiary (`#F59E0B` Tactical Amber)**: Dedicated to streak counters, match urgency, time-trouble warnings, blunders/inaccuracies, and competitive milestone badges.
- **Neutral (`#64748B` Slate)**: Grounded, clinical slate tones ranging from `#F8FAFC` (Canvas Base) and `#FFFFFF` (Card Surfaces) to `#E2E8F0` (Structural Dividers) and `#0F172A` (Terminal Deep Slate for readable typography).
- **Surface Elevation Hierarchy**:
  - `Surface-0` (`#F8FAFC`): Base screen canvas and system background.
  - `Surface-1` (`#FFFFFF`): Primary elevated cards, evaluation sheets, and control decks.
  - `Surface-Glass` (`rgba(255, 255, 255, 0.82)`): Translucent floating controls, HUD navigation bars, and top timers with a blur backdrop.

## Typography

Typography establishes an intentional tri-font structure:

1. **Space Grotesk (Headlines & Performance Titles)**: Geometric, tech-forward, and authoritative. Gives board outcomes, phase shifts ("Opening Preparation", "Middlegame Complexity"), and player ranks an assertive computational signature.
2. **Plus Jakarta Sans (Body & Microcopy)**: Warm, ergonomically sound, and exceptionally legible on compact mobile screens. Used for opening names, move annotations, commentary cards, and interactive buttons.
3. **JetBrains Mono (Telemetry, Coordinates & Evaluation)**: Uncompromising tabular monospace precision. Strictly reserved for chess grid coordinates (`a1`–`h8`), real-time clocks (`04:59.2`), engine evaluation markers (`+2.34`, `M4`), centipawn metrics, depth readouts (`depth 34/60`), and neural tree probability percentages.

## Layout & Spacing

The layout is built for fluid touch optimization and viewport preservation on mobile devices:

- **Viewport Preservation**: The primary 8x8 chessboard claims strict 1:1 aspect ratio priority within the device horizontal safe bounds (`margin: 1rem`), remaining anchored without vertical clipping on screens as small as 375pt.
- **Rhythm & Padding**: Component spacing operates on a rigid 4px/8px micro-scale (`space-xs` to `space-xl`). Compact margins (`space-md`) within move history decks ensure that multiple variations and evaluation graphs are visible simultaneously without vertical scrolling.
- **Responsive Adaptations**:
  - **Mobile (<640px)**: Single-column vertical stack. The board occupies the primary viewport width, flanked by compact player timers above and below. Analysis engines, notation ribbons, and neural telemetry live in an interactive bottom sheet or segmented tabs.
  - **Tablet / Large Foldable (≥640px)**: Two-column master-detail grid with an 8-column board container and a 4-column real-time telemetry sidebar (`gutter: 1.5rem`).

## Elevation & Depth

This system avoids dark or dirty drop shadows, achieving physical presence through micro-borders, tinted ambient illumination, and frosted glass:

- **Level 0 (Flat Canvas)**: Pure background (`#F8FAFC`). No depth. Used for application framing and non-interactive space.
- **Level 1 (Card & Board Tile Layer)**: Crisp `#FFFFFF` surfaces bounded by a 1px solid structural border in `#E2E8F0`. Shadow is an ultra-diffused whisper: `0 2px 8px -2px rgba(15, 23, 42, 0.04)`.
- **Level 2 (Tactile Interactive & Analysis Drawers)**: Slightly lifted cards and action sheets. Supported by a dual shadow: `0 4px 16px -4px rgba(8, 127, 91, 0.06), 0 2px 4px -1px rgba(15, 23, 42, 0.03)`.
- **Level 3 (Floating HUDs & Modal Sheets)**: Premium glassmorphic layering utilizing `rgba(255, 255, 255, 0.85)` backing, `backdrop-filter: blur(16px)`, a crisp top highlight border of `1px solid rgba(255, 255, 255, 0.9)`, and an exterior rim of `1px solid rgba(226, 232, 240, 0.8)`.
- **Neural Glow / High-State Elevation**: Interactive engine targets, best-move focus tiles, and tactical check warnings use a targeted ambient aura: `0 0 16px rgba(0, 218, 243, 0.35)` for cyan engine calculations, and `0 0 16px rgba(245, 158, 11, 0.35)` for urgent amber streak states.

## Shapes

The design uses a balanced `roundedness: 2` (0.5rem base radius) to establish a clean, engineered aesthetic that avoids both harsh brutalist points and overly playful bubble geometry:

- **Base Radius (`0.5rem` / `8px`)**: Buttons, evaluation badges, notation pills, clock readouts, and text input fields.
- **Large Radius (`1rem` / `16px`)**: Tactical analysis cards, chessboard surround containers, and floating HUD toolbars.
- **Extra Large Radius (`1.5rem` / `24px`)**: Bottom sheets, modal dialogues, and evaluation bar containers.
- **Special Geometry (Chessboard)**: The outer perimeter of the 64-square grid uses `rounded-lg` (16px) with an interior border clip, while internal squares remain strictly orthogonal (0px) for spatial calculation and move accuracy.

## Components

### Buttons
- **Primary (Engine / Confirm)**: Emerald background (`#087F5B`) with high-contrast white text (`#FFFFFF`), `font-weight: 600`, 8px radius. Active state produces a subtle compression effect (`scale(0.98)`).
- **Secondary (Neural Scan / Analyze)**: Soft mint surface (`#DFF5E9`) with primary emerald text (`#087F5B`) and a 1px border in `rgba(8, 127, 91, 0.2)`.
- **Electric Accent (Deep-Tech Actions)**: Electric Cyan accent (`#00DAF3`) text over an ultra-clean white surface with a cyan border (`#00DAF3`) and a subtle cyan glow on hover/active.

### Evaluation Bar (Metric Visualizer)
- Integrated vertical or horizontal rail utilizing a split layout: crisp `#FFFFFF` for White advantage, `#0F172A` for Black advantage.
- Centered indicator badge rendering real-time metrics (`+1.8`, `-0.4`, `M3`) in `telemetry-md` (JetBrains Mono) with a 1px slate ring (`#E2E8F0`).
- Animated transition curves (cubic-bezier `0.16, 1, 0.3, 1`) ensuring fluid responsiveness to live engine depth changes.

### Chess Clocks & HUD
- Elevated white pill card (`#FFFFFF`) with a 1px slate border (`#E2E8F0`).
- Active player timer displayed in high-contrast `telemetry-lg` JetBrains Mono (`#0F172A`).
- Active turn marked by an ambient cyan pulse dot (`#00DAF3`) and an emerald side-rail border.
- Low-time condition (<30s) automatically shifts background to soft amber tint (`rgba(245, 158, 11, 0.08)`) with tertiary text (`#F59E0B`).

### Chips & Move History
- Move notation presented in horizontal scrolling ribbons: Move numbers in muted slate (`#94A3B8`), moves in crisp dark slate (`#0F172A`) using `telemetry-md`.
- Engine-classified moves feature micro-dots: Brilliant (`#00DAF3`), Best (`#087F5B`), Mistake (`#F59E0B`), Blunder (`#EF4444`).

### Input Fields & Search
- Surface: `#FFFFFF` encased in 1px `#E2E8F0` border.
- Active focus state transitions border to `#087F5B` with an outer ring in `rgba(8, 127, 91, 0.12)`.
- Placeholder text styled in `Plus Jakarta Sans` (`#94A3B8`).

### Cards & Tactical Panels
- Clean white tactile containers framed by `#E2E8F0`.
- Section headers set in `Space Grotesk` (`headline-sm`).
- Internal neural telemetry readouts (win probabilities, node depth, speed kn/s) set in `telemetry-sm` (JetBrains Mono) with slate background pills (`#F1F5F9`).