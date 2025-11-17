---
name: framework
description: Maintain the flattened automation framework in bots/. Design experiments,
  debug issues, enforce documentation consistency, and prevent bloat. Use when working
  on framework infrastructure, creating new automation components, debugging framework
  issues, or when documentation conflicts are detected. Enforces single source of
  truth, prohibits duplicate content, and requires end-to-end integration tests.
allowed-tools: Read,Write,Edit,Grep,Glob,Bash
version: 1.0.0
permalink: bots/skills/framework/skill
---

# Framework Maintenance Skill

Maintain the minimal automation framework in academicOps (installed via symlinks to `~/.claude/`). Enforce strict quality standards: single source of truth, no documentation conflicts, mandatory integration tests, and controlled growth.

## Overview

This skill operates in two modes:

1. **Strategic Partner**: Provides context, guidance, and decision support for framework work. Maintains institutional memory across sessions. Ensures strategic alignment with vision.

2. **Maintenance Operator**: Handles design, experimentation, debugging, fault logging, iteration, improvement, and monitoring of the framework.

The framework lives in `bots/` and follows aggressive minimalism—sophisticated where necessary, simple everywhere else.

**When to use**:

- Strategic discussions about framework direction
- Framework infrastructure work
- Creating automation components
- Debugging framework issues
- Detecting documentation conflicts
- Preventing bloat

## Strategic Partner Mode

Provides context, guidance, and decision support for framework work. Maintains institutional memory and ensures strategic alignment.

**Core functions**: Maintain institutional memory, advocate for strategic goals, guard against complexity, ensure quality, make principled decisions, enable trust.

**Critical requirement**: Trustworthiness through thorough verification (VERIFY FIRST, NO EXCUSES, VERIFY COMPLETENESS, FAIL FAST).

**For detailed procedures**: [[references/strategic-partner-mode.md]]

## Meta-Framework: Iterative Automation Development

The automation framework is built incrementally using a rigorous test-first approach. See these foundational documents for strategic context:

- **[[VISION.md]]** - The ambitious end state: What does fully-automated academic workflow look like?
- **[[ROADMAP.md]]** - Maturity progression model: How do we get there? (Stages 0-5)
- **[[TASK-SPEC-TEMPLATE.md]]** - Task specification: How do we define, scope, test, and validate each automation?

**Key principle**: Build bit-by-bit with each piece working and tested, while progressing toward sophisticated end state.

### Using the Meta-Framework

**When starting new automation work**:

1. Check [[ROADMAP.md]] to identify current stage and next priorities
2. Use [[TASK-SPEC-TEMPLATE.md]] to specify the automation task before coding
3. Design integration test first (must fail before implementation)
4. Implement minimum viable automation
5. Test until passes
6. Document in experiment log
7. Update ROADMAP.md with progress

**Stage progression** (from ROADMAP.md):

- Stage 1: Documented Workflows (current foundation) ✅
- Stage 2: Scripted Tasks (targeted automation) ← **Next focus**
- Stage 3: Integrated Pipelines (workflow automation)
- Stage 4: Adaptive Systems (intelligent automation)
- Stage 5: Proactive Assistance (anticipatory automation)

## Authoritative Sources

**Single source of truth hierarchy**:

1. `~/.claude/CLAUDE.md` - Authoritative directory structure and paths
2. `/home/nic/src/academicOps/AXIOMS.md` - Foundational principles
3. `/home/nic/src/academicOps/CORE.md` - User context and tools
4. `/home/nic/src/academicOps/ACCOMMODATIONS.md` - Work style requirements

All other documentation must reference these sources, never duplicate their content.

## Core Principles

Follow all principles from [[AXIOMS.md]].

### Documentation Integrity (MANDATORY)

**NO INCOMPLETE, CONTRADICTORY, OR CONFLICTED DOCUMENTATION** may exist in any commit to the dev branch.

**Enforcement**:

- Before any commit: Validate all documentation references resolve correctly
- Check for conflicting information across files
- Verify single source of truth is maintained
- Flag any duplication of referenced content

