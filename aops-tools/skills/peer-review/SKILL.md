---
name: peer-review
category: instruction
description: Scaffold peer review workflow for grant/fellowship applications. Creates workspace, downloads criteria, generates review template, and creates bot-assigned subtasks for each application.
allowed-tools: Read,Write,Edit,Bash,Glob,WebFetch,WebSearch,mcp__plugin_aops-core_tasks__create_task,mcp__plugin_aops-core_tasks__update_task,mcp__plugin_aops-core_tasks__get_task,mcp__plugin_aops-core_tasks__decompose_task
version: 1.0.0
---

# Peer Review Workflow

Scaffold structured peer review for grant or fellowship applications with bot-assigned subtasks for parallel processing.

## Inputs

Before starting, gather:

1. **Assessment package** - Zip file or folder containing application PDFs
2. **Scheme identifier** - e.g., "ARC FT26", "NHMRC Ideas 2026"
3. **Parent task ID** - Task to nest review tasks under (create if none exists)
4. **Workspace path** - Where to set up review folder (default: `data/reviews/<scheme-slug>/`)

## Phase 1: Setup

### 1.1 Create Workspace Structure

```
<workspace>/
├── documents/       # Application PDFs and criteria docs
├── notes/          # Transcripts and working notes
├── outputs/        # Final review documents
└── templates/      # Review template for this scheme
```

### 1.2 Download/Locate Assessment Criteria

Find official assessment criteria for the scheme:
- Search for "[scheme name] assessor handbook" or "assessment criteria"
- Download PDF to `documents/`
- Extract key criteria structure for template

### 1.3 Create Review Template

Generate `templates/review-template.md` based on criteria structure:

```markdown
# [Scheme] Assessment

**Application ID**: {{APPLICATION_ID}}
**Candidate**: {{CANDIDATE_NAME}}
**Institution**: {{INSTITUTION}}
**Project Title**: {{PROJECT_TITLE}}

---

## [Criterion 1] ([Weight]%)

### [Sub-criterion 1.1]
- Assessment notes:

### [Sub-criterion 1.2]
- Assessment notes:

**Score**: [ ] A | [ ] B | [ ] C | [ ] D | [ ] E

**Comments** (min [N] chars):

---

[Repeat for each criterion...]

---

## Overall Assessment

**Overall Score**: [ ] A | [ ] B | [ ] C | [ ] D | [ ] E

**Overall Comments** (min [N] chars):

---

## Scoring Guide

[Include scheme-specific scoring bands]
```

### 1.4 Extract Applications

If assessment package is a zip:
```bash
unzip <package>.zip -d <workspace>/documents/
```

List all application PDFs to identify application IDs.

## Phase 2: Task Scaffolding

For each application PDF:

### 2.1 Create Parent Review Task

```python
create_task(
    title="Review <APP_ID>",
    type="task",
    project="<scheme-slug>",
    parent="<parent-task-id>",
    body="Review [[<APP_ID>]] for [[<Scheme>]] round.\n\nApplication: documents/<filename>.pdf"
)
```

### 2.2 Create Subtasks

Create 3 subtasks per application, all with `tags: ["bot"]` for automated processing:

**Subtask 1: Transcribe**
```python
create_task(
    title="Transcribe <APP_ID>",
    type="action",
    parent="<review-task-id>",
    order=0,
    tags=["bot"],
    body="Convert PDF to markdown.\n\nSource: documents/<APP_ID>.pdf\nOutput: notes/<APP_ID>-transcript.md"
)
```

**Subtask 2: Draft Review Doc**
```python
create_task(
    title="Draft review doc <APP_ID>",
    type="action",
    parent="<review-task-id>",
    order=1,
    tags=["bot"],
    body="Fill template with application details.\n\nTemplate: templates/review-template.md\nOutput: outputs/<APP_ID>-review.md"
)
```

**Subtask 3: Initial Observations**
```python
create_task(
    title="Initial observations <APP_ID>",
    type="action",
    parent="<review-task-id>",
    order=2,
    tags=["bot"],
    depends_on=["<transcribe-task-id>", "<draft-task-id>"],
    body="Note initial observations against assessment criteria.\n\nAppend to: outputs/<APP_ID>-review.md"
)
```

## Phase 3: Execution (Bot Tasks)

After scaffolding, bot-assigned subtasks can be processed:

### Transcribe Task
1. Read PDF using Read tool or pdf-to-md conversion
2. Extract text preserving structure (headings, sections)
3. Write to `notes/<APP_ID>-transcript.md`
4. Mark task complete

### Draft Review Doc Task
1. Copy template to `outputs/<APP_ID>-review.md`
2. Fill metadata fields from application
3. Extract descriptive information (candidate bio, project summary)
4. Mark task complete

### Initial Observations Task
1. Read transcript and criteria
2. For each criterion, note relevant evidence from application
3. Flag gaps or concerns
4. Append observations to review doc
5. Mark task complete

## Assignment Convention

Use **tags** for task assignment:
- `tags: ["bot"]` - Automated/agent work
- `tags: ["human"]` - Manual/user work

Query bot-assigned tasks: `list_tasks(project="<scheme>")` then filter by tag.

## Output Artifacts

After workflow completion:

```
<workspace>/
├── documents/
│   ├── <Scheme>-Assessor-Handbook.pdf
│   ├── <APP_ID_1>.pdf
│   ├── <APP_ID_2>.pdf
│   └── ...
├── notes/
│   ├── <APP_ID_1>-transcript.md
│   ├── <APP_ID_2>-transcript.md
│   └── ...
├── outputs/
│   ├── <APP_ID_1>-review.md
│   ├── <APP_ID_2>-review.md
│   └── ...
└── templates/
    └── review-template.md
```

## Example: ARC Future Fellowships FT26

**Criteria structure** (from Assessor Handbook):
- Investigator/Capability (50%): ROPE, research training, leadership, collaboration
- Project Quality and Innovation (25%): knowledge gap, innovation, research questions, design
- Benefit (15%): new knowledge, benefits for Australia, priority areas
- Feasibility and Strategic Alignment (10%): cost effectiveness, facilities, resources

**Scoring bands**: A (Outstanding ~10%), B (Excellent ~15%), C (Very Good ~20%), D (Good ~35%), E (Uncompetitive ~20%)

**Minimum comment lengths**: 500 chars per criterion, 3500 chars overall
