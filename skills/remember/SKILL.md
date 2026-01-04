---
name: remember
description: Write knowledge to markdown AND sync to memory server. MUST invoke - do not write markdown directly.
allowed-tools: Read,Write,Edit,mcp__memory__store_memory
version: 1.0.0
---

# Remember Skill

Persist knowledge to the framework's memory system.

## Why You MUST Invoke This Skill

You know how to write markdown. But there's a **sync step you cannot do directly**.

The framework uses a memory server that indexes `$ACA_DATA/`. When you write markdown, you must ALSO add it to the memory server for semantic search to work. This skill handles both steps.

**If you skip this skill**: The markdown file exists but isn't searchable. Future agents won't find it via `mcp__memory__retrieve_memory`.

## When to Use

- Capturing a decision, learning, or observation
- Recording something that should persist across sessions
- Any time you would write to `$ACA_DATA/` for knowledge purposes

## File Locations

| Content | Location |
|---------|----------|
| General notes | `$ACA_DATA/context/` |
| Goals | `$ACA_DATA/goals/` |
| Project metadata | `$ACA_DATA/projects/<name>.md` |
| Project details | `$ACA_DATA/projects/<name>/` |
| Session notes | `$ACA_DATA/sessions/` |
| Tasks | Delegate to [[tasks]] skill |

### PROHIBITED Content

**NEVER create these in $ACA_DATA** - they belong elsewhere:

| Content Type | Where It Belongs | Why |
|--------------|------------------|-----|
| Specs/specifications | `$AOPS/specs/` | Framework code, version controlled |
| Skills | `$AOPS/skills/` | Framework code |
| Hooks | `$AOPS/hooks/` | Framework code |
| Episodic content | GitHub Issues | Per [[AXIOMS]] #28, [[H26]] |
| `learning/`, `bugs/`, `experiments/`, `decisions/` | GitHub Issues | Episodic, not current state |

**When remembering framework decisions** (specs, heuristics, design choices):
- **DO**: Store to memory server only (for semantic retrieval)
- **DO NOT**: Create markdown files in $ACA_DATA - the authoritative source is in $AOPS

**DO NOT create arbitrary directories** (e.g., `tech/`, `dev/`, `tools/`, `specs/`). Project-related notes go in `projects/<project-name>/`.

## Knowledge Graph Integration (MANDATORY)

**Every note must connect to the graph.** Isolated notes are invisible in Obsidian and useless for navigation.

### Pre-Save Checklist

Before writing ANY file to `$ACA_DATA/`, verify:

| File Type | Required Links (in body, not frontmatter) |
|-----------|-------------------------------------------|
| **Project file** (`projects/*.md`) | Opening paragraph MUST wikilink to the [[goal]] it supports |
| **Project file** | MUST have `## Connections` section with related [[projects]] |
| **Note** (`context/*.md`) | MUST wikilink to at least one [[project]] or [[goal]] |
| **Goal file** | MUST list projects that support it |

### Project Template

**Note**: Wikilinks in YAML frontmatter do NOT create Obsidian graph connections without plugins. Links MUST appear in the document body to be visible in the graph.

```markdown
---
title: Project Name
type: project
tags: [relevant, tags]
---

# Project Name

[Opening paragraph describing project]. Supports [[Goal Name]] through [how].
```

The goal link MUST be in the body text, not just frontmatter.

### Connections Section Template

Every project file needs a `## Connections` section:

```markdown
## Connections

**Goals**: [[Goal Name]] (how this project serves it)

**Related Projects**:
- [[other-project]] - relationship description
- [[another-project]] - shared infrastructure/themes

**Themes**: [[concept]], [[another-concept]]
```

### Finding Links

Before creating a file, search for related content:
1. `mcp__memory__retrieve_memory(query="[topic]")` - find related notes
2. Read `$ACA_DATA/goals/goals.md` - which goal does this serve?
3. Read `$ACA_DATA/projects/projects.md` - what projects relate?

**If you cannot identify at least one goal link**: ASK the user which goal this serves before proceeding.

## Workflow

1. **Search BOTH sources**:
   - Memory server: `mcp__memory__retrieve_memory(query="topic keywords")`
   - Specs directory: `Glob(pattern="$ACA_DATA/projects/*/specs/*.md")` then grep for topic
2. **If match found in EITHER**: AUGMENT existing file (don't create new)
3. **If no match in either**: Create new TOPICAL file (not session/date file)
4. **VERIFY graph integration** per checklist above before saving

### Multi-Location Principle

**Don't over-summarize.** Content often belongs in multiple locations at different levels of detail:

| Location | Content Level |
|----------|---------------|
| Project index (`project.md`) | Summary observations, current strategic position |
| Detailed notes (`project/topic.md`) | Full context, reasoning, personal reflections |
| Memory server | Key facts for semantic retrieval |

**Example**: A plenary reflection belongs BOTH in the project index (strategic summary) AND the meeting notes (full reflection with emotional context, reasoning, history).

When in doubt, save to both. Lost detail is worse than mild redundancy.

4. **Write markdown file** with proper frontmatter:
```markdown
---
title: [Descriptive Title]
type: [note|learning|decision]
tags: [relevant, tags]
created: YYYY-MM-DD
---

# Title

Content here.
```

3. **Add to memory server**:
```
mcp__memory__store_memory(
  content="[Full content or key excerpt]",
  metadata={
    "tags": "tag1,tag2",
    "type": "note",
    "source": "[file path]"
  }
)
```

## Background Invocation (Seamless Capture)

For seamless capture that doesn't interrupt workflow, spawn a background agent:

```
Task(
  subagent_type="general-purpose",
  model="haiku",
  run_in_background=true,
  description="Remember: [summary]",
  prompt="
Invoke Skill(skill='remember') to persist this observation:

Content: [what to remember]
Type: [note|learning|decision]
Tags: [relevant tags]
"
)
```

**When to use background invocation**:
- End of substantial work (Stop event trigger)
- After completing a task (TodoWrite trigger)
- Any time capture should not interrupt user flow

**When to use direct `Skill(skill="remember")`**:
- Need result before proceeding
- User explicitly asks to remember something

## Arguments

- `content`: What to remember (required)
- `type`: note | learning | decision (default: note)
- `tags`: Comma-separated tags for categorization

## Output

Report:
- File written: `[path]`
- Memory stored: `[hash or confirmation]`

## Workflows

- [[workflows/capture]] - Session mining and silent extraction
- [[workflows/validate]] - Check format compliance
- [[workflows/prune]] - Clean low-value files

## Open Questions

We don't yet know the full sync mechanism between markdown files and the memory server. This skill will be updated as we learn. For now: write markdown, then store in memory.
