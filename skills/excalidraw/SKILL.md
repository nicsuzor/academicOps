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

## Color Strategy

### The Open Colors System

Excalidraw uses Open Colors: 13 colors × 10 brightness levels (0-9).

**Standard usage**:
- **Level 0-1**: Canvas background (lightest)
- **Level 6-7**: Element fills (mid-range)
- **Level 9**: Strokes and outlines (darkest)

### Color Application Rules

**Stroke + Fill relationship**:
- Stroke MUST be darker than fill
- Never use fills darker than shade 3 with text
- Light fills (1-3) work with all stroke colors
- Dark strokes (8-9) provide maximum contrast

**Color for meaning**:
- **Functional grouping**: Same color family = related concepts
- **Importance**: Saturated colors = primary, desaturated = secondary
- **States**: Green = success/active, Red = error/critical, Blue = process/info, Gray = inactive
- **Layers**: Lower opacity = background context, full opacity = foreground focus

### Accessibility Considerations

**Minimum contrast requirements**:
- Text on background: 4.5:1 ratio
- UI elements: 3:1 ratio against adjacent colors

**Don't rely on color alone**:
- Use shapes to differentiate categories
- Add icons or symbols
- Include text labels
- Vary patterns (hachure vs. solid vs. cross-hatch)

**Safe color pairs**:
- Red + Blue (always contrast)
- Dark + Light versions of same color
- Avoid red-green combinations (colorblind accessibility)

### Custom Colors with Alpha

Use hex codes with alpha for sophisticated effects:
- `#FF000080` = 50% transparent red
- `#0000FF40` = 25% transparent blue
- Type "transparent" for no fill

**Transparency techniques**:
- Overlay shapes to show quantity/layering
- Create subtle background frames for grouping
- Fade supporting elements to emphasize primary content
- Layer low-opacity shapes behind high-opacity focal points

---

## Typography & Text

### Font Size Hierarchy

**Consistent sizing system**:
- **XL (40-48px)**: Main diagram title only
- **L (24-32px)**: Section headers, major component labels
- **M (16-20px)**: Standard body text, most labels
- **S (12-14px)**: Small object labels, arrow annotations, metadata

**Anti-pattern**: Random font sizes destroy visual coherence

### Text Readability Rules

1. **Backgrounds**: Only use fills ≤ shade 3 behind text
2. **Contrast**: Dark text on light fills, light text on dark fills (rarely needed)
3. **Brevity**: Concise labels > verbose explanations
4. **Alignment**: Center text in shapes, left-align multi-line text
5. **Consistency**: Same font size for same hierarchy level throughout

---

## Shape Selection & Usage

### When to Use Each Shape

**Rectangles/Squares** (most versatile):
- Processes, steps, components
- Containers and groupings
- Text blocks and annotations
- Default choice for most elements

**Circles/Ellipses**:
- Start/end points in flows
- Multiple/plural items
- Actors or entities
- Cyclical concepts

**Diamonds**:
- Decision points (use sparingly)
- Conditional branches
- Warning: text positioning is challenging

**Combined shapes**:
- Create custom forms for specific purposes
- Group primitive shapes for reusable components
- Build visual metaphors

### Aspect Ratios & Proportions

**Golden ratio** (1.618:1): Naturally pleasing rectangles

**Common useful ratios**:
- 2:1 = Wide containers, headers
- 3:2 = Balanced general-purpose boxes
- 1:1 = Equal emphasis, icons, symbols
- 16:9 = Presentation slides, artboards

**Consistency**: Use same proportions for similar element types

---

## Arrows & Connectors

### Arrow Styling

**Stroke width**:
- **Thin (1-2px)**: Default for most arrows, clean and unobtrusive
- **Medium (3-4px)**: Emphasis on critical paths
- **Thick (5-6px)**: Rarely—only for major flow emphasis

**Styles**:
- **Solid**: Standard relationships, data flow
- **Dotted**: Optional paths, weak relationships, future state
- **Dashed**: Alternative flows, return paths

**Arrow types**:
- **Standard arrows**: Directional flow, one-way relationships
- **Elbow/orthogonal**: Clean 90° angles, professional technical diagrams
- **Curved**: Show loops, cyclical processes, organic relationships
  - Avoid extreme curves (disrupts flow)
  - Strategic curves for specific concepts (spirals, cycles)

### Connector Best Practices

**Multi-point arrows**: Click-click-click (not click-drag)
- Enables precise control
- Creates cleaner paths
- Easier to adjust later

**Binding**: Always bind arrows to shapes
- Arrows move with connected elements
- Maintains relationships during rearrangement
- Hold Ctrl/Cmd to prevent auto-binding when needed

**Labels**: Double-click arrow body to add text
- Use for intermediate steps
- Annotate conditions or requirements
- Keep labels brief (3-5 words max)

**Avoid arrow chaos**:
- No crossing flows (rearrange elements instead)
- Consistent arrow directions (left-to-right, top-to-bottom)
- Group parallel arrows when showing similar relationships

