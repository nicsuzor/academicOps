---
title: Excalidraw Library Usage Guide
type: reference
permalink: excalidraw-library-guide
description: Guidance on using built-in Excalidraw libraries and creating custom component libraries for reuse across diagrams.
---

# Excalidraw Library Usage Guide

## Built-in Libraries

**Available in this skill** (`skills/excalidraw/libraries/`):

6 curated library files ready for immediate use:
- **awesome-icons.excalidrawlib** (105KB) - General-purpose icons for visual interest
- **data-processing.excalidrawlib** (578KB) - Data pipeline, ETL, processing diagrams
- **data-viz.excalidrawlib** (921KB) - Charts, graphs, visualization components
- **hearts.excalidrawlib** (52KB) - Decorative elements, emphasis markers
- **stick-figures-collaboration.excalidrawlib** (281KB) - Human collaboration, teamwork visuals
- **stick-figures.excalidrawlib** (92KB) - Individual human figures, personas

## How to Use Libraries

### Loading Libraries

1. **Load into Excalidraw**:
   - Open Excalidraw
   - Click library icon (book/folder icon in toolbar)
   - Click "Load library from file"
   - Navigate to `skills/excalidraw/libraries/`
   - Select one or more .excalidrawlib files
   - Components now available in library panel

2. **Insert library components**:
   - Open library panel (click library icon)
   - Browse loaded libraries
   - Click component to insert into canvas
   - Customize colors, sizes, labels as needed

3. **Combine libraries with custom design**:
   - Use library components as starting points
   - Apply consistent styling (colors, fonts)
   - Group library elements with custom shapes
   - Maintain visual coherence between library and custom elements

### When to Use Libraries

- ✅ Data visualization diagrams (use data-viz components)
- ✅ Human-centered process flows (use stick figures)
- ✅ Complex data pipelines (use data-processing)
- ✅ Adding visual interest to otherwise plain diagrams (use awesome-icons, hearts)
- ❌ Don't force library components if simple custom shapes work better
- ❌ Don't mix too many library styles (creates visual chaos)

### Library Styling Tips

- Library components come with default colors → recolor for consistency
- Group library elements to create custom compound components
- Use library items sparingly for emphasis, not everywhere
- Match library component stroke width to your diagram's overall style

## Online Libraries

Access additional pre-built components at libraries.excalidraw.com:
- System design components (databases, load balancers, queues)
- Cloud architecture (AWS, Azure, GCP icons)
- Network diagrams (routers, switches, firewalls)
- UI/UX wireframe components

**Installation**: Click "Add to Excalidraw" → available in library panel

## Creating Custom Libraries

### Save Reusable Components

1. Design component (group multiple elements)
2. Add to library for reuse
3. Maintain consistent styling across projects

### Design Systems Approach

- Define standard shapes/sizes for common elements
- Create color palette presets
- Document spacing rules
- Build component library
