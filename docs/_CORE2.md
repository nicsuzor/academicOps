# User-Specific Context

This is Nicolas Suzor's personal writing workspace and command center for LLM agents managing academic work and personal projects. You are an agent helping automate research tasks within this environment.

## CRITICAL: Repository Ownership

**You are currently working in:**

- OUTER: `nicsuzor/writing` (PRIVATE, parent project, polyrepo)
- Agent framework: `nicsuzor/academicOps` (PUBLIC, at `bot/`)
- Buttermilk: `nicsuzor/buttermilk` (PUBLIC, at `projects/buttermilk/`)

**NEVER assume repository names. ALWAYS verify before GitHub operations.**

## User

Nic: Law professor with ADHD, researching tech fairness. Needs zero-friction capture, clean task separation, concise communication.

## Auto-Extraction

Extract during conversation (ADHD-optimized): tasks → `data/tasks/inbox/`, projects → `data/projects/`, goals → `data/goals/`. Extract immediately, infer when unclear, maintain flow.

## Major Work Projects

### Buttermilk

Foundational Python framework for computational research in Humanities/Social Sciences ("MLOps for HASS scholars"). Provides agents, flows, and reproducible research pipelines. Core infrastructure that supports multiple research projects.

- **Repository**: `nicsuzor/buttermilk`
- **Path:** `projects/buttermilk/`
- **Priority:** P1 - Critical infrastructure with 4 dependent projects

**Key Notes:**

- Test all dependents before making changes
- Breaking changes require approval
- Uses Hydra config, Pydantic contracts, async I/O
- Data stored in GCS/BigQuery, tracked in Weights & Biases

### academicOps: public scholarly automation resource

Public framework for AI-assisted academic work. Modular instruction library, workflows, and tools for other researchers. Being refactored from personal toolset to reusable platform.

- **Repository:** `nicsuzor/academicOps`
- **Path:** `bot/`

### Automod Demo (automod.cc)

High-impact public demo and accountability tool. Terminal-style web interface for running AI-powered content moderation research. Demonstrates Buttermilk capabilities for evaluating AI models against journalism ethics guidelines (GLAAD, TJA, GBV standards).

- **Repository:** `nicsuzor/automod.cc` (frontend), uses buttermilk backend
- **Path:** `projects/automod.cc/`

**Key Notes:**

- SvelteKit frontend + Buttermilk Python backend
- Evaluation data in BigQuery, analysis via Looker Studio
- Focus on "proving and selling" not further development
- JUDGE→SYNTH evaluation pattern with stochastic testing

### DBR: Digital Bills of Rights thematic extraction

**Repository** nicsuzor/dbr **Path**: `projects/dbr/`

### 6. ZotMCP (Zotero RAG Agent)

Custom MCP server providing semantic search over Zotero research library. Vectorizes full-text documents using Buttermilk, exposes 7 tools for search, item retrieval, and similarity finding. Enables AI writing assistants to access scholarly literature.

- **Repository:** `nicsuzor/zotmcp`
- **Path:** `projects/zotmcp/`
- **Priority:** Medium - Supporting tool for academic writing

### 7. OSB ChatMCP (Oversight Board Chatbot)

MCP server for searching and analyzing Meta Oversight Board case decisions. Contains AI-generated IRAC-format legal summaries of all cases. Provides semantic search and case retrieval tools.

- **Repository:** `nicsuzor/osbchatmcp`
- **Path:** `projects/osbchatmcp/`

## Writing Style (Content Production)

When drafting content in user's voice (academic writing, reviews, emails, etc.):

@docs/STYLE-QUICK.md (quick reference - use for most tasks) @docs/STYLE.md (comprehensive guide - use for deep writing tasks)

## Further Reading

Cross-project deps: `docs/CROSS_CUTTING_CONCERNS.md`, Project registry: `docs/projects/INDEX.md`
