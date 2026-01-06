---
title: Theme Colors
type: reference
category: ref
permalink: excalidraw-theme-colors
description: User's preferred color palette for Excalidraw diagrams with retro terminal aesthetic. Includes semantic colors, typography hierarchy, and integration guidelines.
---

# Theme Colors: User's Preferred Palette

**Source**: `/home/nic/src/automod/tja/dash/utils/theme.py` (Retro Terminal / Cyberpunk aesthetic)

**Design Philosophy**: Muted retro terminal aesthetic with soft, low-saturation colors. Sharp edges (no border-radius), subtle shadows, professional monospace typography.

---

## Core Color Palette

### Background & Surface Colors

```
Background (Dark):     #1a1a1a  (26, 26, 26)    - Main canvas background
Surface (Elevated):    #252525  (37, 37, 37)    - Card/box backgrounds
Border (Subtle):       #404040  (64, 64, 64)    - Borders and dividers
Border (Accent):       #333333  (51, 51, 51)    - Secondary borders
```

### Text Colors

```
Body Text:             #b8c5b8  (184, 197, 184) - Soft green-gray, primary text
Headers (Primary):     #c9b458  (201, 180, 88)  - Muted gold, H1 headers
Headers (Secondary):   #a89968  (168, 153, 104) - Dimmer gold, H2-H6 headers
Captions/Dimmed:       #888888  (136, 136, 136) - Gray for secondary text
```

### Semantic Colors

```
Success/Active:        #8fbc8f  (143, 188, 143) - Soft green (DarkSeaGreen)
Success (Bright):      #76c893  (118, 200, 147) - Brighter green accent
Info/Links:            #7a9fbf  (122, 159, 191) - Muted blue
Warning:               #c9b458  (201, 180, 88)  - Muted gold (same as H1)
Warning (Bright):      #ffa500  (255, 165, 0)   - Orange accent
Error/Danger:          #ff6666  (255, 102, 102) - Soft red
```

### Special Purpose

```
Scrollbar Active:      #008800  (0, 136, 0)     - Deep green
Code/Monospace:        #7a9fbf  (122, 159, 191) - Muted blue (for inline code)
Code Blocks:           #8fbc8f  (143, 188, 143) - Soft green (for code content)
```

---

## Excalidraw Application Guidelines

### For Mind Maps & Dashboards

**Goals** (Highest hierarchy):
- Background: `#c9b458` at 20-30% opacity (muted gold glow)
- Stroke: `#c9b458` (muted gold)
- Text: `#1a1a1a` (dark, high contrast on gold background)
- Size: XL (40-48px text)

**Projects** (Mid hierarchy):
- Background: Vary between semantic colors at 15-25% opacity:
  - Active: `#8fbc8f` (soft green)
  - Warning: `#ffa500` (orange)
  - Info: `#7a9fbf` (muted blue)
- Stroke: Darker version of background color
- Text: `#b8c5b8` (body text) or `#1a1a1a` (dark)
- Size: L (24-32px text)

**Tasks - Active/Blocked/Queued** (PROMINENT):
- Active: `#8fbc8f` background (soft green), `#76c893` stroke (brighter green)
- Blocked: `#ff6666` background (soft red), darker red stroke
- Queued: `#ffa500` background (orange), darker orange stroke
- Text: `#1a1a1a` (dark for contrast)
- Size: M (16-20px text), LARGE boxes

**Tasks - Completed** (DE-EMPHASIZED):
- Background: `#252525` (surface gray) or `#8fbc8f` at 10% opacity
- Stroke: `#404040` (subtle border)
- Text: `#888888` (dimmed caption color)
- Size: S (12-14px text), SMALL boxes

**Connections/Arrows**:
- Default: `#404040` (subtle border gray)
- Emphasis: `#8fbc8f` (soft green) or `#7a9fbf` (muted blue)
- Critical: `#ff6666` (soft red) for blockers

**Canvas Background**:
- Use: `#ffffff` (white) or transparent (PREFERRED for Excalidraw)
- NOT dark backgrounds - those are for terminal/web apps, not diagrams
- Diagrams need high contrast and printability

### Typography Hierarchy

