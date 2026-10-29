---
title: Rendering Argument Maps from Argdown Sources
status: ready
---

# Rendering Argument Maps from Argdown Sources

Visual argument maps rebuild automatically from canonical Argdown sources into Excalidraw whiteboards, vector SVGs, and readable overview pages through composable agent skills and general CLI tools, eliminating hand coordinate layout and single-purpose monolithic scripts.

## User stories

### US-1 Automated Argument Rebuild Without Hand Layout

As a researcher or supervisor reading an argument map, I want the visual diagram and overview page to rebuild automatically from updated Argdown source text, so that visual maps never fall out of sync with the underlying logical reconstruction and require no manual coordinate editing.

- **AC-1.1** Given a canonical Argdown document in the PKB, when the rebuild procedure runs, then complete `.excalidraw` scenes, vector `.svg` images, and an overview `.md` page are generated without manual coordinate calculations or hand pixel adjustments.
- **AC-1.2** Given the three representative academic benchmark argument topologies (the multi-leg research paper skeleton, the long-form chapter argument, and the multi-chapter doctoral narrative argument), when the rebuild procedure executes, then all three benchmark topologies compile cleanly into multi-level canvases with zero manual intervention.

### US-2 Referential Integrity and Collision-Free Geometry

As a developer auditing generated diagram artifacts, I want generated canvases to pass automated referential integrity and spatial collision audits, so that whiteboards remain interactively editable and legible.

- **AC-2.1** Given any generated `.excalidraw` file, when audited with referential integrity checks, then every text element carries `containerId` pointing to its shape, shapes carry reciprocal entries in `boundElements`, and every element's `index` key strictly complies with the base-62 fractional-indexing schema containing no trailing zeros in the fractional part.
- **AC-2.2** Given any generated `.excalidraw` file, when audited with spatial collision checks, then zero non-nested shape bounding-box collisions and zero connector polyline intersections with unrelated intermediate boxes are reported.

### US-3 Visual QA and Multi-Scale Readability

As an academic peer reviewing an argument map, I want diagrams that respect visual hierarchy ("nest first, arrow last"), so that top-level thesis claims and part structures are discernible at a glance while warrants and evidence remain inspectable on detailed sub-maps.

- **AC-3.1** Given an argument map with multiple parts or chapters, when rendered, then the output comprises a top-level overview canvas (root headline, part panels, section columns) and dedicated sub-canvases per part with warrant premise-conclusion blocks.
- **AC-3.2** Given rendered vector SVGs, when subjected to visual QA, then arrowheads terminate cleanly at container perimeters, text labels fit completely within container boundaries without clipping, contrast ratios meet or exceed 4.5:1, and encodings remain distinguishable under greyscale.

### US-4 In-Place Editability and Change Propagation

As an author refining premises or tagging open gaps in Argdown, I want edits to propagate directly to existing diagrams, so that modifying a claim or warrant immediately reflects in the visual canvas without recreating unrelated elements.

- **AC-4.1** Given an existing argument map canvas, when a claim's text or tag is edited in the Argdown source and the rebuild runs, then the corresponding canvas node is updated in place, preserving existing element IDs through deterministic title slugging.

## Design

### Division of Labour

Responsibilities are partitioned between domain semantics and general diagram manipulation:

1. **Visual Argument Mapping Skill (`ida:argument-map`):**
   - Extracts and reconstructs argument structures from source texts into canonical Argdown.
   - Maps semantic constructs (thesis, parts, chapters, sections, warrants) to visual hierarchy.
   - Manages the multi-scale canvas decomposition (overview canvas and per-part sub-canvases).
   - Synthesizes the overview markdown document linking generated SVGs, summary metrics, and open issue audits (`#missing`, `#needs-evidence`, `#unanswered`, `#conflict`).
   - Deprecates and retires legacy ad-hoc scripts (`references/gen_panels.py` and `tree_lint.py`).

2. **Diagramming Standard Skill (`tools:diagram`):**
   - Canonical authority for visual hierarchy rules ("nest first, arrow last": headline root, panels for parts, columns for sections, cards for leaves).
   - Defines standard palette roles, container padding, and typography constants for text fitting.
   - Establishes the visual QA inspection protocol on rendered vector SVGs.

3. **Argdown Syntax Tool (`@argdown/cli`):**
   - Standalone syntax parser compiling Argdown text into standard JSON Abstract Syntax Trees (AST) containing statements, arguments, relations, and metadata.

4. **Whiteboard Manipulation Tool (`pkb-excalidraw`):**
   - Zero-dependency CLI companion operating on `.excalidraw` whiteboard files.
   - Executes atomic mutations (element addition, container resizing, text binding, connector creation).
   - Provides automated layout and packing algorithms for nested containers and cards.
   - Validates referential integrity, fractional indexing, and spatial non-overlap.
   - Renders zero-dependency vector SVGs and PNG images.

