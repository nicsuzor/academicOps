---
title: Excalidraw JSON File Format Reference
type: reference
category: ref
permalink: excalidraw-json-format
description: Technical specification for direct manipulation of .excalidraw files, including element properties, styling, and binding patterns.
---

# Excalidraw JSON File Format Reference

**Purpose**: Technical specification for direct manipulation of .excalidraw files.

**When to use**: Batch processing, custom tooling, automation without MCP server.

**Warning**: Complex structure with many required properties. Easy to create invalid files.

## File Format Structure

Excalidraw uses plaintext JSON with this structure:

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "https://excalidraw.com",
  "elements": [/* array of element objects */],
  "appState": {/* editor configuration */},
  "files": {/* image data */}
}
```

## Core Attributes

| Property   | Type    | Purpose                | Example                    |
| ---------- | ------- | ---------------------- | -------------------------- |
| `type`     | String  | Schema identifier      | `"excalidraw"`             |
| `version`  | Integer | Schema version         | `2`                        |
| `source`   | String  | Application origin     | `"https://excalidraw.com"` |
| `elements` | Array   | Canvas drawing objects | See below                  |
| `appState` | Object  | Editor configuration   | See below                  |
| `files`    | Object  | Image element data     | See below                  |

## Element Properties

Each element in the `elements` array includes these properties:

### Common Properties (Required)

```json
{
  "id": "unique-element-id",
  "type": "rectangle", // rectangle, ellipse, diamond, arrow, line, text, image
  "x": 100,
  "y": 200,
  "width": 200,
  "height": 100,
  "angle": 0,
  "index": "a0", // REQUIRED - fractional z-order key, see "Z-Order (`index`)" below
  "version": 1,
  "versionNonce": 987654321,
  "isDeleted": false
}
```

### Styling Properties (Required)

```json
{
  "strokeColor": "#1e1e1e",
  "backgroundColor": "#ffc9c9",
  "fillStyle": "hachure", // hachure, solid, cross-hatch
  "strokeWidth": 1, // 1, 2, 4, 8, etc.
  "strokeStyle": "solid", // solid, dashed, dotted
  "roughness": 1, // 0-2 (0=smooth, 2=very rough)
  "opacity": 100 // 0-100
}
```

### Advanced Properties (Usually Required)

```json
{
  "groupIds": [],
  "frameId": null,
  "roundness": { "type": 3 },
  "seed": 123456,
  "boundElements": null,
  "updated": 1700000000000,
  "link": null,
  "locked": false
}
```

## Complete Element Example

```json
{
  "id": "abc123xyz",
  "type": "rectangle",
  "x": 100,
  "y": 200,
  "width": 200,
  "height": 100,
  "angle": 0,
  "strokeColor": "#1e1e1e",
  "backgroundColor": "#ffc9c9",
  "fillStyle": "hachure",
  "strokeWidth": 1,
  "strokeStyle": "solid",
  "roughness": 1,
  "opacity": 100,
  "groupIds": [],
  "frameId": null,
  "index": "a0",
  "roundness": { "type": 3 },
  "seed": 123456,
  "version": 1,
  "versionNonce": 987654321,
  "isDeleted": false,
  "boundElements": null,
  "updated": 1700000000000,
  "link": null,
  "locked": false
}
```

## Application State

Editor configuration:

```json
{
  "appState": {
    "gridSize": 20,
    "viewBackgroundColor": "#ffffff",
    "lockedMultiSelections": {}
  }
}
```

`lockedMultiSelections` is written by current excalidraw.com even on an empty scene — always include it (as `{}` if nothing is locked). Its absence is one of the things that triggers a full-file migration rewrite when the file is next opened and saved in the web app.

Additional properties may include zoom level, selected elements, UI state, etc.

## Z-Order (`index`)

Every element carries a required `index` string — a **fractional index** (the same family of algorithm Figma and Linear use) that determines stacking order. Elements render in ascending lexicographic order of `index`; you never renumber existing elements to insert one in the middle, you generate a new key that sorts between its neighbors.

**Character set**: `0-9`, then `A-Z`, then `a-z` (ASCII order — this is why you'll see keys like `b0Y`, `b0Z`, `b0a`, `b0b` climbing in that sequence). Keys of the same length sort exactly like you'd read them; a shorter key sorts before a longer key that starts with it (e.g. `"a0"` < `"a00"`).

**For newly generated files, don't try to replicate excalidraw.com's internal jittered-fractional-indexing implementation byte-for-bit** — you only need output that is _valid_ per this scheme (so the web app has no reason to regenerate it). A simple monotonically increasing generator is sufficient:

```python
_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

