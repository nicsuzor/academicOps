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
    "viewBackgroundColor": "#ffffff"
  }
}
```

Additional properties may include zoom level, selected elements, UI state, etc.

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
    "elementId": "source-element-id",
    "focus": 0,
    "gap": 10
  },
  "endBinding": { // REQUIRED - anchors arrow to target box
    "elementId": "target-element-id",
    "focus": 0,
    "gap": 10
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

**Arrow binding details**:

```json
{
  "startBinding": {
    "elementId": "source-box-id", // Required: ID of element arrow starts from
    "focus": 0, // -1 to 1: Position along edge (-1=left/top, 0=center, 1=right/bottom)
    "gap": 10 // Pixels between arrow and element edge
  },
  "endBinding": {
    "elementId": "target-box-id", // Required: ID of element arrow points to
    "focus": 0.2, // Offset from center for visual clarity
    "gap": 10
  }
}
```

**Arrow positioning strategy**:

- `focus: 0` → Arrow connects to center of edge (most common)
- `focus: -0.5` → Arrow connects to left/top quarter of edge
- `focus: 0.5` → Arrow connects to right/bottom quarter of edge
- **Vary focus values** to prevent arrows overlapping when multiple arrows connect to same box
- `gap: 8-12px` provides visual separation between arrow and box border
- When position not specified for start/end, Excalidraw computes based on arrow's x/y coordinates

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

**Last Updated**: 2025-11-26
**Maintainer**: excalidraw skill
**Status**: Reverse-engineered specification with official API documentation
