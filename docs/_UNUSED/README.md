# Modular Documentation Chunks

**Status:** Experimental (Phase 2 of Issue #111)

These are discrete, reusable methodology chunks extracted from _UNCHECKED files.

## Available Chunks

- `FAIL-FAST.md` - Fail-fast philosophy for agents and infrastructure
- `GIT-WORKFLOW.md` - Git submodule workflow and conventional commits

## Usage Pattern

**In agent instructions:**

```markdown
Load methodologies:

- @bot/docs/_CHUNKS/FAIL-FAST.md
- @bot/docs/_CHUNKS/GIT-WORKFLOW.md
```

## Promotion Process (Phase 3)

Chunks move to `docs/` (canonical) after successful experimental integration:

1. Create experiment issue with success metrics
2. Link chunk in agent instruction
3. Track metrics over 2-week evaluation
4. If successful: Promote to `docs/`
5. If failed: Move to `docs/_UNUSED/`

## Chunk Criteria

- ✅ Single responsibility (one concept)
- ✅ Self-contained (no dependencies)
- ✅ <100 lines
- ✅ Reusable across contexts
- ✅ No duplication with other chunks
