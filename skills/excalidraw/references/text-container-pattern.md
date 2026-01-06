---
title: Text in Container Pattern
type: reference
category: ref
permalink: excalidraw-text-container
description: Pattern for binding text to containers in Excalidraw JSON using containerId and boundElements properties to ensure they move together.
---

# Text in Container Pattern (Excalidraw JSON)

**Problem**: Text elements floating separately from containers break when containers move.

**Solution**: Bind text to containers using `containerId` and `boundElements` properties.

---

## Basic Pattern

### Step 1: Create Container

```json
{
  "id": "container-123",
  "type": "rectangle",
  "x": 100,
  "y": 100,
  "width": 200,
  "height": 80,
  "strokeColor": "#c9b458",
  "backgroundColor": "#c9b45840",
  "fillStyle": "solid",
  "strokeWidth": 2,
  "roughness": 1,
  "boundElements": [
    {
      "id": "text-456",
      "type": "text"
    }
  ],
  // ... other required Excalidraw properties
}
```

**Key properties**:
- `id`: Unique identifier for this container
- `boundElements`: Array listing text element(s) inside this container
- `width`, `height`: Container dimensions

### Step 2: Create Text Inside Container

```json
{
  "id": "text-456",
  "type": "text",
  "x": 120,  // Container x + padding (e.g., 20px)
  "y": 125,  // Container y + vertical centering
  "width": 160,  // Container width minus padding (200 - 40)
  "height": 25,  // Auto-calculated by Excalidraw based on text
  "text": "Project Name",
  "fontSize": 24,
  "fontFamily": 1,  // 1=Virgil, 2=Helvetica, 3=Cascadia
  "textAlign": "center",
  "verticalAlign": "middle",
  "containerId": "container-123",
  "originalText": "Project Name",
  "lineHeight": 1.25,
  // ... other required Excalidraw properties
}
```

**Key properties**:
- `containerId`: MUST match container's `id`
- `width`: Should match container width minus padding
- `textAlign`: "center" for centered text
- `verticalAlign`: "middle" for vertical centering
- `x`, `y`: Positioned inside container (accounting for padding)

---

## Auto-Sizing Text to Container

**Goal**: Text should fill container width, wrapping as needed.

**Calculation**:
```javascript
const PADDING = 20;  // Horizontal padding (10px each side)

// Text width = Container width - padding
text.width = container.width - PADDING;

// Text position = Container position + half padding
text.x = container.x + (PADDING / 2);

// Vertical centering (approximate)
text.y = container.y + (container.height / 2) - (text.height / 2);
```

**Example**:
- Container: 200px wide
- Text width: 180px (200 - 20 padding)
- Text x-position: 110px (100 + 10 padding)

---

## Multi-Line Text Wrapping

**Excalidraw automatically wraps text** based on `width` property.

**Line breaks**:
- Use `\n` in `text` property for explicit line breaks
- Excalidraw calculates `height` based on wrapped content
- `lineHeight`: 1.25 (default, good readability)

**Example**:
```json
{
  "text": "Active\nProject\nName",
  "width": 160,
  "lineHeight": 1.25
  // height will be auto-calculated (fontSize * lineHeight * lineCount)
}
```

---

## Grouping (Visual Binding)

While `containerId` creates logical binding, you can also group elements for manual manipulation:

```json
{
  "id": "group-789",
  "type": "group",
  "children": ["container-123", "text-456"]
}
```

**When to use**:
- When you want elements to resize together
- For complex multi-element components
- Grouping related containers

**Note**: `containerId` is usually sufficient for text-in-container pattern.

---

## Common Mistakes

❌ **Missing `boundElements` in container**:
```json
{
  "id": "container-123",
  "type": "rectangle",
  // Missing boundElements!
}
```
Result: Text and container not linked.

❌ **Missing `containerId` in text**:
```json
{
  "id": "text-456",
  "type": "text",
  // Missing containerId!
}
```
Result: Text floats independently.

❌ **Mismatched IDs**:
```json
// Container
{
  "id": "container-123",
  "boundElements": [{"id": "text-999", "type": "text"}]  // Wrong ID!
}

// Text
{
  "id": "text-456",
  "containerId": "container-123"
}
```
Result: Binding broken, elements desync.

❌ **Text wider than container**:
```json
// Container
{"width": 100}

// Text
{"width": 200}  // Too wide! Text overflows.
```
Result: Text spills outside container.

✅ **Correct pattern**:
```json
// Container
{
  "id": "box-1",
  "width": 200,
  "boundElements": [{"id": "txt-1", "type": "text"}]
}

// Text
{
  "id": "txt-1",
  "width": 180,  // 200 - 20 padding
  "containerId": "box-1",
  "textAlign": "center"
}
```

---

## Example: Task Node with Status

**Goal**: Rectangle with task title, properly bound.

