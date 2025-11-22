# Task: Deny Rules Configuration

**Date**: 2025-11-22 **Stage**: 2 (Scripted Tasks) **Priority**: P2

## Problem Statement

**What manual work are we automating?**

Not automation per se—this is a security and integrity configuration. The framework is installed in `~/.claude/` via symlinks from `$AOPS/`. Without deny rules, agents can read/write to `~/.claude/` directly, bypassing the authoritative source at `$AOPS/`.

**Why does this matter?**

- **Single Source of Truth**: AXIOMS require one authoritative location for each piece of information. `$AOPS/` is the authoritative source for the framework; `~/.claude/` is a deployment target only.
- **Integrity Protection**: Direct writes to `~/.claude/` would:
  - Create divergence between source and deployment
  - Bypass version control (git history in `$AOPS/`)
  - Break the symlink model (overwriting a symlink removes it)
- **Principle Enforcement**: Deny rules enforce AXIOM #11 (Skills are Read-Only) and #12 (Trust Version Control) at the tool level.

**Who benefits?**

Nic—prevents accidental corruption of framework installation and enforces proper change management through `$AOPS/`.

## Success Criteria

**The configuration is successful when**:

1. Claude Code cannot read framework files from `~/.claude/` or `./.claude/` paths (must use `$AOPS/` paths)
2. Claude Code cannot write to any `.claude/` directory
3. Existing allow rules continue to function
4. No impact on MCP servers, hooks, or skills that operate correctly

**Quality threshold**: Binary pass/fail—either the deny rules prevent the operations or they don't.

## Scope

### In Scope

- Document existing deny rules (currently empty: `"deny": []`)
- Add deny rules for `.claude/` directory access
- Document rationale for each deny rule
- Update settings files in appropriate locations

### Out of Scope

- Deny rules for other sensitive paths (can be added later)
- Hook-based permission checking (defer to future)
- Testing framework compliance (integration test out of scope—verify manually)

**Boundary rationale**: This task configures existing Claude Code permission functionality. No code to write, just settings configuration with clear documentation.

## Dependencies

### Required Infrastructure

- Claude Code permission system (exists)
- Settings files at `.claude/settings.local.json` (exist in both repos)

### Data Requirements

- None—pure configuration

## Implementation (Completed 2025-11-22)

### Framework-Managed Settings File

**Location**: `$AOPS/config/claude/settings.json` (symlinked to `~/.claude/settings.json`)

**Commit**: `7df3f5d` - feat(config): Add deny rules for .claude directory access

### Updated Deny Rules

```json
{
  "permissions": {
    "allow": ["Read"],
    "deny": [
      "Write(/data/tasks/**)",
      "Write(*/data/tasks/**)",
      "Edit(/data/tasks/**)",
      "Edit(*/data/tasks/**)",
      "Bash(rm */data/tasks/**)",
      "Bash(mv */data/tasks/**)",
      "Bash(cp */data/tasks/**)",
      "Read(**/.claude/**)",
      "Write(**/.claude/**)",
      "Edit(**/.claude/**)"
    ]
  }
}
```

## Proposed Deny Rules

### Rule Set

```json
{
  "permissions": {
    "deny": [
      "Read(**/.claude/**)",
      "Write(**/.claude/**)",
      "Edit(**/.claude/**)"
    ]
  }
}
```

### Justification

| Rule | Purpose | AXIOM Reference |
|------|---------|-----------------|
| `Read(**/.claude/**)` | Force agents to read framework source from `$AOPS/`, not deployment location | #7 Self-Documenting, #12 Trust Version Control |
| `Write(**/.claude/**)` | Prevent bypassing version control; all changes must go through `$AOPS/` | #8 DRY, #11 Skills are Read-Only, #12 Trust Version Control |
| `Edit(**/.claude/**)` | Same as Write—prevent direct modification of deployed framework | Same as Write |

### Pattern Explanation

- `**/.claude/**` matches:
  - `~/.claude/` (user-level framework installation)
  - `./.claude/` (project-level settings)
  - Any `.claude/` directory in any path

### What This Does NOT Prevent

