---
name: excalidraw
description: Creating visually compelling, hand-drawn diagrams with organic mind-map layouts and accessibility-focused design.
allowed-tools: Read,Skill
version: 1.0.0
permalink: skills-excalidraw-skill
title: Excalidraw Diagram Design Skill
---

# Excalidraw Diagram Design Skill

**Purpose**: Create hand-drawn, organic diagrams that communicate clearly and feel human.

**Key principle**: Rigid, corporate diagrams fail to engage. Sloppy, hand-drawn aesthetics with spatial mind-map layouts capture attention and convey meaning effectively.

---

## Special Note: Task Visualization

**For task visualization specifically**, use the automated `task_viz.py` script instead of this skill:
```bash
uv run python skills/tasks/scripts/task_viz.py $ACA_DATA current-tasks.excalidraw
```

The script generates a complete force-directed layout of goals, projects, and tasks. Only invoke this excalidraw skill AFTER the script runs if manual refinement or customization is needed.

---

## When to Use This Skill

You **MUST use this skill to create or edit ANY excalidraw files**.

Use the excalidraw skill when:
- Creating diagrams, flowcharts, or visual explanations
- Designing system architecture visualizations
- Building concept maps or process flows
- Visualizing relationships and hierarchies
- Any task requiring visual communication

**The user expects**: Diagrams that feel hand-drawn, organic, and spatially organized like mind maps—not rigid, corporate flowcharts.

---

## Aesthetic Defaults (CRITICAL)

**Always use these settings for the hand-drawn feel**:

| Property | Value | Why |
|----------|-------|-----|
| `roughness` | `2` | Maximum sketchiness - embrace the hand-drawn aesthetic |
| `fontFamily` | `1` (Virgil/xkcd script) | Handwritten font, NOT Helvetica |
| `strokeStyle` | `"solid"` | But with high roughness looks hand-drawn |
| `fillStyle` | `"hachure"` | Sketchy hatching, not solid fills |

**Arrow style**:
- Use **curved arrows** with multiple points (click-click-click, not drag)
- Arrows must **route around** unrelated boxes, never through them
- Bind arrows to shapes (`startBinding`, `endBinding`) so they adapt when boxes move

