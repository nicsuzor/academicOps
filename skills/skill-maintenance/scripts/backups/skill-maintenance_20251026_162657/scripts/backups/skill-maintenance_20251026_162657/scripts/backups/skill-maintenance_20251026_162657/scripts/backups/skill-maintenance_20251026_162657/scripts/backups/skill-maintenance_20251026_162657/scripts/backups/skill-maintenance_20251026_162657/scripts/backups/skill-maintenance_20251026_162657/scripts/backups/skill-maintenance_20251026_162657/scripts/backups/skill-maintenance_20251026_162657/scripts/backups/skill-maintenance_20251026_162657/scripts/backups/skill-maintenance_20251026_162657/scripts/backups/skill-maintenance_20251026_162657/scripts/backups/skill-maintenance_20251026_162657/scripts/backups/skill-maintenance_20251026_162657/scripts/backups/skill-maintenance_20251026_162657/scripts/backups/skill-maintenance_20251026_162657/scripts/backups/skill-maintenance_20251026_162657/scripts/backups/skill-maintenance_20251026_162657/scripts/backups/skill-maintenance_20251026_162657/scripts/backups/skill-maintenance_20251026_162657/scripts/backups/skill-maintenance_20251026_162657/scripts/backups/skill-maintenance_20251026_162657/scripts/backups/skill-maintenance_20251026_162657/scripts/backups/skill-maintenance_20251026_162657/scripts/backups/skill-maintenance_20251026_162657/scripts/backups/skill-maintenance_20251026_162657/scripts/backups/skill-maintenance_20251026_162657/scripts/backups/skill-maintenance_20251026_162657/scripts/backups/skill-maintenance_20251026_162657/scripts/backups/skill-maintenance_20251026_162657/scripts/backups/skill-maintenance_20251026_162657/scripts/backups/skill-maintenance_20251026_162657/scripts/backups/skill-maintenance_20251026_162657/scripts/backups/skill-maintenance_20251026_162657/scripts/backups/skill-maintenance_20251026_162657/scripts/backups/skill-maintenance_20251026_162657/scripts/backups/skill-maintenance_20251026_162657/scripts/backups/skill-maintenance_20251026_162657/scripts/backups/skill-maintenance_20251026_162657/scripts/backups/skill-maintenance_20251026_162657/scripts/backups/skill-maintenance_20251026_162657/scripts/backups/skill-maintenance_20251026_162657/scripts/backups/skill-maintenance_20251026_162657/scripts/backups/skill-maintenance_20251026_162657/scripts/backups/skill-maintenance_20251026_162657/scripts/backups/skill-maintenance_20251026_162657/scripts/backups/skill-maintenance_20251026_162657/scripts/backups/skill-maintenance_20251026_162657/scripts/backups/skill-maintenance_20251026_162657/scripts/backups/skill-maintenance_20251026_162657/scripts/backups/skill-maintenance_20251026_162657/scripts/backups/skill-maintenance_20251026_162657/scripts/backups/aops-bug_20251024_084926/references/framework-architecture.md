# academicOps Framework Architecture

Framework-specific knowledge for tracking bugs, violations, and improvements in the academicOps agent system.

## Repository Structure

```
${OUTER}/                          # Parent repo (PRIVATE)
├── CLAUDE.md                      # Entry point
├── bot/                           # academicOps submodule (PUBLIC on GitHub)
│   ├── agents/_CORE.md            # Core axioms (inviolable rules)
│   ├── agents/trainer.md          # Trainer agent
│   ├── agents/DEVELOPER.md        # Developer agent
│   ├── bots/agents/_CORE.md       # Alternative location (check both)
│   ├── scripts/                    # Validation and utility scripts
│   ├── experiments/                # Experiment logs
│   ├── ARCHITECTURE.md             # System design documentation
│   └── .claude/
│       ├── skills/                 # Atomic, reusable workflows
│       ├── commands/               # Slash command shortcuts
│       └── settings.json           # Permissions and hooks
├── docs/
│   └── agents/INSTRUCTIONS.md     # User-specific context (PRIVATE)
└── projects/                      # Submodules (each independent)
```

## Core Framework Files

### _CORE.md - Inviolable Axioms

Location: `bots/agents/_CORE.md` or `agents/_CORE.md`

**Contains**: 18 core axioms that ALL agents must follow.

