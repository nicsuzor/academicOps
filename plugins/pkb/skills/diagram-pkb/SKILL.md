---
name: diagram-pkb
description: >-
  Generates expressive, aesthetic Excalidraw diagrams of the PKB (Personal Knowledge Base)
  using the 5-Layer Composition Model and semantic topology. Use this skill when the user
  asks to visualize the PKB, draw an ego-network, map out task dependencies, or graph relationships
  in a visually pleasing way.
---

# Diagram PKB

This skill combines the aesthetic principles from the `diagram` skill with PKB extraction to create beautiful, topologically sound maps of your knowledge base.

It delegates the heavy lifting of spatial coordinate generation (X, Y pixels) to the Rust layout engine (`layout.rs` inside `excalidraw-view`), allowing you to focus purely on **semantic topology** and **composition**.

## The 5-Layer Composition Model

When mapping the PKB, construct the diagram conceptually rather than as a flat array of boxes. Ask yourself which PKB nodes belong to which layer:

1. **Scenery**: Background boundaries and logical zones (`--preset zone`). Use this for grouping related epics or broad domains.
2. **Spine**: The critical path and focal landmark nodes (`--preset hero`). Use this for the root node of the ego-network or the primary tasks in a sequence.
3. **Satellites**: Supporting utility components and standard nodes.
4. **Annotations**: Human commentary via sticky notes (`--preset sticky`). Use this to explain _why_ a dependency exists, pulling from the task's context or rationale.
5. **Connectors**: Solid flows vs. dashed telemetry (`--curved`, `--stroke-style dashed`). Use curved/dashed edges for weak links (e.g., semantic neighbors or conceptual links) and solid edges for strong dependencies (`depends_on`, `contributes_to`).

## Workflow Instructions

1. **Extract the Topology**:
   Use the `pkb__graph_excalidraw` MCP tool or the CLI `pkb excalidraw` to generate the base `.excalidraw` JSON for the neighborhood you are graphing.
   _Example: Generate a 2-hop neighborhood around a specific task._

2. **Apply Semantic Archetypes**:
   Do not try to move nodes by altering their X, Y coordinates in JSON! Instead, use `excalidraw-view` CLI to modify the nodes with aesthetic flags:
   - Make the central node a hero: `excalidraw-view FILE add-node --preset hero --text "Central Idea"` (or use a script to inject the `hero` styling).
   - Add annotations: `excalidraw-view FILE add-node --preset sticky --text "Key insight..."`
   - Mark weak links: `excalidraw-view FILE connect --from A --to B --curved --stroke-style dashed`

3. **Compute the Layout**:
   Let the Rust layout engine compute the final coordinates.
   - For ego-networks (one central node, many children), prefer **Radial Layout** (`--layout radial`).
   - For sequential pipelines or chronological task dependencies, prefer **Sugiyama Layout** (the default pipeline).

4. **Verify the Graph**:
   Always validate the structural integrity of your final `.excalidraw` file before returning it to the user.
   ```bash
   python3 scripts/excalidraw-view.py FILE check
   ```

## References

- Follow all typographical and aesthetic rules defined in the base `diagram` skill (`plugins/tools/skills/diagram/SKILL.md`).
- For manual graph edits, prefer append-only CLI mutations over raw JSON string-replacement to avoid destroying the `index` sorting invariants.
