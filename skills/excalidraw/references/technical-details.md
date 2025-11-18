# Excalidraw Technical Details

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

## Layout & Spatial Organization

### Alignment Tools

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

### Fill Patterns

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