**Layout style**:
- **NO rigid alignment** - don't align everything on vertical/horizontal axes
- **Radial/clustered positioning** - mind map in all directions, not top-to-bottom
- **Embrace asymmetry** - "randomness dressed up as creativity"
- **Use zoom for hierarchy** - big things BIG (use Excalidraw's unlimited canvas), children progressively smaller

---

## Core Visual Design Principles

### 1. Visual Hierarchy

**Identical content looks completely different based on presentation.** Position and style choices are critical.

**Create hierarchy through**:
- **Size contrast**: Titles (XL) > Subtitles (L) > Body (M) > Labels (S)
- **Color contrast**: Darker = more important, lighter = supporting
- **Spatial position**: Top/center = primary focus
- **Grouping**: Related elements clustered together
- **Weight variation**: Stroke width signals importance

**Anti-pattern**: Everything the same size/color/weight = visual chaos

**Anti-pattern**: Big blocks of text in boxes. Keep labels SHORT (1-5 words). Don't overload the user's view.

### Mind Mapping Design Principles

For mind maps and concept maps, apply four fundamental design principles: **Proximity** (group related elements), **Alignment** (consistent positioning), **Contrast** (hierarchy through visual differences), and **Repetition** (unified patterns).

**Key guidelines**: Use keywords over paragraphs, keep labels concise (1-5 words), visual over textual.

See [[references/mind-mapping-principles.md]] for complete principles and examples.

### 2. The Two-Phase Design Process

**Phase 1: Structure** (ignore aesthetics)
- Map all components and relationships
- Focus purely on accuracy and completeness
- Don't worry about positioning or visual appeal
- Challenge assumptions about connections and flow

**Phase 2: Visual Refinement** (maintain structure)
- Reposition elements for clarity and flow
- Apply consistent styling
- Create visual rhythm and balance
- Optimize whitespace and alignment

**Why this works**: Ensures diagrams are both technically correct AND visually appealing.

### 3. Whitespace is a Design Element

Whitespace (negative space) is not "empty"—it's a powerful tool for:

**Macro whitespace** (between major sections):
- Separates conceptual groups
- Creates breathing room
- Guides eye flow through the diagram
- Establishes rhythm and pacing

**Micro whitespace** (within groups):
- Spacing between text lines
- Padding around elements
- Gap between connected items
- Distance between labels and shapes

**Rule of thumb**: If it feels crowded, it IS crowded. Add more space than you think you need.

---

## Technical Elements

**Colors**: User's preferred muted terminal theme (see [[references/theme-colors.md]]) - muted gold, soft greens, blues, on **WHITE backgrounds** (NOT dark). Maintain 4.5:1 contrast ratio for accessibility.

**Typography**: XL (40-48px) titles, L (24-32px) headers, M (16-20px) body, S (12-14px) labels

**Shapes**: Rectangles (most versatile), circles (start/end/actors), diamonds (decisions), ellipses (organic feel for mind maps)

**Arrows**: Thin (1-2px) default, medium (3-4px) emphasis, **must bind to shapes**, click-click-click for multi-point. Curved arrows for organic/mind-map layouts. **Directional arrows free up positioning** - children can be placed anywhere around parent (not just below) to avoid overlap.

**Icons**: Material Symbols (recommended) or built-in libraries. Recolor to theme, use sparingly. See [[references/icon-integration.md]].

**Layout**: Prefer organic, spatial, mind-map layouts over rigid hierarchies. **Spread elements to prevent arrow overlap** - arrows are directional, so children can be positioned anywhere around parent (360° freedom). Grid snapping for precision, radial/clustered positioning for mind maps.

**Grouping**: **Always bind text to containers** using `containerId` property (programmatic) or group manually (select both → Cmd/Ctrl+G). Text should auto-size to container width. This ensures text moves WITH its box. See [[references/text-container-pattern.md]] for JSON binding pattern.

**CRITICAL - Arrow Binding**: Arrows MUST use `startBinding` and `endBinding` to anchor to boxes. This ensures arrows adapt when boxes are moved. Never create floating arrows.

See [[references/technical-details.md]] for complete specifications on colors, typography, shapes, arrows, layout, layering, and fill patterns. See [[references/theme-colors.md]] for user's preferred color palette. See [[references/text-container-pattern.md]] for text-in-container binding.

---

## Process: Creating a Professional Diagram

### Step 1: Analyze & Plan

Before opening Excalidraw:
1. What's the purpose? (explain concept, show flow, document architecture)
2. Who's the audience? (technical experts, stakeholders, general public)
3. What's the key message? (main takeaway)
4. What level of detail? (high-level vs. comprehensive)

### Step 2: Content Structure

In Excalidraw (ignore aesthetics):
1. List all components/concepts
2. Map all relationships
3. Identify hierarchy levels
4. Verify accuracy and completeness
5. Get feedback if possible

### Step 3: Visual Design

Now make it beautiful:
1. **Establish visual hierarchy**
   - Size elements by importance
   - Choose color scheme (2-4 colors max)
   - Set typography scale

2. **Create spatial organization**
   - Position for flow direction
   - Group related elements
   - Add generous whitespace
   - Align everything obsessively

3. **Apply consistent styling**
   - Same colors for same meanings
   - Same shapes for same types
   - Same arrow styles for same relationships
   - Same spacing patterns throughout

4. **Refine and polish**
   - Check alignment (select all → align)
   - Verify contrast and readability
   - Remove visual clutter
   - Test at different zoom levels

### Step 4: Export with Quality

**Export settings**:
- **Use WHITE background** (default, always preferred)
- Enable background (unless transparency needed)
- Use 2x or 3x scale for high resolution
- Choose "Embed scene" to preserve editability
- Export formally (don't screenshot)

---

## Common Patterns & Templates

### System Architecture Diagram

**Structure**:
- Layers: Frontend (top) → Backend (middle) → Data (bottom)
- Colors: Same color = same tier/responsibility
- Arrows: Show data flow, dependencies

**Visual treatment**:
- Larger boxes for complex components
- Grouped services in same color family
- Clear directional arrows
- Labels on all connections

### Process Flow

**Structure**:
- Start (circle) → Steps (rectangles) → End (circle)
- Decisions (diamonds) with Yes/No paths
- Left-to-right or top-to-bottom flow

**Visual treatment**:
- Color coding by actor/swim lane
- Dotted arrows for optional paths
- Consistent spacing between steps
- Numbered steps if sequential

### Concept Map / Mind Map (PREFERRED LAYOUT STYLE)

**Structure**:
- Central concept (LARGE, bold) - use Excalidraw's unlimited zoom
- Related concepts radially distributed in ALL directions (not just below)
- Clusters and proximity show relationships
- 2D spatial thinking, not strict trees - imagine a network/graph, not an org chart

**Visual treatment**:
- Size = importance/hierarchy (**vary dramatically** - goals 3-4× larger than tasks)
- Color = category/type (theme colors: [[references/theme-colors.md]])
- **NO text legends or key boxes** - color meaning should be obvious from context
- **NO duplicate summary sections** - information appears ONCE in its home location
- **Curved arrows** for organic, flowing feel (avoid all straight lines)
- **Asymmetric positioning** - embrace creative layouts, avoid perfect symmetry
- **Generous whitespace** - let elements breathe in 2D space
- **Icons sparingly** - use Material Symbols for emphasis ([[references/icon-integration.md]])
- `roughness: 2` and `fontFamily: 1` (Virgil) for maximum hand-drawn feel

**Anti-pattern**: Rigid top-down tree structures, perfect alignment grids, linear flows. Mind maps should feel spatial and organic, not like org charts.

**Anti-pattern**: Big text blocks explaining things. Use SHORT labels (1-5 words) and let spatial relationships convey meaning.

### Graph/Network Visualization (Goal → Project → Task Structure)

**Three-tier relationship map**: Goals → Projects → Tasks with full connectivity visualization.

**Spatial strategy** (CRITICAL):
- **360° positioning**: Tasks distributed AROUND projects (not just below) - top, bottom, left, right, diagonals
- **Prevent arrow overlap**: Spread elements with minimum 100-150px spacing
- **Directional arrows**: Arrow direction shows relationship, freeing up positioning
- **Calculate angles**: Use 30°, 45°, 60° offsets to distribute tasks radially

**Visual hierarchy**:
- Goals (largest, XL 40-48px text, muted gold)
- Projects (medium, L 24-32px text, varied theme colors)
- Active tasks (LARGE, M 16-20px, prominent colors)
- Completed tasks (SMALL, S 12-14px, gray, de-emphasized)

**Relationship visibility**:
- Show ALL connections: Goal→Project, Project→Task
- Recent completed tasks visible per project (context)
- Orphaned tasks/projects visually distinct

See [[references/graph-layouts.md]] for complete specifications, sizing guidelines, and examples. See [[references/text-container-pattern.md]] for text binding.

### Comparison Matrix

**Structure**:
- Items as rows or columns
- Criteria as opposite axis
- Visual indicators for ratings

**Visual treatment**:
- Consistent cell sizes
- Color scale for intensity
- Icons or symbols for categories
- Clear headers with contrast

---

## Component Libraries & Resources

**Built-in libraries** (`~/.claude/skills/excalidraw/libraries/`): 6 curated libraries available - awesome-icons, data-processing, data-viz, hearts, stick-figures, stick-figures-collaboration.

**Material Symbols** (RECOMMENDED for new icons): Professional icon set from Google Fonts. Import SVGs, recolor to theme palette. See [[references/icon-integration.md]] for complete workflow.

**Quick start**: Load via Excalidraw library panel → "Load library from file" → Select from `~/.claude/skills/excalidraw/libraries/`

**Usage tips**:
- **Recolor to theme** ([[references/theme-colors.md]]): Gold `#c9b458`, Green `#8fbc8f`, Blue `#7a9fbf`, Orange `#ffa500`, Red `#ff6666`
- **Use sparingly** for emphasis (1-3 icons per section)
- **Don't mix too many styles** (pick Material Symbols OR library icons, not both)
- **Size appropriately** (M size: 20-24px for most use cases)

See [[references/library-guide.md]] for library loading, [[references/icon-integration.md]] for Material Symbols integration, [[references/theme-colors.md]] for color palette.

---

## Quality Checklist

Before considering a diagram complete:

**Visual hierarchy**:
- [ ] Clear primary focus (largest/darkest/most prominent)
- [ ] Consistent sizing for same hierarchy level
- [ ] Typography follows size system (S/M/L/XL)

**Alignment & spacing**:
- [ ] All elements aligned to grid/each other
- [ ] Consistent spacing within groups
- [ ] Generous whitespace between sections
- [ ] No accidental misalignments

**Color & contrast**:
- [ ] Limited color palette (2-4 colors)
- [ ] Sufficient contrast (4.5:1 for text)
- [ ] Color used meaningfully, not randomly
- [ ] Accessible to colorblind users

**Arrows & flow**:
- [ ] No crossing arrows (unless unavoidable)
- [ ] Consistent arrow directions
- [ ] All arrows bound to elements
- [ ] Flow is obvious and unambiguous

**Polish**:
- [ ] Consistent fill patterns
- [ ] Consistent roughness level
- [ ] No orphaned elements
- [ ] Readable at intended viewing size
- [ ] Professional export (2-3x scale)

---

## Anti-Patterns to Avoid

**Visual sins**:
- ❌ Rainbow explosion (too many colors)
- ❌ Size chaos (random sizing)
- ❌ Alignment laziness (nothing lines up)
- ❌ Whitespace phobia (cramming everything)
- ❌ Arrow spaghetti (crossing paths everywhere)
- ❌ Text walls (paragraphs in shapes)
- ❌ Inconsistent styling (different fonts, colors, shapes for same purposes)

**The boring diagram**:
- ❌ All boxes same size
- ❌ All text same size
- ❌ Single color throughout
- ❌ No visual hierarchy
- ❌ Generic layout
- ❌ Zero whitespace
- ❌ No attention to alignment

**Result**: Technically accurate but visually dead. Nobody wants to look at it.

---

## Tools & Shortcuts

### Essential Keyboard Shortcuts

**Drawing**:
- `R` or `2` → Rectangle
- `D` or `3` → Diamond
- `O` or `4` → Ellipse
- `A` or `5` → Arrow
- `L` or `6` → Line
- `T` or `7` → Text
- `X` → Freedraw tool
- `E` → Eraser

**Editing**:
- `Cmd/Ctrl + D` → Duplicate
- `Cmd/Ctrl + Arrow` → Duplicate + connect with arrow
- `Shift + V/H` → Flip vertical/horizontal
- Arrow keys → Move 1px (Shift+Arrow for 5px)
- `Alt + /` → Stats for nerds (exact pixel dimensions)
- `Cmd/Ctrl + '` → Toggle grid
- `Cmd/Ctrl + G` → Group selection
- `Cmd/Ctrl + Shift + G` → Ungroup
- `Cmd/Ctrl + K` → Add link to selected element

**Selection**:
- Click drag → Select multiple
- `Cmd/Ctrl + A` → Select all
- Right-click → Context menu (align, arrange, etc.)
- `Cmd/Ctrl + Click` → Add to selection
- Hold `Shift` while resizing → Maintain aspect ratio

**Layers/Z-order**:
- `Cmd/Ctrl + ]` → Bring forward
- `Cmd/Ctrl + [` → Send backward
- `Cmd/Ctrl + Shift + ]` → Bring to front
- `Cmd/Ctrl + Shift + [` → Send to back

**View**:
- `Cmd/Ctrl + Wheel` → Zoom in/out
- `Space + Drag` → Pan canvas
- `Cmd/Ctrl + 0` → Reset zoom to 100%
- `Cmd/Ctrl + 1` → Zoom to fit all elements

### Productivity Tips (2025 Best Practices)

**Essential techniques**:
- Snapping: `Alt/Option + S` for precision alignment
- Multi-point arrows: Click-click-click (not drag) for clean paths
- Duplicate + connect: `Cmd/Ctrl + Arrow` for flowcharts
- Stats for nerds: `Alt + /` for exact pixel dimensions
- Link elements: `Cmd/Ctrl + K` for clickable diagrams

See [[references/productivity-tips.md]] for complete list of 12 productivity techniques and keyboard shortcuts.

### Browser Extensions

**Excalisave**: Save unlimited canvases locally
**Excalidraw Custom Font**: Use custom .woff2 fonts

### Visualization from Data

**Paste table → chart**:
- Copy two-column data
- Paste into Excalidraw
- Auto-generates bar/line chart
- Fully editable afterward

---

## Technical Integration

### MCP Server (Optional Advanced Feature)

For real-time canvas manipulation, see [[references/mcp-server-setup.md]].

**Use cases**:
- Programmatic diagram generation
- Live collaborative editing
- Automation workflows

**Not needed for**: Manual diagram creation, which is the primary use case.

### JSON Format (Advanced)

For direct file manipulation or automation, see [[references/json-format.md]].

**Use cases**:
- Batch processing diagrams
- Custom tooling integration
- Programmatic generation without MCP server

**Not needed for**: Standard diagram creation.

### Alternative: Mermaid Conversion

Excalidraw can import Mermaid.js diagrams and convert to hand-drawn style.

**When to use**: Quick generation of standard diagram types (flowcharts, sequence diagrams)

**Limitation**: Limited styling control, generic layouts—often needs significant manual refinement to look good.

**Recommendation**: Direct creation in Excalidraw produces better visual results.

---

## Summary

**The Goal**: Create diagrams that are both accurate AND visually compelling.

**Core Principles**:
1. **Visual hierarchy** through size, color, position
2. **Mind mapping principles**: Proximity, Alignment, Contrast, Repetition
3. **Two-phase process**: structure first, aesthetics second
4. **Whitespace** as a design element, not empty space
5. **Consistent styling** throughout (colors, sizes, spacing)
6. **Alignment obsession** for professional polish

**Remember**: Boring diagrams fail to communicate, no matter how accurate. Invest in visual design to make your ideas memorable and impactful.

**Quick wins**:
- **WHITE backgrounds ALWAYS** - muted colors on white, not dark backgrounds
- **Use theme colors** ([[references/theme-colors.md]]): Muted gold, soft greens, blues - NO bright pure colors
- Load library components or Material Symbols for visual interest
- **Prefer organic layouts**: Mind maps, spatial clusters, curved arrows - NOT rigid hierarchies
- Align elements for professional polish, but embrace asymmetry and creative positioning
- Add way more whitespace than you think you need (80-120px between clusters)
- Vary sizes significantly to create hierarchy (XL → L → M → S)
- Use radial/clustered layouts for goal → project → task visualizations
- Export at 2-3x scale
- **Icons sparingly**: 1-3 per section, recolored to theme ([[references/icon-integration.md]])

**For goal/project/task visualizations** (mind-map style):
- Central goals (largest, muted gold `#c9b458`, XL text: 40-48px)
- Projects spatially distributed around goals (medium, varied theme colors, L text: 24-32px)
- Tasks clustered near projects (size varies: LARGE for active/blocked, SMALL for completed)
  - Active tasks: M text (16-20px), soft green `#8fbc8f`, PROMINENT
  - Completed tasks: S text (12-14px), gray `#888888`, DE-EMPHASIZED
- **Curved arrows** connecting related elements (organic feel)
- Cluster related projects spatially (not in rigid rows)
- Use opacity and color to show status (blocked=red, active=green, queued=orange)
- Add icons for status indicators (check_circle, pending, block) from Material Symbols