def generate_indices(n: int) -> list[str]:
    """Valid, strictly-increasing fixed-width fractional-index keys for n elements in z-order."""
    base = len(_ALPHABET)
    if n > base * base:
        raise ValueError(f"generate_indices supports up to {base * base} elements")
    return [f"a{_ALPHABET[i // base]}{_ALPHABET[i % base]}" for i in range(n)]
```

(Fixed 3-character width keeps every key the same length, so lexicographic order is numeric order with no prefix-collision edge cases — up to 62×62 = 3,844 elements, far beyond any hand-authored diagram.)

Assign `index` values in the same order elements should stack (later `index` = drawn on top). **Do not** reuse an old ad hoc scheme like sequential `"c00"`, `"c01"`, `"d02"`... — that was produced by the discontinued VS Code Excalidraw extension and is not recognized as valid by excalidraw.com's fractional-indexing validator, so the whole file's `index` values get silently regenerated (and the array order re-sorted) the moment it's opened and saved there. That single-property mismatch is what turns an otherwise-untouched file into a huge diff.

## Files Object

For image elements, maps fileId to file data:

```json
{
  "files": {
    "file-abc123": {
      "mimeType": "image/png",
      "id": "file-abc123",
      "dataURL": "data:image/png;base64,[base64-encoded-data]",
      "created": 1700000000000,
      "lastRetrieved": 1700000000000
    }
  }
}
```

## Clipboard Format

When copying elements, use slightly different schema:

```json
{
  "type": "excalidraw/clipboard",
  "elements": [/* array of copied elements */],
  "files": {/* associated image data */}
}
```

## Element Type Reference

### Rectangle

```json
{
  "type": "rectangle",
  "x": 100,
  "y": 100,
  "width": 200,
  "height": 100
  // + all common properties
}
```

### Ellipse

```json
{
  "type": "ellipse",
  "x": 100,
  "y": 100,
  "width": 150,
  "height": 150
  // + all common properties
}
```

### Diamond

```json
{
  "type": "diamond",
  "x": 100,
  "y": 100,
  "width": 100,
  "height": 100
  // + all common properties
}
```

### Arrow

```json
{
  "type": "arrow",
  "x": 100,
  "y": 100,
  "width": 200,
  "height": 50, // Non-zero for curved arrows
  "points": [[0, 0], [100, 30], [200, 50]], // Multiple points for curves - REQUIRED for organic feel
  "startBinding": { // REQUIRED - anchors arrow to source box
    "mode": "orbit",
    "elementId": "source-element-id",
    "fixedPoint": [0.5, 1]
  },
  "endBinding": { // REQUIRED - anchors arrow to target box
    "mode": "orbit",
    "elementId": "target-element-id",
    "fixedPoint": [0.5, 0]
  },
  "startArrowhead": null,
  "endArrowhead": "arrow"
  // + all common properties (remember: roughness: 2 for hand-drawn feel)
}
```

**CRITICAL for arrows**:

- **Always bind to shapes** - never create floating arrows
- **Use multiple points** for curved paths (minimum 3 points recommended)
- **Route around boxes** - arrows should never pass through unrelated elements
- **roughness: 2** for consistent hand-drawn aesthetic

**Arrow binding details** (current excalidraw.com format — as of the schema excalidraw.com itself now writes; this superseded an older `{elementId, focus, gap}` shape used by the discontinued VS Code extension, and older files will get silently rewritten wholesale the next time they're opened and saved on excalidraw.com):

```json
{
  "startBinding": {
    "mode": "orbit", // Required literal value — the only mode excalidraw.com currently emits
    "elementId": "source-box-id", // Required: ID of element arrow starts from
    "fixedPoint": [0.5, 1] // [x, y] normalized 0..1 anchor on the bound element's bounding box
  },
  "endBinding": {
    "mode": "orbit",
    "elementId": "target-box-id", // Required: ID of element arrow points to
    "fixedPoint": [0.5, 0]
  }
}
```

There is no more `focus`/`gap` pair — the anchor point and any visual gap are both folded into `fixedPoint`, a single normalized coordinate on the bound element's own bounding box: `[0, 0]` = top-left corner, `[1, 1]` = bottom-right corner.

**`fixedPoint` anchor convention** (edge midpoints — use these for the vast majority of arrows):

| Anchor             | `fixedPoint` |
| ------------------ | ------------ |
| Top-center         | `[0.5, 0]`   |
| Bottom-center      | `[0.5, 1]`   |
| Left-center        | `[0, 0.5]`   |
| Right-center       | `[1, 0.5]`   |
| Dead center (rare) | `[0.5, 0.5]` |

- **Vary the offset along the edge** (e.g. `[0.3, 0]` or `[0.7, 0]`) to prevent multiple arrows overlapping where they land on the same box — this replaces the old `focus: -0.5 .. 0.5` trick.
- Pick the edge (`x`=0/0.5/1, `y`=0/0.5/1) based on the arrow's actual approach direction: an arrow arriving from below binds to the target's top edge (`[0.5, 0]`), one arriving from the side binds to the left/right edge, etc.
- Don't try to reproduce excalidraw.com's own floating-point precision (it emits values like `0.5001` from its internal geometry solver) — clean `0`, `0.5`, `1` values are valid and load identically; the app will not rewrite a file just because your anchors are exact rather than jittered.
- When position isn't specified for start/end, Excalidraw computes one from the arrow's x/y coordinates, but always set it explicitly for reproducible, diff-quiet output.

### Text

```json
{
  "type": "text",
  "x": 100,
  "y": 100,
  "width": 150, // Auto-calculated if omitted when using convertToExcalidrawElements API
  "height": 25, // Auto-calculated based on text content + fontSize + lineHeight
  "text": "Sample Text",
  "fontSize": 16,
  "fontFamily": 1, // 1=Virgil (hand-drawn, PREFERRED), 2=Helvetica, 3=Cascadia
  "textAlign": "left",
  "verticalAlign": "top",
  "baseline": 18, // Distance from top to text baseline, scales with fontSize
  "lineHeight": 1.25, // Multiplier for line spacing (1.25 = 125% of fontSize)
  "containerId": null // ID of container element if text is bound to a shape
  // + all common properties
}
```

**Text sizing rules**:

- **Width calculation**: Approximately `text.length * fontSize * 0.6` for rough estimates (varies by font)
- **Height calculation**: `fontSize * lineHeight * lineCount` where lineCount depends on text wrapping
- **Baseline**: Typically `fontSize * 0.7` for Virgil font family
- **Container padding**: Add ~20px padding when calculating container size around text
- **Auto-sizing**: When using `convertToExcalidrawElements()` API, omit width/height for automatic calculation

**Bound text elements** (text inside containers):

```json
// Text element with containerId
{
  "type": "text",
  "containerId": "container-element-id",  // Links to parent container
  "text": "Text inside box",
  // width auto-calculated to fit container with padding
  // ... other properties
}

