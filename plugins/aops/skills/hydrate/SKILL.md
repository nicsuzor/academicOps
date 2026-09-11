---
name: hydrate
description: Fast disambiguation index--extract ambiguous terms from an ask, run parallel semantic searches, and return a concise shortlist of IDs with one-line snippets, flagging potential overlap with unfinished tasks. Does not open bodies, synthesise, or write to the graph.
---

# Hydrate

Fast disambiguation index. Identify ambiguous terms in an ask, locate matching graph entries via semantic search, and return a curated shortlist of IDs. Do not read full bodies, summarise context, or write to the graph.

## Preconditions

Access the PKB strictly through MCP tools (`mcp__plugin_pkb_services__pkb__search`). If tools fail, halt and report (`halt-on-failure`); never attempt direct filesystem access.

```
$ARGUMENTS
```

## Workflow

1. **Extract ambiguous terms**: Identify 2-3 terms carrying ambiguity (project names, technical terms, shorthand references).
2. **Search with varied phrasing**: Run 2-3 phrasing variants per term using MCP search tools.
   - Always pass `include_subtasks: true` on `task_search` to avoid missing open work.
   - Budget approximately six calls; stop when two consecutive queries return no new results.
3. **Filter to a shortlist**: Retain only hits that directly affect caller planning. Discard generic vocabulary matches.
4. **Emit flat shortlist**: Group by kind (tasks, knowledge, terms), omitting empty kinds:
   ```markdown
   - `<id>` -- <what it is, <=12 words> -- <relevance to ask>
   ```
   If a search yields nothing, state the exact queries and scope: `no prior task (task_search, include_subtasks: true: '...', 0 hits)`.

### Possible Overlap Flag

If an **incomplete task** appears to cover ground shared with the ask, lead with it at the top:

```markdown
**Possible overlap** -- decide before creating anything new:

- `<id>` [<status>] -- <title> -- overlaps on <shared scope or touched files>
```
