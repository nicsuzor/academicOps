---
title: Planning Web — Theme-Specific Design Guide
type: spec
status: draft
tier: ux
depends_on: [planning-web-spec]
tags: [spec, planning-web, themes, visual-design, operator, holographic]
created: 2026-03-08
---

# Planning Web — Theme-Specific Design Guide

Translates the functional spec into visual and interaction design for the **Operator** and **Holographic** themes.

See: `specs/planning-web-spec.md` for functional requirements.

---

## 1. Global Navigation & Layout

**ADHD Principle:** *Zero-friction, clear boundaries.*

| Aspect      | Operator (Flight Deck)                                                              | Holographic (Industrial Cyber-Zen)                                               |
| ----------- | ----------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| Layout      | Rigid 3-column Bento grid. Persistent sidebar.                                      | Translucent floating panels. Depth (z-axis) creates separation. No hard borders. |
| Atmosphere  | Deep void black (`#0A0A0A`), Terminal Amber (`#FFB000`) accents. Scanline overlay.  | Glassmorphic panels, 16px backdrop blur. Cyan Neon (`#00F0FF`). Deep-space bg.   |
| Navigation  | Vertical icon strip, 12px monospaced uppercase labels. Active: Amber bg, black text. | Floating glass drawer. Active: Cyan glow border, chromatic aberration on hover.  |

---

## 2. Focus View

**ADHD Principle:** *Scannable, not studyable. Cap at 5.*

| Element        | Operator                                                                    | Holographic                                                              |
| -------------- | --------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| Card design    | 1px solid Amber border, sharp corners.                                      | `rgba(255,255,255,0.05)` fill, 4px radius, subtle cyan outer glow.       |
| P0 badge       | Solid red block, black text.                                                | Neon red glowing pill.                                                   |
| Downstream wt. | "Load" percentage in corner.                                                | Pulse frequency (more critical = faster pulse).                          |
| Active signal  | Blinking block cursor next to active task title.                            | Focus "lens" effect (increased brightness/sharpness) on top 5 cards.    |

---

## 3. Graph View

**ADHD Principle:** *Graph-native. Structural nodes larger.*

### Node Encoding

| Aspect  | Shared               | Operator                                                    | Holographic                                                   |
| ------- | -------------------- | ----------------------------------------------------------- | ------------------------------------------------------------- |
| Size    | Goals 4×, Projects 2×, Epics 1.5×, Tasks 1× | Hollow squares `[]`. Goals double-bordered. High-contrast amber fill. | Glowing spheres. Goals: revolving orbital ring. Neon cyan fill. |

### Edge Encoding

| Edge type    | Operator                                             | Holographic                                       |
| ------------ | ---------------------------------------------------- | ------------------------------------------------- |
| Default      | ASCII-style connectors (`\|`, `-`, `+`).             | Gaussian blurred light trails.                    |
| `depends_on` | Thick dashed red line.                               | "Hot" white-orange laser beam.                    |

---

## 4. Epic Tree View

**ADHD Principle:** *Collapsible density. Nothing lost.*

| Element   | Operator                                          | Holographic                                                        |
| --------- | ------------------------------------------------- | ------------------------------------------------------------------ |
| Structure | Classic CLI tree (`├──`).                         | Nested glass folders with soft depth shadows.                      |
| Progress  | ASCII bars `[####----] 50%`.                      | Thin neon lines with "liquid fill" animation on subtask completion. |
| Icons     | Bootstrap Icons, 1-bit style (no gradients).      | Glowing, semi-transparent; brighten on hover.                      |

---

## 5. Dashboard

**ADHD Principle:** *Dropped threads first.*

### Where You Left Off

| Operator                                                             | Holographic                                                            |
| -------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| "REENTRY POINT" in bold amber. Cards look like terminal output blocks. | "DROPPED THREAD" in neon pink. Cards "hover" higher to grab attention. |

### Focus Synthesis

| Operator                                               | Holographic                                                      |
| ------------------------------------------------------ | ---------------------------------------------------------------- |
| "SYSTEM REPORT" with monospaced bullet points.         | Holographic projection effect, flickering text, 0.8 opacity.    |

---

## 6. Node Detail View

**ADHD Principle:** *Progressive disclosure.*

| Element | Operator                                                     | Holographic                                                          |
| ------- | ------------------------------------------------------------ | -------------------------------------------------------------------- |
| Layout  | Split-pane with vertical divider.                            | Centered modal. Background "The Void" blurred to 40px.               |
| Actions | Large boxed buttons `[ COMPLETE ]`, invert on hover.         | Floating wireframe buttons that "materialise" (fill with colour) on hover. |

---

## 7. Batch Operations

**ADHD Principle:** *Support focus transitions.*

| Operator                                                                         | Holographic                                                                   |
| -------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| Persistent "COMMAND BAR" at bottom: `> 5 ITEMS SELECTED: [REPARENT] [ARCHIVE]`. | Floating "ACTION ORB" near cursor, appears when multiple items lasso-selected. |