**Detection patterns**:

- Same information in multiple files
- Outdated references to moved/deleted content
- Contradictory instructions in different files
- Summaries that duplicate referenced content (multi-line explanations after references)
- Historical context or "What's Gone" sections (git history IS the record)
- Meta-instructions about how to use the documentation itself

### Single Source of Truth

Each piece of information exists in exactly ONE location.

**Rules**:

- Core principles → `bots/AXIOMS.md`
- Directory structure → `README.md`
- User context → `bots/CORE.md`
- Work style → `bots/ACCOMMODATIONS.md`
- Writing style → `bots/STYLE.md` or `bots/STYLE-QUICK.md`

**Prohibited**:

- Duplicating axioms in multiple files
- Copying directory structure into multiple documents
- Repeating user information across files
- Creating summaries of referenced content

**Pattern**: Reference, don't repeat.

**Skill references**: Use Claude-native language: `use the \`python-dev\` skill`, not`refer to [[../python-dev/SKILL.md]]`.

### Authoritative vs Instructional Content

**Each file must be EITHER authoritative OR instructional, never both.**

**Authoritative content** = Facts this file owns:

- Directory structure and paths
- Contact information
- Session start loading sequence
- Configuration values
- State data

**Instructional content** = How to use things:

- Workflows and procedures
- Examples and tutorials
- Explanations of concepts
- Troubleshooting guides
- Decision frameworks

**Radical minimalism for authoritative sources**:

- README.md owns directory structure → contains ONLY directory tree, contact info, session start list
- AXIOMS.md owns principles → contains ONLY principle statements
- CORE.md owns user/tool context → contains ONLY facts about user, references to detailed docs

**Pattern violations to detect**:

- Authoritative file (README.md) containing workflow examples
- Authoritative file explaining how to use the information it provides
- Authoritative file containing "For more details, see X" followed by summary of X
- Instructional content mixed with configuration/state data

**Correct pattern**:

- Authoritative source states the fact
- Separate instructional file explains how to use it
- References between them, no summaries

**Example (README.md)**:

- ✅ Correct: Lists `@bots/CORE.md` in session start sequence, stops
- ✅ Acceptable: `@bots/CORE.md → User context, tools, and paths` (brief inline summary on same line)
- ❌ Wrong: Lists `@bots/CORE.md` then adds multi-line explanation paragraph
- ❌ Wrong: Contains entire section "How to Add Session Start Content"

### File Creation Prohibition

**New files are PROHIBITED** unless proven necessary through successful integration tests.

**Approval process for new files**:

1. Document clear justification (why existing files insufficient)
2. Design file with specific, bounded scope
3. Create integration test that validates the file's purpose
4. Implement file
5. Run integration test end-to-end
6. Only commit if tests pass

**Exception**: Experiment logs are allowed but must follow strict format (see Experiments section).

### Bloat Prevention

**Hard limits**:

- Skill files: 500 lines maximum
- Documentation chunks: 300 lines maximum
- Approaching limit = Extract and reference, don't expand

**Bloat categories** (remove aggressively):

1. **Multi-line summaries after references**: Brief inline summaries (same line) are acceptable, but multi-line explanations = bloat
   - ❌ Bad: "Use the task skill at [[skills/README.md]]. Tasks are stored in data/tasks/. Use task scripts, never write files directly." (multi-line explanation)
   - ✅ Good: "For task management, use the `task` skill." (simple direction)
   - ✅ Acceptable: `@bots/CORE.md → User context and tools` (brief inline summary)
   - Principle: Direct to tool with brief context OK, but don't explain tool. Agent must invoke/read to get full instructions.
2. **Excessive decorative elements**: Excessive horizontal rules, ASCII art (unless functional like directory tree markers). Emojis are allowed for visual navigation and section marking.
3. **Historical context**: "What's Gone", "Why we changed", migration notes (git history IS the record)
4. **Meta-instructions**: "How to use this file", "Support" sections (self-evident or belongs in instructional doc)
5. **Redundant explanations**: Same concept explained in multiple places
6. **Verbose formatting**: Multi-line presentations of simple factual data (can often condense to single line)

