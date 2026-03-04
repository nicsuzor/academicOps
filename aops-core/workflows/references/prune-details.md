# Prune Workflow Detailed Procedures

Detailed criteria, patterns, and strategies for pruning the knowledge base.

## Classification Criteria

### DELETE (No extraction)

Files with zero lasting value: raw transcripts, scheduling, noise, orphaned coordination, duplicates.
**Test**: Would you ever search for this? If "no way" → DELETE.

### CONSOLIDATE (Time-based logs)

Guidelines for consolidating logs into an organized knowledge base.

- **SSoT**: Each project should have ONE main file; avoid hunting through multiple files.
- **Deletable**: Completed session logs, superseded reports, executed plans, resolved issues, abandoned ideas, stubs.
- **Keep Separate**: Meeting records, file notes, user-written records, main project file, active investigations.

### EXTRACT_DELETE

Files with mostly noise but some facts worth keeping: contact roles, project outcomes, event attendees.
**Process**: Identify target, extract facts as observations, append to target, delete source.
**Test**: Is there ONE fact worth adding to another file? Extract it, then DELETE.

### KEEP

Substantive prose, research findings, strategic context, collaboration history.
**Test**: Is this actual prose, meeting/file notes, or substantive content? → KEEP.

## Execution Strategy

### Phase 1: Discovery

1. Count total files to establish baseline.
2. Identify main directories/projects to analyze.
3. Spawn parallel agents for different areas to produce recommendations.

### Phase 2: Triage by Category

Classify each file (DELETE | EXTRACT_DELETE | KEEP) based on content analysis.

- **Green Flags (KEEP)**: Main project files, reference docs (Architecture, Spec), learning logs, recent work.
- **Consolidate (THEN DELETE)**: Session logs, phase reports, implementation plans.

## Decision Tree

```
Is it substantive prose/notes?
├─ Yes → KEEP
└─ No → Is there any fact worth saving?
         ├─ Yes → EXTRACT_DELETE
         └─ No → DELETE
```

## Safety Protocols

- All deletions via `git rm` (recoverable).
- Commit after each batch to ensure progress is saved.
- Use `git checkout` if recovery is needed.
