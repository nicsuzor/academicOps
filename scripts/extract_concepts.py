#!/usr/bin/env python3
"""
Extract concepts from bot repo into writing repo concepts/ directory.

This script:
1. Parses AXIOMS.md to extract core principles
2. Creates concept nodes in concepts/axioms/ with WikiLinks
3. Establishes connections between related concepts
4. Uses Basic Memory MCP to create graph-native notes

Usage:
    python extract_concepts.py [--dry-run]
"""

import sys
from pathlib import Path
from typing import Dict

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# Core concept definitions extracted from AXIOMS.md
AXIOM_CONCEPTS = [
    {
        "id": "do-one-thing",
        "title": "Axiom #1: Do One Thing",
        "description": "Complete the task requested, then STOP. Never scope creep.",
        "content": """## Principle

Complete the task requested, then STOP.

## Rules

- User asks question → Answer it, then stop
- User requests task → Do it, then stop
- Find related issues → Report them, don't fix them

## Related Concepts

- [[no-excuses]] - Don't rationalize doing extra work
- [[verify-first]] - Check what was actually requested
- [[hypothesis-driven]] - Ask before expanding scope

## Examples

✅ **CORRECT**: "Task complete. Found 3 related issues: [list]. Should I fix these?"
❌ **WRONG**: "Task complete. Also fixed these 3 related issues I found..."

## Why It Matters

Prevents scope creep, maintains predictability, respects user's decision-making authority.
""",
        "tags": ["axiom", "core", "scope", "workflow"],
        "related": ["no-excuses", "verify-first", "hypothesis-driven"],
    },
    {
        "id": "fail-fast-code",
        "title": "Axiom #6: Fail-Fast Philosophy (Code)",
        "description": "No defaults, no fallbacks, no workarounds. Fail immediately when configuration missing.",
        "content": """## Principle

**Fail immediately when configuration is missing or incorrect.**

## What This Means

- No `.get(key, default)` - Silent misconfiguration corrupts research data
- No `try/except` returning fallback values - Hides errors
- No defensive programming (`if x is None: use_fallback`) - Masks problems

## Required Patterns

✅ `config["param"]` - Raises KeyError immediately if missing
✅ Pydantic `Field()` with no default - Raises ValidationError
✅ Explicit check: `if key not in dict: raise ValueError(...)`

## What This Does NOT Mean

- ❌ Does NOT mean: Avoid using industry-standard tools as dependencies
- ✅ CORRECT: Require `pre-commit`, `uv`, `pytest` and fail if missing
- ✅ CORRECT: Use best standard tool for the job

## Related Concepts

- [[fail-fast-agents]] - Same principle for agent behavior
- [[standard-tools]] - Use best tools, fail if missing
- [[no-workarounds]] - Don't bypass broken infrastructure

## Why It Matters

Research integrity depends on explicit configuration. Silent failures corrupt data and waste time debugging phantom issues.

## Anti-Patterns

```python
# ❌ WRONG - Silent misconfiguration
threshold = config.get("threshold", 0.5)

# ❌ WRONG - Hiding errors
try:
    value = parse_config()
except:
    value = DEFAULT

# ✅ CORRECT - Fail immediately
threshold = config["threshold"]  # KeyError if missing
```
""",
        "tags": ["axiom", "core", "fail-fast", "code", "config"],
        "related": ["fail-fast-agents", "standard-tools", "no-workarounds"],
    },
    {
        "id": "fail-fast-agents",
        "title": "Axiom #7: Fail-Fast Philosophy (Agents)",
        "description": "When YOUR instructions or tools fail, STOP immediately. Don't work around broken infrastructure.",
        "content": """## Principle

**When YOUR instructions or tools fail, STOP immediately.**

## Prohibited Behaviors

❌ Attempting recovery when slash commands fail
❌ Working around broken paths or missing environment variables
❌ "Figuring it out" when infrastructure is broken
❌ Continuing with workarounds instead of reporting errors

## Required Behaviors

✅ Report error immediately and stop
✅ Demand infrastructure be fixed, don't bypass it

## Rationale

Just like code shouldn't silently fail with defaults, agents shouldn't silently work around broken infrastructure. Fail-fast exposes problems so they get fixed, not hidden.

## Related Concepts

- [[fail-fast-code]] - Same principle for code
- [[no-workarounds]] - Never bypass broken tools
- [[tool-failure-protocol]] - How to handle tool failures

## Tool Failure Protocol

When a tool/script fails:

1. **Read the error message** - What exactly is it saying?
2. **ONE retry maximum** - If you misunderstood input format, try ONCE more
3. **STOP after 2nd failure** - Report the problem, don't continue

**After 2nd failure, STOP and report**:
- What you tried (both attempts)
- The exact error message
- Your hypothesis about the bug (if clear)
- Ask user how to proceed

**NEVER**:
- Try 3+ variations to "figure it out"
- Explore filesystem/code to understand tool internals
- Invent workarounds for broken tools
- Keep trying different formats/approaches

## Example

```
Attempt 1: task_process.py modify task-id --archive
Error: "Invalid task ID format"

Attempt 2: task_process.py modify 20250929-abc123 --archive
Error: "Invalid task ID format"

The script expects format YYYYMMDD-XXXXXXXX but task files use
different format. This appears to be a validation bug.

Should I investigate the script bug or handle this differently?
```
""",
        "tags": ["axiom", "core", "fail-fast", "agents", "tools"],
        "related": ["fail-fast-code", "no-workarounds", "tool-failure-protocol"],
    },
    {
        "id": "no-workarounds",
        "title": "Rule #12: No Workarounds",
        "description": "If tooling doesn't work PRECISELY, log failure and HALT until user decides what to do.",
        "content": """## Principle

**We're building a toolkit. If your tooling doesn't work PRECISELY, you've discovered a bug!**

Don't work around it; log the failure and HALT ALL WORK until the user decides what to do.

## What This Means

When infrastructure fails:
1. ✅ **STOP immediately**
2. ✅ **Log the bug** (use aops-bug skill)
3. ✅ **Report to user** with exact error
4. ✅ **Wait for decision** on how to proceed

## Anti-Patterns

❌ "The script failed but I found another way"
❌ "I couldn't use the skill so I did it manually"
❌ "The path was wrong so I searched for the file"
❌ "The tool doesn't work but I wrote a quick script"

## Related Concepts

- [[fail-fast-agents]] - Stop when tools fail
- [[fail-fast-code]] - Same principle for code
- [[no-excuses]] - Don't rationalize workarounds
- [[verify-first]] - Check if infrastructure actually works

## Why It Matters

1. **Framework quality**: Workarounds hide bugs that affect everyone
2. **Reliability**: If it doesn't work for agent, it won't work for users
3. **Maintenance**: Workarounds create technical debt
4. **Trust**: Framework must be dependable

## Example

✅ **CORRECT**:
```
Task script failed with: "Invalid config path"
This is a bug in the script.
Logged as issue #123.
Stopping work until script is fixed.
```

❌ **WRONG**:
```
Task script failed but I found the task files manually
and completed the task using direct file editing.
```
""",
        "tags": ["rule", "core", "fail-fast", "quality"],
        "related": ["fail-fast-agents", "fail-fast-code", "no-excuses", "verify-first"],
    },
    {
        "id": "no-excuses",
        "title": "Rule #14: No Excuses",
        "description": "Never close issues or claim success without confirmation. No error is somebody else's problem.",
        "content": """## Principle

**Never close issues or claim success without confirmation. No error is somebody else's problem.**

## Rules

- If asked to "run X to verify Y", success = X runs successfully
- Never rationalize away requirements
- If a test fails, fix it or ask for help - don't explain why it's okay
- If you can't verify and replicate, it doesn't work

## Anti-Patterns

❌ "Tests passed except for 2 flaky ones (those don't count)"
❌ "The bug might be environmental"
❌ "This should work if the config is correct"
❌ "The error is in the upstream library, not our code"
❌ "Root cause unclear but I implemented a workaround"

## Required Behaviors

✅ Tests ALL pass or task is incomplete
✅ Verified on actual system, not hypothetically
✅ Replicable by user right now
✅ No rationalizing why failures don't matter

## Related Concepts

- [[verify-first]] - Check actual state
- [[no-workarounds]] - Fix the problem
- [[hypothesis-driven]] - Express uncertainty honestly
- [[do-one-thing]] - Complete what was requested

## Why It Matters

Research integrity requires absolute honesty about what works. Excuses waste time and erode trust.

## Examples

✅ **CORRECT**: "2 tests failed. Should I fix them or are they expected?"
❌ **WRONG**: "2 tests failed but they're flaky, so the feature is done"

✅ **CORRECT**: "Can't replicate the bug. Need more info: [specific questions]"
❌ **WRONG**: "Probably environmental. Closing issue."
""",
        "tags": ["rule", "core", "quality", "honesty"],
        "related": [
            "verify-first",
            "no-workarounds",
            "hypothesis-driven",
            "do-one-thing",
        ],
    },
    {
        "id": "verify-first",
        "title": "Rule #13: Verify First",
        "description": "Check actual state, never assume.",
        "content": """## Principle

**Check actual state, never assume.**

## What This Means

Before claiming something:
- Run the code
- Read the file
- Check the directory
- Test the endpoint
- Verify the output

## Anti-Patterns

❌ "The config should be in..."
❌ "This file probably contains..."
❌ "The API likely returns..."
❌ "Based on the code structure, it seems..."

## Required Patterns

✅ "I read config.yaml and it contains..."
✅ "I ran the script and got output: [actual output]"
✅ "I checked the directory and found: [actual files]"

## Related Concepts

- [[no-excuses]] - Can't claim success without verification
- [[hypothesis-driven]] - Express uncertainty as testable hypotheses
- [[no-workarounds]] - Verify tools actually work

## Why It Matters

Assumptions waste time. Verification exposes actual state and prevents chasing phantom issues.

## Example

✅ **CORRECT**:
```
I ran `ls data/tasks/` and found 285 JSON files.
The schema matches: all have id, title, priority fields.
```

❌ **WRONG**:
```
Based on the code, tasks should be in data/tasks/ as JSON.
They probably have id, title, and priority fields.
```
""",
        "tags": ["rule", "core", "verification", "honesty"],
        "related": ["no-excuses", "hypothesis-driven", "no-workarounds"],
    },
    {
        "id": "hypothesis-driven",
        "title": "Rule #18: Hypothesis-Driven Communication",
        "description": "Express uncertainty as testable hypotheses, not definitive claims.",
        "content": """## Principle

**Express uncertainty as testable hypotheses, not definitive claims.**

## Pattern

❌ "The problem must be X" or "This is because Y"
✅ "Maybe X is Y? How should we check?"

## When Debugging

Propose hypothesis + verification method:

```
Hypothesis: Config file missing the 'threshold' key
Verification: Run `cat config.yaml | grep threshold`
```

## When Explaining

Question assumptions, suggest investigation:

```
This pattern might be X, but we should verify by checking Y.
```

## Related Concepts

- [[verify-first]] - Check before claiming
- [[no-excuses]] - Don't fake certainty
- [[dont-make-shit-up]] - Admit when you don't know

## Why It Matters

1. **Intellectual honesty**: Separates knowledge from speculation
2. **Effective debugging**: Testable hypotheses lead to solutions
3. **Team communication**: Clear about what's certain vs. uncertain
4. **Scientific rigor**: Research requires falsifiable claims

## Examples

✅ **GOOD**:
```
"Maybe the issue is the date format? We could test by parsing a sample."
"This looks like a race condition. Should we add logging to verify?"
```

❌ **BAD**:
```
"The date format is definitely wrong."
"This is a race condition."
```
""",
        "tags": ["rule", "communication", "debugging", "science"],
        "related": ["verify-first", "no-excuses", "dont-make-shit-up"],
    },
    {
        "id": "standard-tools",
        "title": "Axiom #10: Use Standard Tools",
        "description": "ONE GOLDEN PATH - use the best industry-standard tool for each job.",
        "content": """## Principle

**ONE GOLDEN PATH** - use the best industry-standard tool for each job.

## Standard Tool Stack

- **Package management**: `uv` (not pip, poetry, or custom solutions)
- **Testing**: `pytest` (not unittest or custom frameworks)
- **Git hooks**: `pre-commit` (not custom bash scripts)
- **Type checking**: `mypy` (not custom validators)
- **Linting**: `ruff` (not flake8, pylint, or custom)

## Rationale

- Reduces maintenance burden
- Leverages community knowledge
- Prevents reinventing wheels
- Enables onboarding (people know these tools)

## Fail-Fast Integration

Installation fails immediately if required tool missing (no fallbacks).

## Related Concepts

- [[fail-fast-code]] - Fail if standard tool missing
- [[one-golden-path]] - Single way to do each thing
- [[no-workarounds]] - Don't bypass standard tools

## Anti-Patterns

❌ "uv isn't installed, I'll use pip"
❌ "Let me write a custom script instead of using pre-commit"
❌ "We could build our own test framework"

## Required Behaviors

✅ Fail if `uv` not installed
✅ Use `pytest` for all tests
✅ Use `pre-commit` for all hooks
✅ Follow tool conventions (don't fight them)

## Why It Matters

1. **Maintainability**: Standard tools have docs, community support
2. **Reliability**: Battle-tested tools have fewer bugs
3. **Onboarding**: New team members already know these tools
4. **Focus**: Spend time on research, not building infrastructure
""",
        "tags": ["axiom", "tools", "standards", "infrastructure"],
        "related": ["fail-fast-code", "one-golden-path", "no-workarounds"],
    },
]


