# User-Specific Instructions

**This file is read on EVERY session start. Keep it minimal.**

## User Context

- **Nic**: Law professor with ADHD researching tech fairness
- **Needs**: Zero-friction capture, clean task separation, efficient design, concise communication
- **Work Style**: Commitment to highest quality, academic rigor, professional standards

## Repository Information

**Owner**: nicsuzor **Primary Repos**:

- Parent repo: `/home/nic/src/writing/` (PRIVATE)
- Agent framework: `nicsuzor/academicOps` (PUBLIC, submodule at `bot/`)
- GitHub issues tracked centrally in `nicsuzor/academicOps`

## Polyrepo Structure

```
/home/nic/src/writing/
├── bot/                    # academicOps (nicsuzor/academicOps)
├── projects/
│   ├── buttermilk/        # Core infrastructure (4 dependents)
│   ├── zotmcp/            # Zotero MCP server
│   ├── osbchatmcp/        # Oversight Board MCP
│   ├── automod.cc/        # Research project
│   ├── dbr/               # Research project
│   ├── mediamarkets/      # Research project
│   └── wikijuris/         # Research project
└── data/
    ├── goals/
    ├── projects/
    └── tasks/
```

## Cross-Cutting Concerns

**buttermilk**: Shared by 4 projects

- Changes require testing ALL dependents
- Breaking changes require user approval

**GitHub Issue Management**:

- ALL agent training issues → `nicsuzor/academicOps`
- Project-specific issues → project repos
- Always search before creating new issues
- Tag with `prompts` label for agent instruction issues

## Auto-Extraction (ADHD-Optimized)

Extract information DURING conversation:

- Tasks with deadlines → `data/tasks/inbox/`
- Project updates → `data/projects/*.md`
- Goals → `data/goals/*.md`
- Use `bot/scripts/task_add.py` for task creation

**Principles**:

1. Extract immediately, don't ask for clarification
2. Infer when unclear
3. Maintain conversation flow
4. Save everything

## Interaction Modes

**Default**: WORKFLOW MODE

- Follow established workflows exactly
- NO improvisation, NO workarounds, NO skipping steps
- HALT on ALL errors

**Other modes**: Require explicit permission to switch

## Writing Style

When drafting in author's voice:

- Quick reference: `docs/STYLE-QUICK.md`
- Comprehensive: `docs/STYLE.md`

## Scope Detection

**Before ANY work**, detect project context:

```bash
pwd | grep -oE 'projects/[^/]+' | cut -d/ -f2
cat docs/projects/INDEX.md
cat docs/projects/{project_name}.md  # if in submodule
```

## Path Configuration

Use absolute paths:

- Production: `/home/nic/src/writing/`
- Data: `/home/nic/src/writing/data/`
- Projects: `/home/nic/src/writing/projects/`

## Further Information

- **Cross-project dependencies**: See `docs/CROSS_CUTTING_CONCERNS.md`
- **Project registry**: See `docs/projects/INDEX.md`
- **Error handling**: See `docs/error-quick-reference.md`
- **User accommodations**: See `docs/accommodations.md`
