# Skill Dependency Map

Generated: 2026-01-11 for ns-9ka (Prerequisite: Skill Dependency Mapping)

## Summary

- **Total skills**: 28
- **Skills with outbound dependencies**: 6
- **Skills invoked by others**: 8
- **Standalone skills**: 20

## Bidirectional Map

### audit

- **invokes**: framework, flowchart
- **invoked-by**: /audit-framework, framework

### daily

- **invokes**: tasks
- **invoked-by**: /task-next

### extractor

- **invokes**: remember
- **invoked-by**: (none)

### framework

- **invokes**: audit, remember, transcript
- **invoked-by**: audit, /meta, /learn

### learning-log

- **invokes**: transcript
- **invoked-by**: /learn, /log

### remember

- **invokes**: (self-reference in examples only)
- **invoked-by**: extractor, framework, /qa

### flowchart

- **invokes**: (none)
- **invoked-by**: audit

### tasks

- **invokes**: (none)
- **invoked-by**: daily, /email, /q

### transcript

- **invokes**: (none)
- **invoked-by**: framework, learning-log, /learn

### excalidraw

- **invokes**: (none)
- **invoked-by**: /task-viz

### python-dev

- **invokes**: (none - self-references are examples)
- **invoked-by**: (none directly, but implicitly via prompt-hydrator)

### qa-eval

- **invokes**: (none - self-reference is example)
- **invoked-by**: (none)

## Standalone Skills (No Dependencies)

These skills neither invoke nor are invoked by other skills:

- analyst
- convert-to-md
- dashboard
- debug-headless
- fact-check
- feature-dev
- garden
- ground-truth
- introspect
- osb-drafting
- pdf
- review
- review-training
- session-insights
- training-set-builder

## Command → Skill Invocations

| Command          | Invokes Skill(s)                    |
| ---------------- | ----------------------------------- |
| /audit-framework | audit                               |
| /email           | tasks                               |
| /learn           | framework, transcript, learning-log |
| /log             | learning-log                        |
| /meta            | framework                           |
| /q               | tasks                               |
| /qa              | remember                            |
| /reflect         | log (alias for learning-log)        |
| /task-next       | daily                               |
| /task-viz        | excalidraw                          |

## Consolidation Risk Assessment

Skills that are safe to consolidate (no inbound dependencies):

- extractor (only invokes remember)
- All standalone skills listed above

Skills requiring careful consolidation (have inbound dependencies):

- **remember**: invoked by extractor, framework, /qa - core infrastructure
- **tasks**: invoked by daily, /email, /q - task management hub
- **transcript**: invoked by framework, learning-log, /learn - session analysis
- **framework**: invoked by audit, /meta, /learn - central routing
- **audit**: invoked by /audit-framework, framework - governance

## Notes

1. Self-references in skill documentation (e.g., python-dev showing how to invoke itself) are not counted as dependencies
2. The prompt-hydrator agent dynamically routes to skills based on domain signals, creating implicit dependencies not captured here
3. Commands are the primary entry points; most skills are invoked via commands rather than other skills
