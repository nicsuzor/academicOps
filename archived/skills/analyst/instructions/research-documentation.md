---
title: Research Project Documentation Structure
type: note
category: instruction
permalink: analyst-chunk-research-documentation
description: Mandatory documentation structure and maintenance rules for academic research projects
---

# Research Project Documentation Structure

## Overview

Academic research projects require rigorous, transparent, and reproducible documentation. This guide defines the mandatory documentation structure for academicOps research projects.

## Forbidden: Proliferating Random Markdown Files

**🚨 CRITICAL RULE: NO random markdown files. We have a strict structure. Follow it.**

### Prohibited Patterns

❌ **NEVER** create these files:

- `analysis_notes.md`
- `findings_summary.md`
- `weekly_update.md`
- `scratch_notes.md`
- `todo_list.md`
- `random_thoughts.md`
- Any ad-hoc markdown file without defined purpose

❌ **NEVER** proliferate documentation:

- Multiple README files in subdirectories
- Redundant explanations in different files
- "Notes" or "scratch" directories
- Duplicate information across files

### Why This Matters

- **Findability**: Team knows exactly where to look for information
- **Maintenance**: Updates happen in one place, not scattered across files
- **Reproducibility**: Clear structure enables replication
- **Quality**: Forced structure prevents "junk drawer" documentation
- **Version control**: Git history shows meaningful changes, not churn

## Required Documentation Files

Research projects MUST maintain this exact structure:

```
project_root/
├── README.md                    # Project overview and quick start
├── METHODOLOGY.md              # Research design and approach
├── dbt/
│   ├── models/                 # Data transformation pipeline
│   │   ├── staging/
│   │   ├── intermediate/
│   │   └── marts/
│   └── schema.yml              # Model and column documentation
├── experiments/                # Experimental work (see experiment-logging.md)
│   └── YYYYMMDD-description/
├── methods/                    # Detailed technical methods
│   ├── method_name.md
│   └── method_name_2.md
├── streamlit/                  # Interactive dashboards
│   └── dashboard.py
└── data/
    └── README.md               # Data sources and schema
```

## Documentation Hierarchy

1. **README.md** (project root)
   - **Purpose**: First file anyone reads
   - **Contents**: Research questions, project status, quick start instructions
   - **Length**: 1-3 pages maximum
   - **Audience**: External collaborators, future you
   - **Update frequency**: When project scope or status changes

2. **METHODOLOGY.md** (project root)
   - **Purpose**: Research design and epistemological approach
   - **Contents**: See [[methodology-files]]
   - **Length**: 2-10 pages depending on complexity
   - **Audience**: Academic peers, reviewers
   - **Update frequency**: When research design changes

3. **data/README.md**
   - **Purpose**: Data provenance and schema documentation
   - **Contents**: Source descriptions, access methods, schema documentation
   - **Length**: Variable (can be extensive for complex datasets)
   - **Audience**: Data analysts, reproducibility auditors
   - **Update frequency**: When data sources change or schema evolves

4. **dbt/schema.yml**
   - **Purpose**: Column-level documentation for transformed data
   - **Contents**: Model purposes, column descriptions, business logic
   - **Length**: Comprehensive (every model and column documented)
   - **Audience**: Data analysts working with warehouse
   - **Update frequency**: Every time models change (MANDATORY)

5. **methods/*.md**
   - **Purpose**: Detailed technical implementation of specific methods
   - **Contents**: See [[methods-vs-methodology]]
   - **Length**: One file per method, as detailed as needed
   - **Audience**: Technical implementers, reproducibility auditors
   - **Update frequency**: When implementation changes

6. **experiments/YYYYMMDD-description/**
   - **Purpose**: Organized experimental work and results
   - **Contents**: See [[experiment-logging]]
   - **Length**: One directory per experiment
   - **Audience**: Research team, future reproducibility efforts
   - **Update frequency**: During active experimentation

## Documentation Maintenance Rules

### Rule 1: Documentation-as-Code

**REQUIRED**: Documentation MUST be kept up to date with code changes.

When you modify:

- **dbt models** → Update `dbt/schema.yml` in SAME commit
- **Methods implementation** → Update `methods/*.md` in SAME commit
- **Data sources** → Update `data/README.md` in SAME commit
- **Research design** → Update `METHODOLOGY.md` in SAME commit

**If documentation is not updated, the code change is INCOMPLETE.**

### Rule 2: Self-Documenting Work

Prefer these INSTEAD of separate documentation:

✅ **Code comments** - Explain WHY decisions were made ✅ **dbt model descriptions** - Inline {{ doc("description") }} in SQL ✅ **Streamlit dashboards** - Interactive explanations with `st.markdown()` ✅ **Jupyter notebooks** - Analysis with inline markdown cells ✅ **GitHub issues** - Track decisions and discussions ✅ **Git commit messages** - Document what and why

### Rule 3: Fail-Fast on Stale Documentation

**If you find stale documentation:**

1. **STOP immediately** - Do not continue with other work
2. **Update the documentation** - Make it current
3. **Commit documentation update** - Separate commit with clear message
4. **Then proceed** with original task

**NEVER:**

- Work around stale documentation
- Make mental notes to "fix it later"
- Create NEW documentation files because old ones are wrong
- Continue coding when documentation is out of date

### Rule 4: One Source of Truth

**Each piece of information lives in EXACTLY ONE place.**

❌ **NEVER**:

- Repeat README content in METHODOLOGY.md
- Duplicate schema documentation between data/README.md and code comments
- Copy method descriptions across multiple files

✅ **ALWAYS**:

- Reference other files when needed: "See `methods/scoring.md` for details"
- Use `@reference` pattern in agent instructions
- Link to GitHub issues for historical context

## Where Different Information Lives

| Information Type          | Location                | Example                               |
| ------------------------- | ----------------------- | ------------------------------------- |
| Research questions        | README.md               | "How does X affect Y?"                |
| Research design           | METHODOLOGY.md          | "We use quasi-experimental design..." |
| Data sources              | data/README.md          | "Data from BigQuery project X..."     |
| Column meanings           | dbt/schema.yml          | "case_id: Unique identifier for..."   |
| Technical implementation  | methods/*.md            | "Scoring algorithm implementation..." |
| Experimental results      | experiments/YYYYMMDD-*/ | "Results from testing approach X"     |
| Data transformations      | dbt models (SQL)        | SQL with inline comments              |
| Analysis narratives       | Streamlit dashboards    | Interactive explanations              |
| Decisions and discussions | GitHub issues           | "Why we chose X over Y"               |
| Code rationale            | Code comments           | "Using X here because Y constraint"   |

## Documentation Quality Standards

All documentation files must be:

- **Current**: Updated with every relevant code change
- **Accurate**: Reflects actual implementation, not plans or wishes
- **Complete**: No TK, TODO, or "coming soon" placeholders
- **Concise**: No redundant information
- **Structured**: Uses headings, lists, tables appropriately
- **Linked**: References other docs when appropriate, no duplication
- **Versioned**: Lives in git, not Notion/Google Docs/Slack

## Enforcement

These documentation standards are MANDATORY, not suggestions.

**Violations are BUGS** and must be:

1. Logged as GitHub issues
2. Fixed immediately
3. Tracked like code defects

**No exceptions.**