**Active monitoring**:

- Track file sizes in pre-commit hooks
- Flag files approaching limits
- Require justification for growth beyond 80% of limit
- Count references followed by multi-line explanatory paragraphs
- Flag "What's Gone" or historical sections

### Script Design: Orchestration vs Reasoning

**Key principle**: Scripts are simple utilities (like `jq` or `split`) that agents call via Bash. Agents do ALL orchestration, decision-making, and reasoning.

**Prohibited**: Scripts that read files, filter with regex, search files, extract patterns, or orchestrate workflows (use agent tools: Read, Write, Edit, Grep, Glob, LLM reasoning).

**Allowed**: Pure mechanical data transformation (chunk JSONL, merge JSON files) and aggregation.

**Pattern**: Agents orchestrate → Scripts are simple tools → Agents reason

**For detailed guidance and examples**: [[references/script-design-guide.md]]

## Workflows

Detailed step-by-step workflows for framework operations. Read and follow the appropriate workflow for each task:

1. **[[workflows/01-design-new-component.md]]** - Adding hooks, skills, scripts, commands
2. **[[workflows/02-debug-framework-issue.md]]** - Fixing failures and unexpected behavior
3. **[[workflows/03-experiment-design.md]]** - Testing new approaches and capabilities
4. **[[workflows/04-monitor-prevent-bloat.md]]** - Maintaining file size limits and preventing duplication
5. **[[workflows/05-review-pull-request.md]]** - Reviewing PRs before merge (critical for quality)
6. **[[workflows/06-develop-specification.md]]** - Developing automation specifications collaboratively with user

## Documentation Conflict Detection

**Run before every commit to dev branch**.

**Check**:

1. All wikilink-style references resolve to existing files
2. No contradictory information across documentation
3. Directory structure in README.md matches actual structure
4. No duplication of axioms, principles, or core information
5. No summaries following references (trust the reference)

**Pattern**: Use grep to find potential conflicts (check against `bots/AXIOMS.md`):

```bash
# Find files referencing AXIOMS
grep -r "AXIOMS\|axiom\|principle" bots/

# Check for duplication of key concepts from AXIOMS.md
grep -r "fail-fast\|single source\|DRY" bots/

# Verify references resolve
grep -r "\[\[.*\.md\]\]" bots/
```

**Action on conflicts**:

- HALT immediately
- Document conflict clearly
- Resolve by choosing single source of truth
- Update all references to point to that source
- Remove duplicated content
- Verify resolution before proceeding

## Integration Testing

**MANDATORY before committing any framework changes**.

### Test Types: Unit vs E2E

**Unit tests** verify structural prerequisites exist:

- Files exist at expected paths
- References resolve correctly
- Scripts are executable
- Configuration is valid

**End-to-end (E2E) tests** verify agent behavior in actual workflows:

- Agent READS the files (not just that files exist)
- Agent FOLLOWS the instructions (not just that instructions exist)
- Complete workflow executes from user input to final output
- Agent makes correct decisions based on context

**Critical distinction**: Testing that `data/tasks/` exists ≠ testing that agent uses task scripts. Testing that `README.md` contains task references ≠ testing that agent reads and follows those references.

**Test categories**:

1. **Documentation integrity test** (UNIT)
   - All references resolve
   - No contradictions detected
   - Single source of truth maintained

2. **Component functionality test** (UNIT/INTEGRATION)
   - New component performs intended function
   - No regressions in existing components
   - Error handling works correctly

3. **End-to-end workflow test** (E2E)
   - Agent receives user input in realistic scenario
   - Agent reads session start context
   - Agent follows documented workflows
   - Complete workflow executes successfully
   - Output matches expected format
   - Edge cases handled appropriately

**Test location**: `bots/tests/`

**Test documentation**: `bots/tests/README.md` - Must be kept up-to-date when tests change

**Test format (pytest)**:

