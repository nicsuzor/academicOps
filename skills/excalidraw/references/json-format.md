# Excalidraw JSON File Format Reference

**Purpose**: Technical specification for direct manipulation of .excalidraw files.

**When to use**: Batch processing, custom tooling, automation without MCP server.

**Warning**: Complex structure with many required properties. Easy to create invalid files.

---

## File Format Structure

Excalidraw uses plaintext JSON with this structure:

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "https://excalidraw.com",
  "elements": [ /* array of element objects */ ],
  "appState": { /* editor configuration */ },
  "files": { /* image data */ }
}
```

---

## Core Attributes

| Property | Type | Purpose | Example |
|----------|------|---------|---------|
| `type` | String | Schema identifier | `"excalidraw"` |
| `version` | Integer | Schema version | `2` |
| `source` | String | Application origin | `"https://excalidraw.com"` |
| `elements` | Array | Canvas drawing objects | See below |
| `appState` | Object | Editor configuration | See below |
| `files` | Object | Image element data | See below |

---

## Element Properties

Each element in the `elements` array includes these properties:

### Common Properties (Required)

```json
{
  "id": "unique-element-id",
  "type": "rectangle",  // rectangle, ellipse, diamond, arrow, line, text, image
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
  "fillStyle": "hachure",     // hachure, solid, cross-hatch
  "strokeWidth": 1,            // 1, 2, 4, 8, etc.
  "strokeStyle": "solid",      // solid, dashed, dotted
  "roughness": 1,              // 0-2 (0=smooth, 2=very rough)
  "opacity": 100               // 0-100
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

---

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

---

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

---

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

---

## Clipboard Format

When copying elements, use slightly different schema:

```json
{
  "type": "excalidraw/clipboard",
  "elements": [ /* array of copied elements */ ],
  "files": { /* associated image data */ }
}
```

---

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
  "height": 0,
  "points": [[0, 0], [200, 0]],
  "startBinding": {
    "elementId": "source-element-id",
    "focus": 0,
    "gap": 10
  },
  "endBinding": {
    "elementId": "target-element-id",
    "focus": 0,
    "gap": 10
  },
  "startArrowhead": null,
  "endArrowhead": "arrow"
  // + all common properties
}
```

### Text
```json
{
  "type": "text",
  "x": 100,
  "y": 100,
  "width": 150,
  "height": 25,
  "text": "Sample Text",
  "fontSize": 16,
  "fontFamily": 1,
  "textAlign": "left",
  "verticalAlign": "top",
  "baseline": 18
  // + all common properties
}
```

---

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
- 0 = Perfectly straight (architectural)
- 1 = Default hand-drawn feel
- 2 = Very sketchy

### Roundness Types
- `{ "type": 1 }` = Legacy round corners
- `{ "type": 2 }` = Proportional radius
- `{ "type": 3 }` = Adaptive corners (default)

---

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

---

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

---

**Last Updated**: 2025-11-18
**Maintainer**: excalidraw skill
**Status**: Reverse-engineered specification (unofficial)