**Key axioms**:
1. DO ONE THING - Complete task requested, then STOP
2. ANSWER DIRECT QUESTIONS DIRECTLY
3. Namespace Separation (agents/ vs docs/)
4. Data Boundaries (public vs private)
5. Project Isolation
6. Project Independence
7. Fail-Fast Philosophy (Code) - No defaults, no fallbacks
8. Fail-Fast Philosophy (Agents) - Stop when infrastructure fails
9. Everything is self-documenting
10. DRY, modular, EXPLICIT
11. Use Standard Tools - uv, pytest, pre-commit, etc.
12. STOP WHEN INTERRUPTED
13. VERIFY FIRST - Check actual state
14. NO EXCUSES - No error is someone else's problem
15. WRITE FOR THE LONG TERM
16. DOCUMENT PROGRESS - GitHub issues are memory
17. DON'T MAKE SHIT UP
18. ALWAYS CITE SOURCES

**When to reference**: Any agent violation traces back to one or more axioms.

### trainer.md - Meta-Agent for Framework Maintenance

Location: `bots/agents/trainer.md` or `agents/trainer.md`

**Purpose**: Maintains and optimizes all agent instructions, configurations, enforcement mechanisms.

**Key sections**:
- Enforcement Hierarchy: Scripts > Hooks > Config > Instructions
- Anti-Bloat Protocol: Skills should stay <500 lines
- GitHub Issue Management protocol
- Instruction Index maintenance

**When to reference**: Issues about trainer behavior, framework meta-problems.

### ARCHITECTURE.md - System Design

Location: `ARCHITECTURE.md` (repo root)

**Purpose**: Describes current system state (not aspirational).

**Contains**:
- Component descriptions (agents, skills, scripts, hooks)
- Design decisions and rationale
- Workflow patterns
- Open questions

**When to reference**: Architecture drift detected, design questions.

### experiments/ - Experiment Tracking

Location: `experiments/` directory

**Format**: `YYYY-MM-DD_descriptive-name.md`

**Purpose**: Document experiments testing framework changes.

**Structure**:
```markdown
# Experiment: [Name]

**Date**: YYYY-MM-DD
**Commit**: [SHA]
**Issue**: #[number]
**Agent**: [which agent tested]

## Hypothesis
[What we expect to change]

## Implementation
[What was changed]

## Results
[What actually happened]

## Outcome
[SUCCESS / FAILED / PARTIAL]

## Decision
[Keep / Revert / Iterate]
```

**When to use**: Testing hooks, scripts, instruction changes.

## Enforcement Hierarchy

Per trainer.md, enforcement goes from strongest to weakest:

### 1. Scripts (Strongest)

**Location**: `scripts/`

**Purpose**: Automated validation that prevents bad behavior.

**Examples**:
- `check_solved_problems.py` - Detects reinvented wheels
- `check_fail_fast.py` - Detects defensive patterns
- `load_instructions.py` - Loads agent instructions

**Characteristics**:
- Runs before or during agent execution
- Can block operations
- Zero token cost
- Most reliable enforcement

**When to use**: Detectable patterns, deterministic violations

### 2. Hooks

**Location**: `.claude/settings.json` hooks configuration

**Types**:
- `SessionStart` - Loads instructions when session begins
- `PreToolUse` - Validates tool usage before execution
- `SubagentStop` - Validates subagent completion
- `Stop` - Validates session end

**Example**:
```json
"PreToolUse": [
  {
    "hooks": [
      {
        "type": "command",
        "command": "uv run python bots/hooks/validate_tool.py",
        "timeout": 3000
      }
    ]
  }
]
```

**Characteristics**:
- Runs at specific lifecycle points
- Can block or warn
- Immediate feedback
- Requires pattern matching

**When to use**: Tool usage patterns, permission enforcement

### 3. Configuration

**Location**: `.claude/settings.json` permissions

**Example**:
```json
"permissions": {
  "allow": [
    "Bash(uv run pytest:*)",
    "Bash(uv run python:*)"
  ],
  "deny": [
    "Write(**/*.md)",
    "Write(**/*.env*)"
  ]
}
```

**Characteristics**:
- Declarative restrictions
- Tool-level granularity
- No custom logic
- Simple to understand

**When to use**: Broad tool restrictions, security boundaries

### 4. Instructions (Weakest)

**Location**: Agent `.md` files, skill `SKILL.md` files

**Characteristics**:
- Text-based guidance
- Agents can forget in long conversations
- Requires agent understanding
- Least reliable

**When to use**: Complex decision-making, nuanced guidance, last resort

**Principle**: If agents consistently violate an instruction, move enforcement UP the hierarchy.

## Component Types

### Agents

**Location**: `bots/agents/*.md` or `agents/*.md`

**Purpose**: Define agent behavior and responsibilities.

**Format**: Markdown with YAML frontmatter

**Examples**:
- `_CORE.md` - Core axioms for all agents
- `trainer.md` - Meta-agent for framework maintenance
- `DEVELOPER.md` - Development workflow

**Invocation**: Via slash commands (`/trainer`) or subagent spawning

### Skills

