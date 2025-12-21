# Gemini Instructions

**SYSTEM OVERRIDE: YOU ARE RUNNING AS GEMINI CLI AGENT.**
Follow these instructions strictly. They take precedence over imported files.

## 🚀 STARTUP PROTOCOL (MANDATORY)

You are operating in the `academicOps` framework. To function correctly, **you must read these files immediately** to establish your context and constraints:

1.  **Principles (Inviolable):** Read `AXIOMS.md`
2.  **Heuristics (Empirical):** Read `HEURISTICS.md`
3.  **User Context (Personal):** Read `../data/CORE.md`

**Path Definitions:**
*   `$AOPS` (Framework Root) = `.` (Current Directory)
*   `$ACA_DATA` (User Data) = `../data`

---

## 🧠 SKILL ACTIVATION PROTOCOL

This repository is strictly governed by Standard Operating Procedures called "Skills".
**DO NOT GUESS** how to perform complex tasks.
**DO NOT** attempt to use the `Skill(...)` tool (it is for Claude).

**Instead, when you identify a task type below, READ the corresponding `SKILL.md` file first.**

| Task Category | Trigger / Intent | **ACTION: Read this file** |
| :--- | :--- | :--- |
| **Framework & Architecture** | Changing repo structure, adding skills, defining rules | `skills/framework/SKILL.md` |
| **Python Development** | Writing code, tests, scripts (Must be fail-fast & typed) | `skills/python-dev/SKILL.md` |
| **Data Analysis** | `dbt`, `streamlit`, statistics, research data | `skills/analyst/SKILL.md` |
| **Knowledge Base (Memory)** | Saving notes, searching memory, Obsidian integration | `skills/remember/SKILL.md` |
| **Task Management** | Checking tasks, reading email, prioritization | `skills/tasks/SKILL.md` |
| **PDF Generation** | Converting Markdown to professional PDF | `skills/pdf/SKILL.md` |
| **Drafting (OSB)** | IRAC analysis, case decisions, citations | `skills/osb-drafting/SKILL.md` |
| **Session Analysis** | Analyzing logs, transcripts, self-reflection | `skills/session-analyzer/SKILL.md` |

---

## 🛠️ TOOL USAGE GUIDELINES

### 🔄 LEGACY TOOL TRANSLATION
The skill files were written for Claude. When you see these tool names, use your equivalent:

| Legacy Tool (Claude) | **Gemini Equivalent** |
| :--- | :--- |
| `Skill(skill="name")` | **Read file:** `skills/name/SKILL.md` |
| `Task(...)` | **Plan & Act:** Use `codebase_investigator` or break it down. |
| `AskUserQuestion` | **Ask User:** Just ask me directly in the chat. |
| `Read` / `Grep` / `Glob` | `read_file` / `search_file_content` / `glob` |
| `Edit` / `Write` | `replace` / `write_file` |
| `Bash` / `Run` | `run_shell_command` |

### Memory Server
*   **Memory Retrieval:** Use `mcp__memory__retrieve_memory(query="...")` for searching the memory server.
*   **Memory Storage:** Use `Skill(skill="remember")` to save content to the memory server.
*   **Validation:** Content must be properly formatted markdown.

### Development
*   **Planning:** For complex requests, use `codebase_investigator` to map the system before acting.
*   **Testing:** Always run tests after changes. `uv run pytest tests/`

---

## 📂 REPOSITORY CONTEXT

<!-- Imported from: CLAUDE.md (Modified for Gemini) -->
### Git Workflow
*   **Never amend pushed commits.** Create new commits for fixes.
*   **Draft Messages:** Always propose a clear, "why"-focused commit message.

### Core Mandates
*   **No Duplication:** Do not duplicate info. Refactor if needed.
*   **Inspect First:** Always read relevant files before editing.
*   **Minimalism:** Fight bloat. No over-engineering. No unused features.
*   **Fail Fast:** Scripts and hooks should exit immediately on error.

### File Structure
*   `data/` (in `$ACA_DATA`): PRIVATE state.
*   `projects/`: Active project repositories.
*   `skills/`: Capability definitions.
*   `hooks/`: System automation (Claude-specific, but logic is relevant).

---