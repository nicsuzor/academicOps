---
title: Icon Integration Guide
type: reference
category: ref
permalink: excalidraw-icon-integration
description: Add professional iconography to Excalidraw diagrams using Material Symbols and existing libraries.
---

# Icon Integration Guide

**Purpose**: Add professional iconography to Excalidraw diagrams using Material Symbols and existing libraries.

---

## Available Icon Sources

### 1. Built-in Excalidraw Libraries (READY TO USE)

Located in: `~/.claude/skills/excalidraw/libraries/`

**awesome-icons.excalidrawlib** (107 KB):
- General purpose icons
- Social media, UI elements, common symbols
- Good for: Task indicators, status badges, general purpose

**data-viz.excalidrawlib** (942 KB):
- Charts, graphs, data visualization elements
- Good for: Analytics dashboards, metrics displays

**data-processing.excalidrawlib** (591 KB):
- Database symbols, processing flows, data pipelines
- Good for: System architecture, data flows

**stick-figures.excalidrawlib** (93 KB):
- Human figures, basic poses
- Good for: User personas, actors in workflows

**stick-figures-collaboration.excalidrawlib** (287 KB):
- People working together, interactions
- Good for: Team workflows, collaboration diagrams

**hearts.excalidrawlib** (52 KB):
- Heart variations
- Good for: Favorites, likes, emotional indicators

### 2. Material Symbols (RECOMMENDED FOR NEW ICONS)

**Why Material Symbols**:
- Clean, professional, consistent design
- Massive library (2,500+ icons)
- Three variants: Outlined (recommended), Rounded, Sharp
- Perfect match for terminal/modern aesthetic
- Free from Google Fonts

**Access**:
- Web: https://fonts.google.com/icons
- Direct download: https://github.com/google/material-design-icons

**Integration workflow**: See "Adding Material Symbols to Excalidraw" below.

### 3. Font Awesome (ALTERNATIVE)

**Why Font Awesome**:
- Extremely popular, 2,000+ icons
- Good ecosystem support
- Free tier available

**Access**:
- Web: https://fontawesome.com/icons
- CDN or download available

**Note**: Material Symbols preferred for consistency with existing tools.

---

## Loading Built-in Libraries into Excalidraw

### Method 1: Via Obsidian Plugin

If using Obsidian Excalidraw plugin:

1. Open Excalidraw drawing
2. Click library icon (bottom right)
3. Click "Load library from file"
4. Navigate to: `~/.claude/skills/excalidraw/libraries/`
5. Select desired `.excalidrawlib` file
6. Icons now available in library panel

### Method 2: Via Excalidraw Web App

1. Open excalidraw.com
2. Click library icon (left sidebar)
3. Click three-dot menu → "Import library"
4. Upload file from: `~/.claude/skills/excalidraw/libraries/`
5. Library loads into current session

### Method 3: Programmatic (for agents)

When generating Excalidraw JSON programmatically:

```python
# Read library file
with open('~/.claude/skills/excalidraw/libraries/awesome-icons.excalidrawlib') as f:
    library_data = json.load(f)

# Extract desired icon element
icon_element = library_data['libraryItems'][index]  # Choose appropriate index

# Add to your diagram's elements array
diagram['elements'].append(icon_element)

# Update position, colors, size as needed
icon_element['x'] = your_x_position
icon_element['y'] = your_y_position
icon_element['strokeColor'] = '#c9b458'  # Recolor to theme
```

---

## Adding Material Symbols to Excalidraw

### Step 1: Find Your Icon

1. Visit: https://fonts.google.com/icons
2. Search for desired icon (e.g., "task", "check_circle", "warning")
3. Select icon variant:
   - **Outlined** (recommended): Clean, professional
   - **Rounded**: Softer, friendlier
   - **Sharp**: Angular, modern
4. Click icon to open detail view

### Step 2: Download as SVG

1. Click "Download" button (or export icon)
2. Configure settings:
   - Format: SVG
   - Size: 24dp (default, will scale in Excalidraw)
   - Color: Black (will recolor in Excalidraw)
3. Save SVG file

### Step 3: Import into Excalidraw

**Via Excalidraw web app**:
1. Open excalidraw.com
2. Drag and drop SVG file onto canvas
3. Icon imports as editable SVG group

**Via Obsidian plugin**:
1. Open Excalidraw drawing in Obsidian
2. Drag SVG file from file explorer onto canvas
3. Icon imports as image or editable elements (depending on plugin version)

### Step 4: Recolor to Match Theme

After importing:
1. Select icon elements (may be grouped)
2. Change stroke color to theme palette:
   - Gold: `#c9b458` (emphasis, goals)
   - Green: `#8fbc8f` (success, active)
   - Blue: `#7a9fbf` (info, links)
   - Orange: `#ffa500` (warning)
   - Red: `#ff6666` (error, blocked)
3. Adjust size to match hierarchy (scale proportionally)

### Step 5: Save to Custom Library (Optional)

To reuse themed icons:
1. Select styled icon
2. Click library icon → "Add to library"
3. Icon saved to personal library
4. Export library: Three-dot menu → "Export library"
5. Save to: `~/.claude/skills/excalidraw/libraries/custom-material-symbols.excalidrawlib`

---

## Icon Usage Guidelines

### Size & Positioning

**Icon sizes** (match text hierarchy):
- XL icons: 40-48px → Major goals, primary indicators
- L icons: 28-36px → Project markers, section headers
- M icons: 20-24px → Task status, inline indicators
- S icons: 14-18px → Labels, small annotations