**Location**: `.claude/skills/*/SKILL.md`

**Purpose**: Atomic, reusable workflows usable across any project.

**Format**: Markdown with YAML frontmatter, optional resources

**Examples**:
- `github-issue` - Universal GitHub issue management
- `python-dev` - Python development standards
- `git-commit` - Git commit workflow

**Invocation**: Via `Skill` tool or from other agents/skills

**Constraints**:
- Should be <500 lines (complexity budget)
- Must work universally (not repo-specific)
- Atomic (does ONE thing)

### Commands

**Location**: `.claude/commands/*.md`

**Purpose**: User-facing slash command shortcuts.

**Format**: Markdown that expands to prompt

**Examples**:
- `/trainer` - Loads trainer.md + invokes trainer skill
- `/dev` - Loads DEVELOPER.md agent instructions
- `/ops` - Shows academicOps help

**Invocation**: User types `/command-name`

### Scripts

**Location**: `scripts/*.py`

**Purpose**: Automated validation and utility operations.

**Examples**:
- `check_solved_problems.py` - Pre-commit linter
- `load_instructions.py` - Instruction loader for agents

**Invocation**: Run via `uv run python scripts/script_name.py`

## Data Boundaries

### Public vs Private

**PUBLIC (bot/ repository)**:
- Generic agent instructions
- Skills (universal workflows)
- Scripts (validation tools)
- Core documentation
- Experiments (framework testing)

**PRIVATE (parent repository, projects)**:
- User-specific contexts
- Client/project data
- API keys, credentials
- Proprietary business logic

**Rule**: NEVER leak private data to public repository or GitHub issues.

### Cross-Repository Posting

**When working in academicOps repo**:
- ✅ Can write to local files (experiments/, ARCHITECTURE.md)
- ✅ Can write to GitHub issues in nicsuzor/academicOps
- ✅ Can reference all framework files

**When working in third-party repos**:
- ❌ NEVER modify local files
- ✅ CAN write to nicsuzor/academicOps GitHub issues ONLY
- ❌ NEVER include sensitive data in GitHub
- ✅ Must sanitize examples and quotes

### Sanitization Requirements

Before posting to public GitHub from private repos:

1. **Remove credentials**: API keys, tokens, passwords
2. **Generalize paths**: `/home/nic/client-acme/` → `[project-directory]/`
3. **Remove proprietary info**: Client names, private data
4. **Keep framework errors**: Stack traces, agent behaviors safe

**Tool**: Use `sanitize_github.py` script (DataFog-based)

## GitHub Repository

**Name**: `nicsuzor/academicOps`

**Purpose**: Public repository for academicOps framework.

**Verification Protocol**: ALWAYS verify before posting:
```bash
gh repo view nicsuzor/academicOps --json owner -q '.owner.login'
# Output should be: nicsuzor
```

**Issue Labels**:
- `prompts` - Agent instruction issues
- `infrastructure` - Scripts, hooks, config
- `bug` - Something broken
- `enhancement` - New capabilities
- `documentation` - Docs issues

**Issue Tracking**: All framework issues go to nicsuzor/academicOps, regardless of which repo you're working in.

## Common Workflows

### Agent Violation Workflow

1. Identify violation (which axiom, which behavior)
2. Categorize by behavioral pattern (see behavioral-patterns.md)
3. Search GitHub for existing issues (3+ strategies)
4. Create or update issue in nicsuzor/academicOps
5. Determine enforcement layer needed
6. Create experiment log if testing fix
7. Update ARCHITECTURE.md if system changed

### Experiment Workflow

1. Identify problem needing testing
2. Create experiment log: `experiments/YYYY-MM-DD_name.md`
3. Document hypothesis and implementation
4. Make changes
5. Test
6. Document results and outcome
7. Update INDEX.md
8. Link to GitHub issue

### Architecture Drift Workflow

1. Compare ARCHITECTURE.md to actual codebase state
2. Identify discrepancies
3. Verify actual implementation
4. Update ARCHITECTURE.md to match reality
5. Create GitHub issue if major drift

## Success Metrics

**Framework health indicators**:
- Decreasing agent violations over time
- Fewer duplicate GitHub issues
- Faster resolution of framework bugs
- Cleaner agent instructions (<500 lines per skill)
- More enforcement at script/hook layer, less in instructions

**Red flags**:
- Same violation recurring (enforcement failed)
- Growing instruction files (bloat, move to scripts)
- Unclear agent boundaries (authority violations)
- Architecture drift (ARCHITECTURE.md outdated)

## Related Skills

- **github-issue**: For GitHub operations (search, create, update issues)
- **experiment-tracker**: Full workflow (being split into aops-bug + github-issue)
- **trainer**: For framework maintenance work
