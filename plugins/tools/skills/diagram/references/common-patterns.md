---
category: ref
---

# Common Patterns & Templates

## System Architecture Diagram

**Structure**:

- Layers: Frontend (top) → Backend (middle) → Data (bottom)
- Colors: Same color = same tier/responsibility
- Arrows: Show data flow, dependencies

**Visual treatment**:

- Larger boxes for complex components
- Grouped services in same color family
- Clear directional arrows
- Labels on all connections

## Process Flow

**Structure**:

- Start (circle) → Steps (rectangles) → End (circle)
- Decisions (diamonds) with Yes/No paths
- Left-to-right or top-to-bottom flow

**Visual treatment**:

- Color coding by actor/swim lane
- Dotted arrows for optional paths
- Consistent spacing between steps
- Numbered steps if sequential

## Concept Map / Mind Map (PREFERRED LAYOUT STYLE)

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

## Graph/Network Visualization (Goal → Project → Task Structure)

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

## Comparison Matrix

**Structure**:

- Items as rows or columns
- Criteria as opposite axis
- Visual indicators for ratings

**Visual treatment**:

- Consistent cell sizes
- Color scale for intensity
- Icons or symbols for categories
- Clear headers with contrast
