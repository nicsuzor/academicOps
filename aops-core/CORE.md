# academicOps Framework Core

You are operating within the **academicOps** framework. This file provides the essential baseline context needed for every session.

## Core Capabilities (MCP Servers)

- **Knowledge & Tasks** (`pkb`): Semantic search, task management, knowledge graph traversal. Primary store for research and operations.
- **Academic references** (`zot`): Zotero library search and academic paper discovery (OpenAlex).
- **Communication** (`outlook`): Email processing and calendar management.
- **Documentation** (`context7`): Up-to-date documentation and code examples for programming libraries.

## Essential Workflows

- **Tasks**: Use the **task skill** (`/pull`, `/q`, `/plan`) for all task operations. **Do NOT write task files directly**; always use the provided skills or scripts. Refer to `aops-core/SKILLS.md` for full trigger list.
- **Email → Task workflow**: When asked to "check my email for tasks", "process emails", find "any new tasks from email", "email triage", "review emails for action items", or see "what's in my inbox that needs action", invoke the **email-task-capture** workflow to **extract** and **categorize** tasks. See [[email-capture.md]] for detailed guidance.
- **Learning**: If you hit friction or a bug, use `/learn` to capture it.
- **Context**: Use `/hydrate` to enrich task context or `/aops` to discover capabilities.
- **Handover**: Use `/dump` before ending the session to record progress and follow-up tasks.

## Principles

- **Fail-Fast**: Stop immediately if instructions are unclear or tools fail. No fallbacks, no guesses.
- **Verify**: Never claim success without empirical evidence (logs, tests, QA).
- **Institutional Memory**: Prefer existing framework patterns over creating new ones. Update instructions at source.

See [[README.md]] for full documentation.
