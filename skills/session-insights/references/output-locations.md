---
category: ref
---

# Output Locations

| Artifact               | Location                                                                 | Format                                   |
| ---------------------- | ------------------------------------------------------------------------ | ---------------------------------------- |
| Transcripts (full)     | `$ACA_DATA/sessions/claude/YYYYMMDD-{project}-{sessionid}-*-full.md`     | Markdown with YAML frontmatter           |
| Transcripts (abridged) | `$ACA_DATA/sessions/claude/YYYYMMDD-{project}-{sessionid}-*-abridged.md` | Markdown with YAML frontmatter           |
| Per-session mining     | `$ACA_DATA/dashboard/sessions/{session_id}.json`                         | JSON (one per session)                   |
| Daily summary          | `$ACA_DATA/sessions/YYYYMMDD-daily.md`                                   | Markdown with accomplishments by project |
| Dashboard synthesis    | `$ACA_DATA/dashboard/synthesis.json`                                     | JSON for dashboard rendering             |
| Learning observations  | GitHub Issues (nicsuzor/academicOps)                                     | Via `/log` skill → Issues                |

## Output Summary Template

```
## Session Insights - YYYY-MM-DD

### Transcripts
- Generated: N | Skipped: M

### Daily Summary
- Updated: sessions/YYYYMMDD-daily.md

### Learnings
- insight ...
- insight ...
```
