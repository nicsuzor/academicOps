# Workflow Index - Model Agnostic

All workflows are model-agnostic. Store in `/docs/workflows/`.

## Active Workflows

- daily-planning.md - Daily task organization
- weekly-review.md - Weekly progress review
- project-creation.md - New project inception
- idea-capture.md - Quick idea processing

**Note**: Strategic planning is handled by the strategist agent (see `bot/agents/strategist.md`), not a standalone workflow.

## Workflow Patterns

- ALL agents use same workflows
- Model-specific config ONLY in .gemini/ or .claude/
- Instructions are universal, not model-specific

## Cross-Workflow Lessons

When one workflow improves, check if pattern applies to others.
