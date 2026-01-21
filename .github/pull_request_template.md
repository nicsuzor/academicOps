## Summary

<!-- 1-3 bullet points describing what this PR does -->

## Test plan

<!-- How was this tested? -->

## Checklist

### General

- [ ] Changes are focused and minimal (no scope creep)
- [ ] Commit messages follow conventions
- [ ] No hardcoded paths or secrets

### If adding/modifying tests (H37)

- [ ] Tests verify **actual behavior**, not surface patterns
- [ ] No keyword matching: `any(x in text for x in list)` ❌
- [ ] No weak assertions: `assert len(output) > 0` without structural check ❌
- [ ] Real framework prompts used, not contrived examples
- [ ] For LLM behavior: demo test exists showing full untruncated output
- [ ] Test can NOT pass on wrong behavior

### If modifying framework infrastructure

- [ ] Changes traced to axiom/heuristic
- [ ] enforcement-map.md updated if adding enforcement
- [ ] INDEX.md updated if adding files

🤖 Generated with [Claude Code](https://claude.com/claude-code)