### Structural Mapping: Argdown AST to Whiteboard Panels

The visual argument mapping skill directs the transformation of Argdown AST nodes into spatial Excalidraw structures following containment conventions:

| Argdown Construct | Visual Element | Styling and Layout Treatment |
| - | - | - |
| **Thesis / Root Statement** | Hero Headline | Prominent headline text at top of canvas, outside any box, with whitespace. |
| **Part / Chapter Headings** (`#`, `##`) | Zone Panels | Enclosing background panel (`#f1f3f5`, subtle border). Nesting conveys high-level structure without arrows. |
| **Section Headings** (`###`) | Columns within Panels | Vertical column lanes within the part panel, partitioning thematic argument threads. |
| **Claims & Premises** | Cards (`rectangle`, sharp corners) | Sized dynamically to text. Fill and stroke bound to semantic role (claim: gold, evidence: green, theory: purple). |
| **Open Gaps & Objections** | Annotated Cards (`dashed` border) | Sized to text. `#missing` and `#needs-evidence`: warning orange with dashed stroke; `#unanswered` and `#conflict`: soft red stroke. |
| **Warrant Blocks** (`-- Warrant --`) | Premise-Conclusion Clusters | Placed on per-part detail canvases beside the main panel. Warrants rendered with dotted neutral border and explicit premise relations. |
| **Support Relations** (`+>`) | Containment or Solid Arrows | Direct vertical containment within columns for hierarchical support; solid directed arrows (`#404040`) only for moves between distinct columns or panels. |
| **Attack Relations** (`->`, `_>`) | Solid Directed Arrows | Directed arrows in error red (`#e03131`) connecting the objection/rebuttal to the target claim or inference bar. |

### Rebuild Contract & Processing Stages

When an argument map is compiled or updated from source, execution advances through four observable transformation stages:

1. **Syntax Parsing:** The canonical Argdown source is parsed into an AST representing statements, arguments, relation graphs, tags, and data attributes.
2. **Hierarchical Assembly & Layout:** AST nodes are mapped into a nested structure (root headline, part panels, section columns, and card clusters). A layout algorithm computes non-overlapping bounding boxes, wraps text according to typeface constants, establishes bidirectional bindings between text and container shapes, and routes connectors around shapes.
3. **Automated Audit & Verification:** Canvases are audited against referential integrity (valid bidirectional bindings, monotonic base-62 fractional indices without trailing fractional zeros) and spatial clearing (zero AABB collisions, zero arrow-box crossings).
4. **Rendering & Visual QA:** Canvases are rendered to vector SVGs. The executing agent visually inspects the rendered graphics against visual QA criteria to verify arrowheads terminate at shape boundaries, text does not overflow containers, and contrast is preserved.
5. **Page Synthesis:** An overview markdown document is emitted, embedding the rendered overview SVG, per-part sub-canvas SVGs, summary statistics, and part-by-part gap analyses.

### Non-Tree Topological Semantics

Real academic arguments are directed acyclic graphs (DAGs) rather than strict trees. Non-tree relations are handled systematically:

1. **Multi-Parent Lemmas:** When an evidence card or intermediate lemma supports claims across multiple sections or chapters, it resides within the container of its primary introduction. Secondary support relations are represented by directed cross-panel arrows connecting the node to secondary targets.
2. **Undercut Relations Targeting Inference Bars:** Relations attacking a warrant or inference step (`_>`) bind directly to the warrant block's container or inference connector rather than a terminal claim card.
3. **Cross-Canvas Boundary References:** On per-part detail canvases, external premises originating in other chapters are rendered as reference stub cards (muted background, external indicator) with inbound connector stubs.

### Deterministic In-Place Element Reconciliation

To ensure that rebuilding a canvas preserves manual annotations and stable references:

1. **Deterministic Element Identification:** Element IDs are derived deterministically from the statement or argument title (using alphanumeric snake-case slugging: `s_<slug>` for statements, `a_<slug>` for arguments, `w_<slug>` for warrants).
2. **In-Place Mutation:** When rebuilding an existing canvas, elements with matching IDs are updated in place (updating text, dimensions, and styling) rather than deleted and recreated, preserving existing positions where possible and maintaining stable element identities across git revisions.

## Open questions

- **OD-1: Layout Engine Boundary in Tooling:** Should container packing and connector obstacle-avoidance be implemented as a native subcommand within `pkb-excalidraw` (e.g. `pkb-excalidraw layout --hierarchy`), or should `pkb-excalidraw` consume pre-computed layout coordinates from an upstream layout adapter (such as ELK / Graphviz JSON)?
- **OD-2: Sub-Canvas Decomposition Threshold:** What statement count or nesting depth marks the boundary where an argument section should split from a panel column on the overview canvas into a dedicated sub-canvas?
