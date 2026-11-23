---
name: hydrate
description: Fast disambiguation index -- distill short conceptual queries from an ask, run parallel semantic searches, and return a concise shortlist of IDs with one-line snippets, flagging potential overlap with unfinished tasks; the PKB custodian (Pauli) runs it. Does not open bodies, synthesise, or write to the graph.
---

# Hydrate

Fast disambiguation index. Distill short conceptual queries from an ask, locate matching graph entries via semantic search, and return a curated shortlist of IDs. The PKB custodian (Pauli) runs this skill; other agents requiring disambiguation or overlap checking route the request to the custodian rather than querying the PKB directly with raw asks. Do not read full bodies, summarise context, or write to the graph.

## Preconditions

Access the PKB strictly through PKB MCP tools at summary, snippet, or metadata detail only -- never read full node bodies, and never attempt direct filesystem access. If PKB tools fail, halt and report (`halt-on-failure`).

```
$ARGUMENTS
```

## Workflow

1. **Strip framing and decompose**: Strip conversational framing, personal preambles, channel wrappers, and negative or incidental references to unrelated note or task IDs. Split multi-topic asks into distinct conceptual facets and identify 2-3 terms or facets carrying ambiguity (project names, technical mechanisms, shorthand references).
2. **Search with distilled conceptual queries**: Never pass raw or verbatim prompts to `pkb_search`. Formulate 1-3 concise conceptual queries (5-15 words) per facet or term expressing the substantive system behavior, architectural mechanism, or domain intent (avoiding incidental hyphens, underscores, or digits unless targeting a known literal symbol), and run them in parallel using PKB semantic search.
   - Budget approximately six calls; stop when two consecutive queries return no new results.
3. **Filter to a shortlist**: Retain only hits that directly affect caller planning. Discard generic vocabulary matches.
4. **Emit flat shortlist in prose Argdown (`ida:premise-check`)**: Return agent-to-agent results solely as unfenced prose Argdown blocks -- lead with any **overlapping incomplete task** in `Main Conclusion` and premise `(1)`, then put one flat, scannable line per retained match (`<id> [<kind/status>] -- <what it is, <=12 words> -- <relevance>; query '<q>'`) or bounded zero-hit query (`0 hits for PKB search '<q>'`) as its own numbered premise so every ID and negative claim carries its exact query source.