Following excalidraw standards with user's preferred font philosophy:

**Font Family**: Excalidraw defaults (Virgil for hand-drawn, Cascadia for monospace feel)

**Size Scale**:
- XL: 40-48px → Goals, main titles
- L: 24-32px → Projects, section headers
- M: 16-20px → Active tasks, body content
- S: 12-14px → Completed tasks, labels, captions

**Text Color by Context** (on white/light canvas):
- Primary text: `#1a1a1a` (dark, high contrast)
- On colored box backgrounds: `#1a1a1a` (dark)
- De-emphasized: `#888888` (dimmed gray)
- Headers/emphasis: Dark text on gold/colored backgrounds for readability
- Note: Avoid light text colors (`#b8c5b8`) on white - use dark colors for contrast

### Contrast Guidelines (White Background)

Maintain 4.5:1 minimum contrast ratio:

✅ **Good combinations on white canvas**:
- `#1a1a1a` (dark text) on `#ffffff` (white): 19.6:1 (excellent)
- `#1a1a1a` (dark text) on `#c9b458` (gold box): 9.2:1
- `#1a1a1a` (dark text) on `#8fbc8f` (green box): 8.1:1
- `#1a1a1a` (dark text) on `#ffa500` (orange box): 7.5:1
- `#888888` (dimmed) on `#ffffff` (white): 5.6:1 (for de-emphasized only)

⚠️ **Avoid on white canvas**:
- Light text (`#b8c5b8`, `#a89968`) directly on white (too low contrast)
- Pure bright colors without opacity (use 20-40% opacity for subtle backgrounds)
- Light gray boxes with light gray text (use darker text instead)

### Color Harmony Rules

**Limit palette**: Use 4-6 colors maximum per diagram
- Background/surface: 2 shades
- Semantic states: 3-4 colors (green/blue/orange/red)
- Emphasis: 1 accent (muted gold)

**Opacity for layering**:
- Subtle background fills: 10-20% opacity
- Moderate emphasis: 20-35% opacity
- Strong presence: 40-60% opacity
- Solid (no transparency): Only when needed for maximum contrast

**Avoid**:
- Rainbow explosion (too many colors)
- High saturation fights (stick to muted palette)
- Pure colors (always use user's muted variations)

---

## Integration with Excalidraw Libraries

When using icon libraries (awesome-icons, data-viz, etc.):

**Recolor icons** to match theme:
- Primary icons: `#c9b458` (muted gold)
- Success icons: `#8fbc8f` (soft green)
- Warning icons: `#ffa500` (orange)
- Error icons: `#ff6666` (soft red)
- Info icons: `#7a9fbf` (muted blue)

**Use sparingly**: Icons should emphasize, not overwhelm. 1-3 icons per major section.

**Size appropriately**: Scale icons to match associated text hierarchy.

---

## Material Symbols Integration (Future)

**Preferred icon set**: Material Symbols Outlined (clean, professional)

**How to integrate**:
1. Export Material Symbol as SVG from Google Fonts
2. Import SVG into Excalidraw
3. Recolor using theme palette
4. Save to custom library for reuse

**Alternative**: Material Symbols Rounded (softer, friendlier feel)

**Icon color mapping**:
- Task/action icons → `#8fbc8f` (soft green)
- Warning/alert icons → `#ffa500` (orange)
- Info/help icons → `#7a9fbf` (muted blue)
- Error/block icons → `#ff6666` (soft red)
- Goal/star icons → `#c9b458` (muted gold)

---

## Quick Reference: Hex Code Cheatsheet

```
Backgrounds:  #1a1a1a, #252525
Borders:      #404040, #333333
Text:         #b8c5b8, #888888, #1a1a1a
Gold:         #c9b458, #a89968
Green:        #8fbc8f, #76c893, #008800
Blue:         #7a9fbf
Orange:       #ffa500
Red:          #ff6666
```

**Design principle**: Muted, professional, terminal-inspired. Prioritize readability and visual hierarchy over flashiness.

---

**Last Updated**: 2025-11-19
**Source**: TJA Dashboard theme (Buttermilk-inspired retro terminal aesthetic)