```json
{
  "type": "excalidraw",
  "version": 2,
  "elements": [
    {
      "id": "task-box-001",
      "type": "rectangle",
      "x": 500,
      "y": 300,
      "width": 180,
      "height": 60,
      "strokeColor": "#8fbc8f",
      "backgroundColor": "#8fbc8f40",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "roughness": 1,
      "opacity": 100,
      "angle": 0,
      "boundElements": [
        {
          "id": "task-text-001",
          "type": "text"
        }
      ],
      "updated": 1700000000000,
      "version": 1,
      "versionNonce": 123456789,
      "isDeleted": false
    },
    {
      "id": "task-text-001",
      "type": "text",
      "x": 510,  // 500 + 10 padding
      "y": 315,  // Vertically centered
      "width": 160,  // 180 - 20 padding
      "height": 25,
      "text": "Review Bella's project",
      "fontSize": 16,
      "fontFamily": 1,
      "textAlign": "center",
      "verticalAlign": "middle",
      "containerId": "task-box-001",
      "originalText": "Review Bella's project",
      "lineHeight": 1.25,
      "opacity": 100,
      "angle": 0,
      "updated": 1700000000000,
      "version": 1,
      "versionNonce": 987654321,
      "isDeleted": false
    }
  ]
}
```

---

## Programmatic Generation

**Helper function** for creating text-in-container:

```python
def create_text_box(box_id, text_id, x, y, width, height, text_content, font_size, colors):
    """
    Create a rectangle container with centered text inside.

    Args:
        box_id: Unique ID for container
        text_id: Unique ID for text
        x, y: Position coordinates
        width, height: Container dimensions
        text_content: String to display
        font_size: Text size (px)
        colors: Dict with 'stroke' and 'bg' keys

    Returns:
        Tuple of (container_element, text_element)
    """
    PADDING = 20

    container = {
        "id": box_id,
        "type": "rectangle",
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "strokeColor": colors['stroke'],
        "backgroundColor": colors['bg'],
        "fillStyle": "solid",
        "strokeWidth": 2,
        "roughness": 1,
        "opacity": 100,
        "angle": 0,
        "boundElements": [{"id": text_id, "type": "text"}],
        # ... add other required Excalidraw properties
    }

    text = {
        "id": text_id,
        "type": "text",
        "x": x + (PADDING / 2),
        "y": y + (height / 2) - (font_size * 0.6),  # Approximate vertical center
        "width": width - PADDING,
        "height": font_size * 1.25,  # Approximate, Excalidraw recalculates
        "text": text_content,
        "fontSize": font_size,
        "fontFamily": 1,
        "textAlign": "center",
        "verticalAlign": "middle",
        "containerId": box_id,
        "originalText": text_content,
        "lineHeight": 1.25,
        "opacity": 100,
        "angle": 0,
        # ... add other required Excalidraw properties
    }

    return (container, text)
```

**Usage**:
```python
box, txt = create_text_box(
    box_id="goal-1",
    text_id="goal-1-text",
    x=100,
    y=100,
    width=250,
    height=100,
    text_content="Academic Excellence",
    font_size=44,
    colors={'stroke': '#c9b458', 'bg': '#c9b45830'}
)

elements.extend([box, txt])
```

---

## Required Excalidraw Properties (Reference)

Every element needs these properties:

```json
{
  "id": "unique-id",
  "type": "rectangle|text|ellipse|arrow|...",
  "x": 0,
  "y": 0,
  "width": 100,
  "height": 100,
  "angle": 0,
  "strokeColor": "#000000",
  "backgroundColor": "transparent",
  "fillStyle": "solid",
  "strokeWidth": 2,
  "roughness": 1,
  "opacity": 100,
  "groupIds": [],
  "frameId": null,
  "roundness": null,
  "seed": 123456789,
  "version": 1,
  "versionNonce": 987654321,
  "isDeleted": false,
  "updated": 1700000000000,
  "link": null,
  "locked": false
}
```

**For text elements, add**:
```json
{
  "text": "Content here",
  "fontSize": 16,
  "fontFamily": 1,
  "textAlign": "center",
  "verticalAlign": "middle",
  "containerId": "container-id-or-null",
  "originalText": "Content here",
  "lineHeight": 1.25
}
```

**For containers with text, add**:
```json
{
  "boundElements": [
    {"id": "text-id", "type": "text"}
  ]
}
```

**For arrows, add**:
```json
{
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
  "points": [[0, 0], [100, 50]],  // Relative path
  "lastCommittedPoint": null
}
```

---

## Summary Checklist

When creating text-in-container:

- [ ] Container has unique `id`
- [ ] Container has `boundElements: [{id: "text-id", type: "text"}]`
- [ ] Text has matching `containerId`
- [ ] Text `width` = Container `width` - padding (typically -20px)
- [ ] Text positioned inside container (x/y with padding offset)
- [ ] Text `textAlign`: "center" for centered text
- [ ] Text `verticalAlign`: "middle" for vertical centering
- [ ] Both elements have all required Excalidraw properties

**Result**: Text and container move together, text auto-wraps to fit container width.

---

**Last Updated**: 2025-11-19
**Related**: [[theme-colors]], [[technical-details]]
