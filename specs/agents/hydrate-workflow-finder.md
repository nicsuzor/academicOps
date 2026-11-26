---
title: Hydrate as an MCP Workflow Finder
status: draft
---

# Hydrate as an MCP Workflow Finder

Expose `/hydrate` as a fast, parameterized MCP endpoint on the PKB MCP server so an agent receiving an instruction can immediately discover which workflows to apply (`workflows` mode, default) or retrieve separated active and background context (`general` mode).

## User stories

### US-1 Fast workflow discovery from an instruction

As a worker agent, I want to query the MCP server with an instruction and immediately receive up to three matching workflows ordered from most specific to most general, so that I know which steps to follow without reading the full workflow library.

- **AC-1.1** Given a free-text `query` and `mode: "workflows"` (or `mode` omitted, since `"workflows"` is the default), when the endpoint is called, then it searches only workflow and workflow-template documents (both PKB `type: template` nodes and universal workflow-library files).
- **AC-1.2** Given matching workflows, when the response is returned in `workflows` mode, then it contains at most 3 results ordered most-specific first, followed by broader workflows that wrap it, with no server-side workflow composition.
- **AC-1.3** Given a warm server, when `workflows` mode runs, then it completes within 100 ms (skipping cross-encoder reranking or using a tight deadline budget).

### US-2 General hydration with active-vs-background separation

As an agent, I want a `general` hydration mode that separates active in-progress work from background knowledge, so that I can distinguish ongoing tasks from reference notes and completed or queued items.

- **AC-2.1** Given a free-text `query` and `mode: "general"`, when the endpoint is called, then results distinguish `in_progress` tasks from background items (notes, knowledge documents, and other tasks) related to the query.

### US-3 Spec-aligned MCP exposure across direct and portal clients

As a framework operator, I want the workflow finder exposed via the current MCP specification's native parameterized mechanism and compatible with Code Mode portals, so that both direct MCP clients and portal-routed agents can invoke it.

- **AC-3.1** Given a direct MCP client, when it calls `prompts/list`, then a `hydrate` prompt appears with `workflows` mode as the core of its description and arguments `query` (required string) and `mode` (`"workflows"` | `"general"`, default `"workflows"`).
- **AC-3.2** Given a direct MCP client calling `prompts/get` for `hydrate`, when `query` and optional `mode` are supplied, then the server executes the lookup and returns the formatted workflow or general results in `PromptMessage` content.
- **AC-3.3** Given a Code Mode portal client that only sees `tools/list`, when the tool surface is enabled, then `hydrate` (accepting `query` and `mode`) is callable via `tools/call` using the same backend handler.

## Design

### MCP specification choice

Evaluated the 2026 MCP specification mechanisms for server-suggested skills, prompts, and queries:

1. **MCP Skills extension (`io.modelcontextprotocol/skills`, SEP-2640, `skills/list` + `skills/get` + `skill://` URIs)**: Designed for static, content-addressed `SKILL.md` directories with SHA-256 file manifests fetched via `resources/read`. It has no `query` or `mode` parameters, and `"dynamic"` skill manifests omit SHA-256 integrity guarantees (which hosts may reject). It is suited for serving static skill files (such as `ida:hydrate` itself), not for parameterized query lookup.
2. **MCP Prompts (`prompts/list` + `prompts/get`)**: The native MCP primitive for parameterized, server-suggested commands and workflow recipes (`Prompt` with `PromptArgument`s, returning `PromptMessage`s). The PKB MCP server already declares `prompts` capability and implements `prompts/list` and `prompts/get`.
3. **MCP Tools (`tools/call`)**: Required alongside `prompts/get` for Code Mode MCP portals that only aggregate and dispatch `tools` (`tools/list` / `tools/call`) rather than forwarding `prompts/*`.

Accordingly, the v1 experimental design exposes `hydrate` as an **MCP Prompt** (`prompts/list` and `prompts/get` executing the search server-side rather than returning static tool-call instructions) **and** publishes `hydrate` on `tools/list` / `tools/call` with the same `query` and `mode` schema so portal-routed agents can experiment immediately.

### Parameters

| Parameter | Type | Required | Default | Description |
| - | - | - | - | - |
| `query` | `string` | Yes | - | Free-text instruction or search query (capped at 8,192 bytes). |
| `mode` | `enum` (`"workflows"`, `"general"`) | No | `"workflows"` | `"workflows"` searches workflow/template files only (<= 3 results, most specific first); `"general"` returns background notes/tasks separated from `in_progress` tasks. |

### Ranking and ordering in `workflows` mode

- **Corpus**: Include PKB documents with `type: template` and universal workflow files from the plugin workflow library (`plugins/ida/skills/workflow-library/workflows/*.md`). Because universal workflow files currently live outside the PKB vault, the PKB server needs either a configured workflow directory path or vault sync so both tiers are indexed in one fast pass.
- **Specificity ordering**: Start with a simple, tunable heuristic for v1 experimentation: rank by semantic/BM25 relevance, and break ties or order within the top 3 so narrower/leaf workflows (e.g., non-composite templates or higher-specificity matches) precede broader/composite wrappers (e.g., templates tagged `composite` or with broader scope). Return at most 3 items (id, title, tier/scope, one-line description/pointer).
- **No server-side composition**: The server returns the relevant workflows only; assembling them into a composite execution plan remains the calling agent's job.

### Grouping in `general` mode

- Run standard PKB search/hydration and partition returned items into two explicit sections:
  - **In-progress tasks**: `type: task` with `status: in_progress`.
  - **Background**: `note`, `knowledge`, and non-`in_progress` tasks.