def create_concept_note(
    concept: Dict,
    folder: str = "concepts/axioms",
    project: str = "ns",
    use_mcp: bool = True,
) -> Dict:
    """
    Create a concept node in Basic Memory.

    Args:
        concept: Concept dictionary with id, title, description, content, tags, related
        folder: Folder to create note in
        project: BM project name
        use_mcp: Whether to use MCP

    Returns:
        Result dictionary
    """
    # Build full content with WikiLinks
    full_content = f"""# {concept["title"]}

{concept["description"]}

{concept["content"]}

## Tags

{", ".join(f"#{tag}" for tag in concept["tags"])}

## Related Concepts

{chr(10).join(f"- [[{rel}]]" for rel in concept["related"])}
"""

    if not use_mcp:
        # Test mode
        return {
            "success": True,
            "id": concept["id"],
            "message": f"Created {concept['id']} (test mode)",
        }

    try:
        from mcp import mcp__bm__write_note

        result = mcp__bm__write_note(
            title=concept["title"],
            content=full_content,
            folder=folder,
            entity_type="concept",
            project=project,
            tags=concept["tags"],
        )

        return {
            "success": True,
            "id": concept["id"],
            "identifier": result.get("identifier"),
            "message": f"Created concept: {concept['id']}",
        }

    except Exception as e:
        return {
            "success": False,
            "id": concept["id"],
            "error": str(e),
            "message": f"Failed to create concept: {e}",
        }


def main():
    """Extract and create all concept nodes."""
    import argparse

    parser = argparse.ArgumentParser(description="Extract concepts from bot repo")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be created"
    )
    parser.add_argument("--project", default="ns", help="BM project name")

    args = parser.parse_args()

    print(f"Extracting {len(AXIOM_CONCEPTS)} concepts from bot repo...")
    print()

    created = 0
    failed = 0

    for concept in AXIOM_CONCEPTS:
        if args.dry_run:
            print(f"Would create: {concept['id']} - {concept['title']}")
            created += 1
        else:
            result = create_concept_note(concept, project=args.project, use_mcp=True)

            if result["success"]:
                print(f"✓ Created: {concept['id']}")
                created += 1
            else:
                print(f"✗ Failed: {concept['id']} - {result['message']}")
                failed += 1

    print()
    print("=" * 60)
    print(f"Extraction {'simulation' if args.dry_run else 'complete'}:")
    print(f"  Created: {created}")
    print(f"  Failed: {failed}")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