---

## Layout & Spatial Organization

### Alignment is Non-Negotiable

**Use alignment tools obsessively**:
1. Select multiple elements
2. Right-click → Align options
3. Choose horizontal/vertical/distribute

**Grid & snapping** (Ctrl/Cmd + '):
- 20px minor grid (default)
- 100px major grid
- Enable object snapping (Alt/Option + S)
- Snap to anchor points for precision

**Visual balance**:
- Symmetry creates calm, stability
- Asymmetry creates energy, movement
- Choose intentionally based on purpose

### Flow Direction Patterns

**Left-to-right** (Western reading pattern):
- Sequential processes
- Timelines
- Cause-and-effect chains

**Top-to-bottom** (hierarchy/gravity):
- Organizational structures
- Decomposition diagrams
- Waterfall processes

**Radial** (hub-and-spoke):
- Central concept with related elements
- Network diagrams
- Mind maps

**Circular/cyclical** (loops):
- Iterative processes
- Feedback loops
- Life cycles

**Consistency**: Pick one primary direction per diagram

### Grouping & Proximity

**Gestalt proximity principle**: Things close together = related

**Create groups through**:
- Physical proximity (most important)
- Background boxes/frames (container concept)
- Color coding (same family = same group)
- Visual connectors (lines, brackets)

**Group hierarchy**:
- Related elements: 20-40px apart
- Separate groups: 80-120px apart
- Major sections: 150-200px apart

---

## Advanced Techniques

### Layering & Z-Index

**Layer strategy**:
- Background frames/containers: Send to back
- Primary content: Middle layers
- Labels and annotations: Bring to front

**Opacity layering**:
- Background context: 30-50% opacity, behind
- Supporting elements: 60-80% opacity, middle
- Focal points: 100% opacity, front

**Technique**: Create subtle frames at low opacity to show groupings without overwhelming

### Stats for Nerds (Alt + /)

Shows exact pixel dimensions of selected elements.

**Use for**:
- Maintaining exact proportions
- Matching sizes across elements
- Creating pixel-perfect layouts
- Debugging spacing issues

### Fill Patterns for Visual Interest

**Hachure** (hand-drawn hatching):
- Default Excalidraw aesthetic
- Organic, approachable feel
- Best for most diagrams

**Solid**:
- Clean, modern look
- Smallest file size
- Good for technical diagrams

**Cross-hatch**:
- Heavier visual weight
- Emphasis or texture
- Larger file size (use sparingly)

**Pattern consistency**: Use same pattern family throughout diagram

### Roughness & Sloppiness

**Roughness** (0-2):
- 0 = Perfectly straight lines (technical)
- 1 = Default hand-drawn feel (recommended)
- 2 = Very sketchy (informal, brainstorming)

**Consistency**: Same roughness level throughout maintains coherence

**File size**: Lower roughness = smaller files

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

### Concept Map

**Structure**:
- Central concept (large, bold)
- Related concepts radially arranged
- Hierarchical depth through size/distance

**Visual treatment**:
- Size = importance/hierarchy
- Color = category/type
- Labeled connections show relationships
- Strategic use of curves for organic feel

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

### Excalidraw Libraries

Access pre-built components at libraries.excalidraw.com:
- System design components (databases, load balancers, queues)
- Cloud architecture (AWS, Azure, GCP icons)
- Network diagrams (routers, switches, firewalls)
- UI/UX wireframe components

**Installation**: Click "Add to Excalidraw" → available in library panel

### Creating Reusable Components

**Save frequently-used elements**:
1. Design component (group multiple elements)
2. Add to library for reuse
3. Maintain consistent styling across projects

**Design systems approach**:
- Define standard shapes/sizes for common elements
- Create color palette presets
- Document spacing rules
- Build component library

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

**Editing**:
- `Cmd/Ctrl + D` → Duplicate
- `Cmd/Ctrl + Arrow` → Duplicate + connect with arrow
- `Shift + V/H` → Flip vertical/horizontal
- Arrow keys → Move 1px (Shift+Arrow for 5px)
- `Alt + /` → Stats for nerds
- `Cmd/Ctrl + '` → Toggle grid

**Selection**:
- Click drag → Select multiple
- `Cmd/Ctrl + A` → Select all
- Right-click → Context menu (align, arrange, etc.)

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
2. **Two-phase process**: structure first, aesthetics second
3. **Whitespace** as a design element, not empty space
4. **Consistent styling** throughout (colors, sizes, spacing)
5. **Alignment obsession** for professional polish

**Remember**: Boring diagrams fail to communicate, no matter how accurate. Invest in visual design to make your ideas memorable and impactful.

**Quick wins**:
- Use 2-4 colors max, purposefully
- Align everything obsessively
- Add way more whitespace than you think you need
- Vary sizes to create hierarchy
- Export at 2-3x scale

---

**Last Updated**: 2025-11-18
**Skill Type**: Visual Communication Design
**Complexity**: Moderate (easy to start, deep mastery possible)
