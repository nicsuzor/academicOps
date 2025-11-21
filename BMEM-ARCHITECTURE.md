---
title: BMEM Architecture - Single Knowledge Base Design
permalink: bmem-architecture
type: spec
tags:
  - bmem
  - architecture
  - knowledge-base
  - framework
---

# BMEM Architecture: Single Knowledge Base Design

## Overview

Basic Memory (bmem) implements a **single, unified knowledge base per user across all projects**. Unlike per-project or per-workspace approaches, bmem maintains ONE consistent source of truth located at `$ACA_DATA` (user's private data repository), accessible from any project, location, or execution context.

This architecture enables seamless multi-project workflows where knowledge created in one project is immediately available in all others.

---

## Core Architecture Principles

### 1. Environment Variable Guarantee

The `$ACA_DATA` environment variable is the single, immutable contract for knowledge base location:

```bash
# User's shell configuration (~/.bashrc or ~/.zshrc)
export ACA_DATA="$HOME/writing/data"
```

**Guarantee**: bmem ALWAYS reads from and writes to `$ACA_DATA`, never to relative paths or project-specific locations.

**Validation**: If `$ACA_DATA` is not set or invalid, all bmem operations fail immediately (fail-fast principle).

### 2. Write Location Invariance

bmem write operations are **independent of current working directory (CWD)**:

- Running from `/home/user/project-a/` → writes to `$ACA_DATA`
- Running from `/tmp/` → writes to `$ACA_DATA`
- Running from `/home/user/project-b/` → writes to `$ACA_DATA`

This invariance is verified by diagnostic tests that execute Claude from `/tmp`, proving files are written to `$ACA_DATA` regardless of CWD.

**Implementation**: All paths use absolute resolution from environment variables, never relative path traversal.

### 3. Framework vs Data Separation

academicOps separates framework code from user data:

```
$AOPS/                    ← Framework (code, skills, hooks, tests)
  ├── skills/
  ├── hooks/
  ├── commands/
  ├── lib/paths.py       ← Path resolution module
  └── tests/

$ACA_DATA/                ← User Data (knowledge base, personal context)
  ├── projects/          ← Project-specific data
  │   └── aops/          ← aOps project data (VISION, ROADMAP, experiments)
  ├── tasks/             ← Tasks (inbox, completed, archived)
  ├── sessions/          ← Claude Code session logs
  ├── context/           ← Contextual notes
  ├── goals/             ← Goals and objectives
  └── [bmem entities]/   ← People, orgs, concepts, etc.
```

**Key invariant**: Framework code never persists state to `$AOPS`. All persistence is to `$ACA_DATA`.

---

## How It Works

### Path Resolution Strategy

academicOps provides a central path resolution module (`lib/paths.py`) that implements fail-fast semantics:

```python
from lib.paths import get_aops_root, get_data_root

# Framework root (auto-detected or from $AOPS)
aops = get_aops_root()

# User data root (requires $ACA_DATA)
data = get_data_root()  # Raises RuntimeError if not set
```

**AOPS Resolution** (framework code location):
1. Use `$AOPS` if set (fail immediately if invalid)
2. Auto-detect from module location
3. Check common installation paths
4. Fail with clear error if not found

**ACA_DATA Resolution** (user data location):
1. Require `$ACA_DATA` to be explicitly set (no auto-detection)
2. Validate path exists
3. Fail immediately if not valid

### MCP Server Architecture

The bmem MCP server (`skills/bmem/`) wraps the basic-memory knowledge base backend:

```
Claude Code Session
    ↓
mcp__bmem__* function tools
    ↓
bmem MCP Server (skills/bmem/)
    ↓
basic-memory Backend
    ↓
Reads/Writes $ACA_DATA/
    ↓
Markdown files with YAML frontmatter
```

**Key guarantee**: MCP server always accesses `$ACA_DATA` through environment variable resolution, not configuration files or discovery.

### Vector Search & Indexing

bmem provides automatic background indexing:

- **Full-text search**: Fast keyword matching across all notes
- **Semantic search**: Vector embeddings enable conceptual queries
- **Automatic indexing**: Updates as files are created/modified in `$ACA_DATA`

All indexes are stored within `$ACA_DATA`, enabling consistent multi-project search.

### Framework Config Symlinks

academicOps installs framework configuration (skills, hooks, commands) via symlinks:

```
~/.claude/                      (Claude Code config directory)
├── CLAUDE.md                   (project-specific instructions)
├── skills/  → symlink to $AOPS/skills/
├── hooks/   → symlink to $AOPS/hooks/
└── commands/  → symlink to $AOPS/commands/
```

This approach:
- Keeps single copy of framework code in `$AOPS`
- Enables consistent updates across all projects
- Maintains clear separation from user data in `$ACA_DATA`

---

## Installation Model

### Three-Component System

academicOps operates as three distinct components:

| Component | Location | Purpose | Persistence |
|-----------|----------|---------|-------------|
| **Framework** | `$AOPS` | Code, skills, hooks, tests | Read-only during execution |
| **User Data** | `$ACA_DATA` | Knowledge base, personal context | Primary data store |
| **CLI Config** | `~/.claude/` | Session configuration (symlinked) | Derived from `$AOPS` and `$ACA_DATA` |

### Installation Steps

1. **Download framework** from GitHub releases
2. **Extract to** `$AOPS` directory (e.g., `~/src/aOps`)
3. **Run setup script** which creates symlinks in `~/.claude/`
4. **Set environment variables**:
   ```bash
   export AOPS="/home/user/src/aOps"
   export ACA_DATA="/home/user/writing/data"
   ```

### Multi-Project Workflow

Once installed, academicOps enables seamless multi-project work:

```
Project A                    Project B
├── .claude/                 ├── .claude/
│   └── CLAUDE.md (A)        │   └── CLAUDE.md (B)
│   └── skills/→$AOPS        │   └── skills/→$AOPS
│   └── hooks/→$AOPS         │   └── hooks/→$AOPS
└── [project files]          └── [project files]

                ↓ Both projects ↓

         Single Knowledge Base
         $ACA_DATA/
         ├── projects/aops/   (shared framework context)
         ├── tasks/           (unified task management)
         ├── sessions/        (all session logs)
         └── [bmem entities]  (searchable across projects)
```

**Result**: Create a note in Project A, search it from Project B. Task management, session history, and all personal knowledge remains consistent across projects.

---

## Data Organization

### Markdown Format

All knowledge base files use **bmem format** - markdown with YAML frontmatter:

```yaml
---
title: Clear Descriptive Title
permalink: url-safe-slug
type: note|project|task|person|decision|spec
tags:
  - tag1
  - tag2
created: YYYY-MM-DDTHH:MM:SSZ
updated: YYYY-MM-DDTHH:MM:SSZ
---

# Clear Descriptive Title

## Context
Brief background and purpose.

## Observations
- [category] Atomic fact or insight #tag1 #tag2

## Relations
- relation_type [[Related Entity Title]]
```

### Directory Structure

Knowledge base content is organized in `$ACA_DATA/`:

```
$ACA_DATA/
├── projects/
│   └── aops/                   # aOps project-specific data
│       ├── VISION.md           # End state vision
│       ├── ROADMAP.md          # Maturity progression (0-5)
│       └── experiments/        # Framework experiment logs
│           └── LOG.md          # Learning patterns (append-only)
│
├── tasks/                      # Task management
│   ├── inbox/                  # New tasks
│   ├── in-progress/            # Active tasks
│   ├── completed/              # Finished tasks
│   └── archived/               # Old tasks
│
├── sessions/                   # Claude Code session logs
│   └── YYYY-MM-DD_HH-MM-SS.md
│
├── context/                    # Contextual information
├── goals/                      # Goals and objectives
└── [other entities]/           # People, orgs, concepts, etc.
```

---

## Testing Strategy

### CWD Invariance Tests

The primary test validating bmem write location is `test_bmem_diagnostic.py`:

```python
@pytest.mark.integration
def test_bmem_writes_to_aca_data_not_tmp(claude_headless):
    """Verify bmem writes to $ACA_DATA regardless of CWD.

    Steps:
    1. Runs Claude from /tmp (automatic with fixture)
    2. Creates a unique note via bmem with identifiable marker
    3. Searches both locations:
       - /tmp/claude-test-* (test execution directory)
       - $ACA_DATA (knowledge base)
    4. Verifies file found in $ACA_DATA, not /tmp
    5. Confirms write location invariance
    """
```

**Key insight**: This test runs from `/tmp` to eliminate any possibility of relative path traversal or project-relative location detection. If files appear in `/tmp`, the test fails. If files appear in `$ACA_DATA`, the architecture is correct.

### Diagnostic Outputs

The test provides diagnostic outputs:

```
Diagnostic Results:
  Marker: diagnostic_test_1234567890
  Found in $ACA_DATA: Yes
  Writing root: /home/user/writing/data
  Relative path: projects/test/diagnostic_test.md
  Absolute path: /home/user/writing/data/projects/test/diagnostic_test.md
  Found in /tmp: No (correct)
```

### Running Tests

Run all bmem diagnostic tests:

```bash
pytest /home/nic/src/aOps/tests/integration/test_bmem_diagnostic.py -v
```

Run from any working directory - the test will still verify correct behavior.

---

## Design Decisions

### Why Single Knowledge Base?

1. **Unified search** - Query across all projects simultaneously
2. **Consistency** - No duplicated knowledge across multiple stores
3. **Portability** - Knowledge follows user, not tied to specific project
4. **Simplicity** - Single environment variable to configure location

### Why $ACA_DATA Invariance?

1. **Explicit configuration** - User controls data location, not framework
2. **Privacy** - User data separate from framework code repositories
3. **Auditability** - All persistence goes to single known location
4. **CWD independence** - Works seamlessly in any execution context

### Why Symlinks for Framework?

1. **Single source of truth** - One copy of framework code in `$AOPS`
2. **Easy updates** - Update framework once, all projects inherit changes
3. **Reduced duplication** - No per-project copies of shared code
4. **Clear ownership** - Framework code in repo, user data separate

---

## Guarantees and Constraints

### Hard Guarantees

- bmem ALWAYS writes to `$ACA_DATA`, never to project directories
- All writes are absolute path-based, never relative to CWD
- Environment variable resolution is fail-fast (no auto-detection for user data)
- Framework and user data are completely separated

### Constraints

- `$ACA_DATA` MUST be set before any bmem operation
- `$ACA_DATA` path MUST exist (no automatic creation)
- Framework code is read-only from bmem perspective (no persistence back to `$AOPS`)

### Failure Modes

If `$ACA_DATA` is not set:
```
RuntimeError: ACA_DATA environment variable not set.
Add to ~/.bashrc or ~/.zshrc:
  export ACA_DATA='$HOME/writing/data'
```

If `$ACA_DATA` path doesn't exist:
```
RuntimeError: ACA_DATA path doesn't exist: /home/user/writing/data
```

---

## Integration Points

### Claude Code Session Start

When Claude Code starts in a project:

1. `CLAUDE.md` is loaded from `.claude/CLAUDE.md`
2. SessionStart hook (`sessionstart_load_axioms.py`) injects framework principles
3. bmem tools become available immediately
4. All operations target `$ACA_DATA` from that moment

### Slash Commands

Slash commands (like `/bmem`) use the same path resolution:

```bash
# From any project directory
/bmem create "My Note"
# → Writes to $ACA_DATA/...
```

### Search and Query

bmem search operations:

```python
# From skill or command
from lib.paths import get_data_root
data_root = get_data_root()
# Search within $ACA_DATA, regardless of CWD
```

---

## Summary

BMEM architecture achieves **single unified knowledge base** through:

| Principle | Implementation | Result |
|-----------|---|---|
| Environment guarantee | `$ACA_DATA` required, fail-fast validation | Explicit, auditable configuration |
| Write invariance | Absolute path resolution, never CWD-relative | Works from `/tmp`, project root, anywhere |
| Separation | Framework (`$AOPS`) vs Data (`$ACA_DATA`) | Clean architecture, easy updates |
| Symlinks | Framework config in `~/.claude/` | Single source of truth |
| Testing | CWD-invariant diagnostic tests | Architectural guarantees verified |

The result is a **portable, auditable, multi-project knowledge base** that gives users one consistent source of truth regardless of current working directory or project context.

---

## References

- **BMEM-FORMAT.md** - Complete bmem markdown format specification
- **BMEM-CLAUDE-GUIDE.md** - Practical guide for creating bmem files
- **lib/paths.py** - Path resolution implementation (single source of truth)
- **tests/integration/test_bmem_diagnostic.py** - CWD invariance verification
- **README.md** - Framework directory structure overview