// Container element with bound text
{
  "type": "rectangle",
  "id": "container-element-id",
  "boundElements": [
    { "type": "text", "id": "text-element-id" }
  ],
  // ... other properties
}
```

## Element Sizing Best Practices

**Problem**: All elements being the same size creates visual chaos and poor hierarchy.

**Solution**: Vary element dimensions dramatically based on content importance and text length.

### Container Sizing Guidelines

**Calculate based on text content**:

```javascript
// Rough formula for container dimensions
const padding = 20;  // Minimum padding around text
const fontSize = 16;
const lineHeight = 1.25;

// Estimate text width (varies by font, this is approximate)
const textWidth = text.length * fontSize * 0.6;

// Calculate wrapped lines if text is long
const maxWidth = 300;  // Maximum container width
const actualWidth = Math.min(textWidth + padding * 2, maxWidth);
const lineCount = Math.ceil(textWidth / (actualWidth - padding * 2));

// Calculate container dimensions
const containerWidth = actualWidth;
const containerHeight = fontSize * lineHeight * lineCount + padding * 2;
```

**Recommended minimum sizes**:

- **XL elements** (goals, main concepts): 200-400px wide, 80-150px high
- **L elements** (projects, sections): 150-250px wide, 60-100px high
- **M elements** (tasks, details): 120-180px wide, 40-70px high
- **S elements** (labels, tags): 80-120px wide, 30-50px high

**Dynamic sizing by text length**:

```javascript
// Adapt container size to text
if (text.length < 15) {
  width = 100; height = 40;  // Small, compact
} else if (text.length < 30) {
  width = 150; height = 50;  // Medium
} else if (text.length < 50) {
  width = 200; height = 60;  // Large
} else {
  width = 250; height = 80;  // Extra large, allow wrapping
}
```

**Visual hierarchy through size**:

- Make important elements **2-3× larger** than supporting elements
- Outstanding tasks should be **PROMINENT** (160-200px wide)
- Completed tasks should be **DE-EMPHASIZED** (100-120px wide, small text)
- Central concepts in mind maps should be **LARGEST** (300-400px wide)

### Text Fitting in Containers

**Common issue**: Text overflows or is tiny inside large boxes.

**Solutions**:

1. **Match text size to container**:

```javascript
// Scale fontSize based on container size
const containerWidth = 200;
const textLength = text.length;
const targetFontSize = Math.min(
  20,  // Maximum font size
  Math.max(
    12,  // Minimum font size
    (containerWidth - 40) / (textLength * 0.6)  // Calculated to fit
  )
);
```

2. **Match container to text** (preferred):

```javascript
// Size container to fit text comfortably
const fontSize = 16;  // Fixed size
const padding = 20;
const containerWidth = text.length * fontSize * 0.6 + padding * 2;
const containerHeight = fontSize * 1.25 + padding * 2;
```

3. **Use text wrapping**:

```javascript
// For longer text, set max width and wrap
const fontSize = 16;
const maxWidth = 250;
const padding = 20;
const lineCount = Math.ceil(text.length * fontSize * 0.6 / (maxWidth - padding * 2));
const containerHeight = fontSize * 1.25 * lineCount + padding * 2;
```

## Property Details

### Stroke Width Values

- 1 = Thin (default)
- 2 = Medium
- 4 = Bold
- 8 = Extra bold

### Fill Style Values

- `"hachure"` = Hand-drawn hatching (default)
- `"solid"` = Solid fill
- `"cross-hatch"` = Cross-hatched pattern

### Stroke Style Values

- `"solid"` = Solid line (default)
- `"dashed"` = Dashed line
- `"dotted"` = Dotted line

### Roughness Values

- 0 = Perfectly straight (architectural) - **AVOID**
- 1 = Default hand-drawn feel
- 2 = Very sketchy - **PREFERRED** (maximum hand-drawn aesthetic)

### Roundness Types

- `{ "type": 1 }` = Legacy round corners
- `{ "type": 2 }` = Proportional radius
- `{ "type": 3 }` = Adaptive corners (default)

## Important Caveats

### No Official Schema Documentation

Must reverse-engineer from source code and examples. Schema may change without notice.

### Complex Required Properties

Many properties are required but not well-documented:

- `versionNonce`: Random integer for conflict resolution
- `seed`: Random number for roughness algorithm
- `roundness`: Complex object, type depends on shape
- `boundElements`: Array of connected element references
- `index`: Fractional z-order key — see "Z-Order (`index`)" above; an invalid or missing scheme triggers a full-file rewrite on next open/save in excalidraw.com

### Validation Challenges

Easy to create files that look valid but fail to load:

- Missing required properties
- Invalid property combinations
- Incorrect type specifications
- Malformed binding references

### Multi-Agent Approach Recommended

One-shot generation often fails due to:

- Output token limits
- Accuracy issues with complex JSON
- Missing required properties

**Strategy**: Generate structure first, validate and refine iteratively.

## Resources

### Official Documentation

- JSON Schema: https://docs.excalidraw.com/docs/codebase/json-schema
- GitHub Source: https://github.com/excalidraw/excalidraw/blob/master/dev-docs/docs/codebase/json-schema.mdx

### Type Definitions

Check Excalidraw repository for TypeScript type definitions:

- `packages/excalidraw/element/types.ts`
- `packages/excalidraw/types.ts`

### Examples

Study existing .excalidraw files to understand working patterns.

## Sources & References

**Official Documentation**:

- [JSON Schema | Excalidraw developer docs](https://docs.excalidraw.com/docs/codebase/json-schema)
- [Creating Elements programmatically](https://docs.excalidraw.com/docs/@excalidraw/excalidraw/api/excalidraw-element-skeleton)
- [GitHub: JSON Schema Documentation](https://github.com/excalidraw/excalidraw/blob/master/dev-docs/docs/codebase/json-schema.mdx)

**Text Container & Sizing**:

- [PR #4343: Bind text to shapes](https://github.com/excalidraw/excalidraw/pull/4343) - Text containers implementation
- [PR #6546: Support creating containers programmatically](https://github.com/excalidraw/excalidraw/pull/6546)
- [Issue #6514: Create text inside rectangle programmatically](https://github.com/excalidraw/excalidraw/issues/6514)
- [Issue #3850: Autolayout container to fit text](https://github.com/excalidraw/excalidraw/issues/3850)

**Arrow Binding**:

- [Issue #157: Attached arrows and lines (glue points)](https://github.com/excalidraw/excalidraw/issues/157)
- [Issue #4797: Arrows shouldn't bind to any shapes](https://github.com/excalidraw/excalidraw/issues/4797)
- [DeepWiki: Linear Element Editor](https://deepwiki.com/excalidraw/excalidraw/6.1-linear-element-editor)

**Maintainer**: excalidraw skill
**Status**: Reverse-engineered specification with official API documentation