- Reading/writing `$AOPS/` directly (desired—that's the authoritative source)
- Hook execution (hooks run via shell, not Claude Code tools)
- MCP server operation (MCP servers are external processes)

## Integration Test Design

**Test must be designed BEFORE implementation**

### Test Setup

No setup required—use existing session.

### Test Execution

Attempt operations that should be denied:

```bash
# After applying deny rules, these should fail:
# 1. Read from ~/.claude/
#    Claude should be unable to use Read tool on ~/.claude/settings.json
#
# 2. Write to ~/.claude/
#    Claude should be unable to use Write tool on ~/.claude/test.txt
#
# 3. Edit in ./.claude/
#    Claude should be unable to use Edit tool on ./.claude/settings.local.json
```

### Test Validation

Manual verification:
1. Ask Claude to read `~/.claude/settings.json` → Should be denied
2. Ask Claude to write a test file to `~/.claude/` → Should be denied
3. Verify Claude CAN still read from `$AOPS/` → Should work

### Success Conditions

- [ ] Read operations on `.claude/` paths denied
- [ ] Write operations on `.claude/` paths denied
- [ ] Edit operations on `.claude/` paths denied
- [ ] Read operations on `$AOPS/` continue to work
- [ ] Write operations on `$AOPS/` continue to work
- [ ] Existing allow rules still function

## Implementation Approach

### High-Level Design

1. Add deny rules to appropriate settings file(s)
2. Verify deny rules take effect
3. Document configuration

### Where to Configure

**Option A**: Per-project settings (`/home/nic/writing/.claude/settings.local.json`)
- Pros: Specific to this project
- Cons: Must repeat in every project

**Option B**: User-level settings (`/home/nic/dotfiles/.claude/settings.local.json`)
- Pros: Applies to all projects using this dotfiles setup
- Cons: May need project-specific overrides

**Recommendation**: Configure in user-level dotfiles (`settings.local.json`), as this protection should apply universally across all projects.

### Implementation Steps

1. Edit `/home/nic/dotfiles/.claude/settings.local.json` to add deny rules
2. Verify symlink propagation (dotfiles → `~/.claude/`)
3. Test in new session

## Failure Modes

### What Could Go Wrong?

1. **Failure mode**: Deny rules too broad, break legitimate operations
   - **Detection**: Operations that should work start failing
   - **Impact**: Workflow disruption
   - **Prevention**: Use specific patterns, test thoroughly
   - **Recovery**: Remove deny rules, restart session

2. **Failure mode**: Deny rules don't apply (wrong syntax)
   - **Detection**: Protected operations still succeed
   - **Impact**: Security gap persists
   - **Prevention**: Verify syntax against Claude Code documentation
   - **Recovery**: Correct syntax, restart session

3. **Failure mode**: Pattern doesn't match as expected
   - **Detection**: Some paths protected, others not
   - **Impact**: Partial protection
   - **Prevention**: Test multiple path variations
   - **Recovery**: Adjust pattern

## Open Questions

1. **Does `**/.claude/**` glob work in Claude Code deny rules?**
   - Examples in hooks_guide.md show patterns like `Read(/etc/**)` and `Read(./.env.*)`
   - Need to verify double-star glob behavior

2. **Should we also deny Bash operations that touch `.claude/`?**
   - E.g., `Bash(cat ~/.claude/*)`, `Bash(rm ~/.claude/*)`
   - May be overkill for now—Bash operations are more visible

3. **Does tilde expansion work in deny patterns?**
   - hooks_guide.md notes "Tilde expansion (~) works correctly"
   - May need to use both `~/.claude/**` and `**/.claude/**` patterns

## Notes and Context

### Related AXIOMS

- **#7 Self-Documenting**: Framework source at `$AOPS/` is documentation-as-code
- **#8 DRY**: One source (`$AOPS/`), one deployment target (`~/.claude/`)
- **#11 Skills are Read-Only**: Skills distributed read-only, no writes to deployment
- **#12 Trust Version Control**: All changes via git in `$AOPS/`, not direct edits

### Related Documentation

- [[hooks_guide.md]] - Permission patterns and examples
- AXIOMS.md - Foundational principles requiring this protection

---

## Completion Checklist

Before marking this task as complete:

- [ ] Deny rules added to settings file
- [ ] Deny rules tested (read/write/edit operations blocked)
- [ ] Existing functionality verified (allow rules still work)
- [ ] Documentation complete (this spec serves as documentation)
- [ ] No workflow disruption observed

## Next Steps After Implementation

1. Monitor for false positives (legitimate operations blocked)
2. Consider adding additional deny rules for other sensitive paths:
   - `.env` files
   - `secrets/` directories
   - Production configs