```python
def test_something(fixture: Type) -> None:
    """Test description.

    Args:
        fixture: Description of fixture

    Raises:
        AssertionError: If test condition fails
    """
    # Arrange
    # Act
    # Assert
```

**Commit rules**:

- All tests must pass
- No partial success accepted
- Fix or revert, never commit broken state
- Update `bots/tests/README.md` when adding/modifying tests

## File Organization

```
/home/nic/src/academicOps/
├── CORE.md              # Authoritative user/tools reference
├── AXIOMS.md            # Authoritative principles
├── ACCOMMODATIONS.md    # Authoritative work style
├── STYLE-QUICK.md       # Quick writing reference
├── STYLE.md             # Full writing reference
├── tests/               # Framework test suite
│   ├── README.md        # Test documentation (keep up-to-date)
│   ├── conftest.py      # Test fixtures
│   ├── paths.py         # Path resolution utilities
│   ├── test_*.py        # Unit tests
│   └── integration/     # Integration tests
│       ├── conftest.py              # Integration fixtures
│       └── test_*.py                # Integration test files
├── skills/
│   └── framework/
│       ├── SKILL.md                 # This file - framework maintenance
│       ├── VISION.md                # End state: fully-automated workflow
│       ├── ROADMAP.md               # Maturity stages 0-5, progression plan
│       ├── TASK-SPEC-TEMPLATE.md    # Template for specifying automations
│       ├── references/              # Technical reference documentation
│       │   ├── hooks_guide.md       # Claude Code hooks system reference
│       │   ├── script-design-guide.md        # Script design principles
│       │   ├── strategic-partner-mode.md     # Strategic partner procedures
│       │   └── testing-with-live-data.md     # Testing patterns
│       ├── workflows/               # Detailed workflow procedures
│       │   ├── 01-design-new-component.md
│       │   ├── 02-debug-framework-issue.md
│       │   ├── 03-experiment-design.md
│       │   ├── 04-monitor-prevent-bloat.md
│       │   ├── 05-review-pull-request.md
│       │   └── 06-develop-specification.md
│       ├── experiments/             # Experiment logs (YYYY-MM-DD_name.md)
│       │   ├── LOG.md               # Learning patterns from experiments
│       │   └── TEMPLATE.md          # Experiment log template
│       └── scripts/                 # Automation scripts
├── hooks/               # Lifecycle hooks
├── commands/            # Slash commands
├── agents/              # Agentic workflows (when added)
└── dist/                # Build artifacts (when added)
```

## Error Handling

**When integration tests fail**:

- HALT immediately
- Do not commit
- Do not rationalize
- Fix or revert
- No exceptions

**When documentation conflicts detected**:

- HALT immediately
- Document the conflict
- Resolve to single source of truth
- Update all references
- Verify resolution
- Run full test suite

**When bloat detected**:

- Stop adding to file
- Extract content to appropriate location
- Reference extracted content
- Verify no duplication remains

## Experiment Log Archive

Keep all experiment logs permanently for learning and reference.

**Structure**:

- `experiments/YYYY-MM-DD_experiment-name.md`
- Immutable after decision finalized
- Tagged with final decision (keep/revert/iterate)

**Learning log (LOG.md)**:

- **APPEND-ONLY**: Never delete entries, even when resolving conflicts
- Patterns emerge from viewing successes AND failures over time
- A single success doesn't indicate stable long-term success
- Both positive and negative outcomes are needed for pattern recognition

**Purpose**:

- Learn from past decisions
- Avoid repeating failed experiments
- Build institutional knowledge
- Justify current framework state

## Quick Reference

**Before any framework work**:

1. Read relevant authoritative sources (README.md, AXIOMS.md, etc.)
2. Check for similar existing components
3. Design integration test first
4. Create experiment log if needed

**Before any commit**:

1. Run all integration tests
2. Check documentation integrity
3. Verify single source of truth
4. Confirm no bloat introduced
5. Validate no conflicts exist

**When in doubt**:

- Reference, don't duplicate
- Test, don't assume
- Revert, don't workaround
- Ask, don't guess
