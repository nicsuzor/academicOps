# Design System: The Operator System - PRD

**Project ID:** 13602521216895540527

## 1. Visual Theme & Atmosphere

**Mood:** Utilitarian, Cyberpunk, Focus-Centric.
**Philosophy:** The "Operator System" is designed for high-density information management and rapid context recovery, specifically tailored for ADHD users. It prioritizes **scannability over studyability**. The atmosphere is that of a futuristic command center or a high-end mission control dashboard—authoritative, dense, and strictly functional. It avoids visual "fluff" in favor of rigid structures and high-contrast data readouts.

## 2. Color Palette & Roles

The system operates on two primary themes: **Operator** (Amber-led) and **Holographic** (Cyan-led), with a shared dark core.

- **Deep Void Black (#0A0A0A):** Primary workspace background. Provides a zero-distraction foundation.
- **Operator Amber (#f2aa0d):** Primary brand and action color. Used for "Tactical" views, progress bars, and critical focus items.
- **Holographic Cyan (#0de3f2):** Secondary brand color. Used for "Neural" views, network graphs, and exploration-mode interfaces.
- **Muted Command Grey (#1A1A1A):** Background for Bento grid cells and containers.
- **Matrix Green (#00FF41):** Indicates completion, success, and "Done" states.
- **Blocking Neon Pink (#FF007F):** High-alert color used exclusively for dependencies and blockers in the graph and task lists.
- **Scanline Overlay:** A subtle, persistent CRT-style scanline effect (`rgba(255, 255, 255, 0.03)`) applied over the entire viewport to reinforce the "Operator" hardware aesthetic.

## 3. Typography Rules

- **Space Grotesk:** Primary font for all Headings, Hero Numbers, and Section Titles. Its wide, geometric form provides an "airy" feel that balances the density of the UI.
- **JetBrains Mono:** Primary font for all Data Readouts, Task Lists, Terminal Outputs, and Code. Monospaced for perfect vertical alignment in dense tables.
- **Hierarchy:**
  - **Display:** Space Grotesk Bold, tracking-wide.
  - **Data:** JetBrains Mono Regular, high-contrast white or theme-color.
  - **Status:** Uppercase monospaced labels.

## 4. Component Stylings

- **Bento Grid Cells:**
  - **Shape:** Sharp, squared-off edges (`rounded-none` or `rounded-sm`).
  - **Stroke:** 1px solid borders (`#2D2D2D`).
  - **Background:** Subtle matrix grid pattern or solid `#1A1A1A`.
  - **Shadows:** None. Depth is communicated via contrast and layering, not blurs.
- **Buttons:**
  - **Primary:** Solid Amber (#f2aa0d) or Cyan (#0de3f2) background with black text. Rectangular.
  - **Secondary:** Ghost buttons with 1px theme-colored borders and monospaced labels.
- **Progress Bars:**
  - **Design:** Segmented "Segment Readouts" (e.g., `[||||||....]`) or solid 4px high bars.
  - **Animation:** Slow pulse on active items.
- **Graph Nodes:**
  - **Active:** Glowing core in the theme color.
  - **Blocked:** Pink stroke with internal cross-hatch.
  - **Done:** Dimmed matrix green.

## 5. Layout Principles

- **12-Column Rigid Grid:** The layout is strictly grid-bound to prevent cognitive load from irregular spacing.
- **Tri-Pane Architecture:**
  - **Navigation/Quick-Capture (Sidebar - Col 1-3):** Context-persistent controls.
  - **Primary Viewport (Center - Col 4-9):** The "Story," "Graph," or "List."
  - **Metrics/Detail (Right - Col 10-12):** Active task metadata and downstream weights.
- **ADHD Orientation:**
  - **Above the Fold:** "What's Running?" and "Dropped Threads" are prioritized at the top of the main scroll.
  - **Visual Triage:** Use high-contrast color coding (Pink/Amber/Green) to allow the user to "read" the dashboard state in under 5 seconds without reading text.
  - **Collapsible Density:** Information is bucketed into collapsible sections to allow the user to control the total amount of visual stimuli.