**Positioning**:
- **Inline with text**: Align baseline, 8-12px gap
- **Above/beside boxes**: 6-10px margin from edge
- **Corner badges**: 4-6px inset from corner
- **Standalone**: Generous whitespace (20-30px minimum)

### Color Application (From Theme)

**Icon color mapping**:
- **Tasks/actions** → `#8fbc8f` (soft green)
- **Goals/stars** → `#c9b458` (muted gold)
- **Warnings/alerts** → `#ffa500` (orange)
- **Errors/blocks** → `#ff6666` (soft red)
- **Info/help** → `#7a9fbf` (muted blue)
- **De-emphasized** → `#888888` (dimmed gray)

**Consistency**: Same meaning = same icon + same color throughout diagram.

### Density & Restraint

**Use icons sparingly**:
- ✅ **Good**: 1-3 icons per major section
- ✅ **Good**: Icons emphasize key points
- ❌ **Bad**: Icon on every single element
- ❌ **Bad**: Mixing multiple icon styles

**Purpose**: Icons should guide attention, not create visual noise.

### Common Icon Mappings for Task Dashboards

**Status indicators**:
- Active/in-progress → `play_circle` or `pending` (green)
- Completed → `check_circle` or `task_alt` (gray/green)
- Blocked → `block` or `cancel` (red)
- Queued → `schedule` or `hourglass_top` (orange/yellow)

**Priority indicators**:
- High priority → `priority_high` or `star` (gold)
- Medium priority → `remove` or `drag_handle` (blue)
- Low priority → `expand_more` or `arrow_downward` (gray)

**Category/type indicators**:
- Goal → `flag` or `emoji_events` (gold)
- Project → `folder` or `work` (blue)
- Task → `check_box` or `assignment` (varied)
- Note → `description` or `note` (gray)

**Workflow indicators**:
- Start → `play_arrow` (green)
- Stop → `stop_circle` (red)
- Warning → `warning` or `report_problem` (orange)
- Info → `info` or `help` (blue)
- Link/relation → `link` or `arrow_forward` (neutral)

---

## Recommended Material Symbols for Task Viz

**High-value icons to download**:

```
Status:
- check_circle (completed)
- pending (in progress)
- block (blocked)
- schedule (queued)

Priority:
- priority_high
- star
- flag

Types:
- emoji_events (goal)
- folder (project)
- assignment (task)

Workflow:
- arrow_forward
- link
- warning
- info
```

**Download batch**:
1. Search "check_circle" → Download outlined SVG
2. Search "pending" → Download outlined SVG
3. Search "block" → Download outlined SVG
4. Search "schedule" → Download outlined SVG
5. Search "star" → Download outlined SVG
6. Search "flag" → Download outlined SVG

**Import workflow**:
1. Import all SVGs into Excalidraw
2. Recolor each to theme palette
3. Size appropriately (M size: 20-24px)
4. Save batch to custom library
5. Reuse across diagrams

---

## Programmatic Icon Usage (For Agents)

When generating Excalidraw JSON with icons:

```python
def create_status_icon(status, x, y):
    """Create a themed status icon element."""

    icon_colors = {
        'active': {'stroke': '#8fbc8f', 'bg': 'transparent'},
        'completed': {'stroke': '#888888', 'bg': 'transparent'},
        'blocked': {'stroke': '#ff6666', 'bg': 'transparent'},
        'queued': {'stroke': '#ffa500', 'bg': 'transparent'},
    }

    colors = icon_colors.get(status, {'stroke': '#7a9fbf', 'bg': 'transparent'})

    # Simple circle icon (can be more complex with SVG import)
    return {
        'type': 'ellipse',
        'id': generate_id(),
        'x': x,
        'y': y,
        'width': 20,
        'height': 20,
        'strokeColor': colors['stroke'],
        'backgroundColor': colors['bg'],
        'fillStyle': 'solid',
        'strokeWidth': 2,
        'roughness': 0,  # Clean circles for icons
        # ... other required Excalidraw properties
    }
```

**Better approach**: Import actual Material Symbol SVGs as complex elements using library files.

---

## Quick Start Checklist

For task-viz agent or manual diagramming:

**Before starting**:
- [ ] Load awesome-icons library (has general purpose icons ready)
- [ ] Have theme colors reference open: [[theme-colors.md]]

**Icon workflow**:
1. [ ] Identify 3-5 key concepts that need visual emphasis
2. [ ] Choose appropriate icons (from library or Material Symbols)
3. [ ] Recolor icons to theme palette
4. [ ] Size icons to match text hierarchy (M size default: 20-24px)
5. [ ] Position with consistent spacing (8-12px gaps)
6. [ ] Verify icons don't overwhelm content (visual restraint)

**Quality check**:
- [ ] Icons use theme colors (not default black)
- [ ] Icon sizes match hierarchy (XL/L/M/S)
- [ ] Consistent meaning (same icon = same concept)
- [ ] Visual density is restrained (not icon-on-everything)
- [ ] Icons enhance understanding (not just decoration)

---

## Future Enhancements

**Potential additions**:
1. Create custom Material Symbols library pre-colored with theme
2. Build automation to batch-convert and theme Material Symbols
3. Integrate Font Awesome icon set as alternative
4. Create Excalidraw plugin for direct Material Symbols browser

**Current state**: Manual import workflow functional, good enough for most use cases.

---

**Last Updated**: 2025-11-19
**Related**: [[theme-colors]], [[library-guide]]
**Icon Sources**: Material Symbols (Google), awesome-icons library (built-in)
