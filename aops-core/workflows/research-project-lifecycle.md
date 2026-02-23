---
id: research-project-lifecycle
category: academic
bases: [base-task-tracking, base-verification, base-commit, base-handover, base-dogfood]
status: draft
---

# Research Project Lifecycle

**DRAFT** — End-to-end workflow for a research project from inception to publication.

## Purpose

Procedural requirements for multi-month research projects where academic integrity, evidence trails, and review stages are critical. This workflow composes base workflows with research-specific gates.

## Phases

### 1. Inception

- Define research question and scope
- Literature review (invoke relevant skills)
- Methodology design
- Human approval gate: research design sign-off

### 2. Data Collection

- Data management plan
- Collection procedures (invoke relevant skills)
- Provenance tracking: every dataset gets a source record
- Integrity gate: data handling complies with ethics approval

### 3. Analysis

- Pre-registration of analysis plan (where applicable)
- Execute analysis (invoke `/analyst` or relevant skills)
- Reproducibility gate: analysis must be re-runnable from source data

### 4. Writing

- Draft sections iteratively (invoke relevant skills)
- Citation integrity: all claims traced to sources
- Human review gate: co-author review before submission

### 5. Review and Publication

- Submission preparation
- Peer review response (invoke `/peer-review` skill)
- Revision cycles with tracked changes
- Final human approval: publication sign-off

## Key Procedural Requirements

- **Evidence trail**: Every claim traceable to data, every dataset traceable to source
- **Human gates**: Research design, co-author review, publication sign-off
- **Reproducibility**: Analysis re-runnable, data management documented
- **Integrity**: Ethics compliance, conflict of interest declarations
