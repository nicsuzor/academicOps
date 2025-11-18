# Excalidraw: Creating Visually Compelling Diagrams

**Purpose**: Create professional, visually appealing diagrams that communicate clearly and look amazing.

**Key principle**: Boring diagrams fail to communicate. Beautiful diagrams capture attention and convey meaning effectively.

---

## When to Use This Skill

Use the excalidraw skill when:
- Creating diagrams, flowcharts, or visual explanations
- Designing system architecture visualizations
- Building concept maps or process flows
- Visualizing relationships and hierarchies
- Any task requiring visual communication

**The user expects**: Diagrams that are visually striking, well-organized, and professionally styled—not generic, boring layouts.

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

**Colors**: Open Colors system (0-9 levels), stroke darker than fill, accessibility contrast 4.5:1

**Typography**: XL (40-48px) titles, L (24-32px) headers, M (16-20px) body, S (12-14px) labels

**Shapes**: Rectangles (most versatile), circles (start/end/actors), diamonds (decisions)

**Arrows**: Thin (1-2px) default, medium (3-4px) emphasis, bind to shapes, click-click-click for multi-point

**Layout**: Alignment obsessive, grid snapping, flow directions (L-R, T-B, radial, circular)

See [[references/technical-details.md]] for complete specifications on colors, typography, shapes, arrows, layout, layering, and fill patterns.

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

### Concept Map / Mind Map

**Structure**:
- Central concept (large, bold)
- Related concepts radially arranged
- Hierarchical depth through size/distance

**Visual treatment**:
- Size = importance/hierarchy
- Color = category/type
- Labeled connections show relationships
- Strategic use of curves for organic feel

### Graph/Network Visualization (Goal → Project → Task Structure)

**Three-tier radial pattern**: Central goals (largest, saturated) → Projects radially distributed (medium, varied colors) → Tasks around projects (smallest, desaturated). Use visual state indicators for completed/outstanding tasks.

**Key techniques**: Cluster related projects spatially, vary radius for priority, balance visual weight across sectors.

See [[references/graph-layouts.md]] for complete specifications, sizing guidelines, and examples.

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

**Built-in libraries** (`skills/excalidraw/libraries/`): 6 curated libraries available - awesome-icons, data-processing, data-viz, hearts, stick-figures, stick-figures-collaboration.

**Quick start**: Load via Excalidraw library panel → "Load library from file" → Select from `skills/excalidraw/libraries/`

**Usage tips**: Recolor for consistency, use sparingly for emphasis, don't mix too many styles.

See [[references/library-guide.md]] for complete loading instructions, usage guidelines, and online library resources.

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

## Examples & Inspiration

### Study Great Diagrams

Look for diagrams that:
- Grab your attention immediately
- Communicate hierarchy clearly
- Use color purposefully
- Have generous whitespace
- Feel professionally designed

### Iterate and Improve

**First draft**: Focus on content and structure
**Second draft**: Apply visual principles
**Third draft**: Polish and refine

**Reality**: Great diagrams are rarely first attempts. Budget time for iteration.

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
- Use 2-4 colors max, purposefully
- Load library components for visual interest (6 libraries included in skill)
- Align everything obsessively (enable snapping: Alt/Option + S)
- Add way more whitespace than you think you need
- Vary sizes to create hierarchy
- Use graph/radial layouts for goal → project → task visualizations
- Export at 2-3x scale

**For goal/project/task visualizations**:
- Central goals (largest, saturated colors, XL text)
- Projects radially distributed (medium size, varied colors, L text)
- Tasks around projects (smallest, desaturated, M text)
- Cluster related projects together
- Use opacity to show completed vs outstanding tasks

**Productivity shortcuts**:
- `Cmd/Ctrl + Arrow` → Duplicate + connect with arrow
- `Alt + /` → Stats for nerds (pixel dimensions)
- `Alt/Option + S` → Toggle snapping
- Click-click-click for multi-point arrows (not click-drag)

---

**Last Updated**: 2025-11-18
**Skill Type**: Visual Communication Design
**Complexity**: Moderate (easy to start, deep mastery possible)
