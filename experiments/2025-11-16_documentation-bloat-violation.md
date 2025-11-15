# Experiment: Enforce MINIMAL Documentation Principle

**Date**: 2025-11-16
**Commit**: ab66ae9 (fix commit after violation)
**Issue**: Creating new issue
**Pattern**: Scope Creep + Violation of MINIMAL Principle

## Violation Summary

**What Happened**: Agent created 340-line INSTALLATION-GUIDE.md when user asked to "teach me how to install the deployment package"

**What Should Have Happened**: Answer with 2 sentences in README (which is exactly what user corrected to)

**Evidence**:
- Created: INSTALLATION-GUIDE.md (340 lines)
- User response: "oh no, i hate installation guides. you know that! i hate long documents! i want things to be obvious, and where it's necessary to have documentation, I want that as short as possible. Why would it take more than two sentences to tell me how to install something? put it in the readme, and don't make this mistake again"
- Fixed: Deleted guide, added 2-sentence installation section to README

## Axioms Violated

1. **CLAUDE.md**: "the watchword is MINIMAL. We are not just avoiding bloat, we are ACTIVELY FIGHTING it"
2. **Axiom 1 "DO ONE THING"**: User asked question → should answer briefly, then stop
3. **Axiom 7 "Self-Documenting"**: "never make separate documentation files"
4. **Axiom 8 "DRY, Modular, Explicit"**: Installation already documented in package's INSTALL.md
5. **ACCOMMODATIONS.md**: "Avoid over-engineering", "Values efficiency... over lengthy explanation"

## Behavioral Pattern

**Pattern**: Scope Creep (Pattern #2)
- User asks question → Agent launches into solution before answering
- Created comprehensive guide instead of brief answer
- Ignored established preference for minimal documentation

**Related Issues**:
- #132: Agent fails to answer direct questions
- #111: Enforce modular documentation architecture (DRY)

## Root Cause Analysis

Why did this happen?
1. **Misinterpreted user intent**: "teach me" → created teaching document, not brief explanation
2. **Ignored established preferences**: User has explicitly stated hatred of long docs
3. **Defensive behavior**: Created "comprehensive" guide "just in case"
4. **Failed to check existing documentation**: INSTALL.md already exists in packages

## Hypothesis

Adding enforcement at SCRIPTS or HOOKS level can prevent creation of documentation files that violate MINIMAL:

**Option 1: Pre-commit hook**
- Detect new .md files
- Check line count
- Warn if >100 lines without justification
- Block if violates naming conventions (e.g., "*-GUIDE.md")

**Option 2: validate_tool.py enhancement**
- Block Write tool for files matching bloat patterns
- Suggest README section instead
- Check for duplication with existing docs

**Option 3: INSTRUCTIONS enhancement** (lowest priority)
- Add explicit rule to AXIOMS.md about documentation brevity
- Add to aops skill documentation review checklist

## Implementation

Following enforcement hierarchy: SCRIPTS > HOOKS > CONFIG > INSTRUCTIONS

### Recommended: HOOKS (validate_tool.py)

Add to `hooks/validate_tool.py`:

```python
# Block creation of bloated documentation files
if tool_name == "Write":
    file_path = args.get("file_path", "")
    content = args.get("content", "")

    # Block *-GUIDE.md files
    if file_path.endswith("-GUIDE.md") or "GUIDE.md" in file_path:
        return {
            "continue": False,
            "systemMessage": (
                "❌ Blocked: *-GUIDE.md files violate MINIMAL principle.\n"
                "Installation instructions belong in README (2 sentences max).\n"
                "User explicitly: 'I hate installation guides. I hate long documents.'\n"
                "Add to README.md instead."
            )
        }

    # Warn on large .md files (>200 lines)
    if file_path.endswith(".md") and len(content.split("\n")) > 200:
        return {
            "continue": False,
            "systemMessage": (
                f"❌ Blocked: {len(content.split('\\n'))} lines exceeds MINIMAL threshold.\n"
                "Documentation should be concise. Consider:\n"
                "- Adding brief section to README.md\n"
                "- Splitting into focused chunks in docs/chunks/\n"
                "- Questioning if this documentation is necessary"
            )
        }
```

### Alternative: Pre-commit hook (SCRIPTS level)

Create `scripts/check_documentation_bloat.py`:
- Run as pre-commit hook
- Check for new .md files
- Flag files >200 lines
- Block *-GUIDE.md files

## Expected Results

1. Agent cannot create *-GUIDE.md files
2. Agent warned when creating >200 line .md files
3. Forces agent to use README or docs/chunks/ instead
4. Prevents future violations of MINIMAL principle

## Success Criteria

- [ ] Hook implemented
- [ ] Tested with attempt to create INSTALLATION-GUIDE.md (should block)
- [ ] Tested with attempt to create large .md file (should warn)
- [ ] Documentation updated in validate_tool.py comments
- [ ] Pattern not observed in next 10 sessions

## Decision

**Choose one**:
- [ ] Keep change (implement hook enforcement)
- [ ] Revert (instructions-only approach)
- [ ] Iterate (different enforcement mechanism)

---

**Next Step**: Create GitHub issue to track enforcement implementation
