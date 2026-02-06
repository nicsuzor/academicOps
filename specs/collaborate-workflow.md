# Workflow: Collaborate

## Giving Effect

- [[workflows/collaborate.md]] - Workflow definition for interactive collaboration
- [[skills/session-insights/SKILL.md]] - Skill for generating structured summaries from transcripts
- [[specs/session-insights-prompt.md]] - Prompt template for session analysis
- [[specs/session-insights-metrics-schema.md]] - Schema for collaboration metrics

## User Story

As a researcher or developer, I want to have open-ended, interactive collaboration sessions with an AI agent to explore complex problems, brainstorm ideas, or debug issues, so that I can gain clarity and solutions without the constraints of a rigid task workflow.

## The Problem

Collaboration sessions can produce massive amounts of text (thousands of lines).
**Anti-pattern:** Pasting the entire raw transcript into a task body (e.g., `data/aops/tasks/aops-1c2a8c87-collaborate-session-1113.md`).
**Impact:**
- Bloats the task file, making it unreadable.
- Degrades performance of tools processing the task.
- Loses semantic value (the "signal" is lost in the "noise").

## Design

### Output Handling Specification

#### 1. Raw Output Storage
Raw collaboration transcripts MUST be stored in a dedicated file, separate from the task definition.

- **Location:** `data/transcripts/YYYY/MM/` (or `data/collaboration/` if distinct from standard transcripts).
- **Format:** Markdown.
- **Naming:** `YYYYMMDD-{short-topic}-{session-id}.md`.

#### 2. Task Body Content
The task body MUST only contain a **Summary** and a **Reference**.

- **Summary:**
    - Maximum 500 characters (approximate).
    - Captures the *outcome*, *key decisions*, and *next steps*.
- **Reference:**
    - A link to the raw output file: `[Full Transcript](../../data/transcripts/...)`.
    - (Optional) A link to the session insights JSON/report if generated.

#### 3. Integration with Session Insights
The `session-insights` skill is the preferred mechanism for processing collaboration sessions.

- **Workflow:**
    1.  Conduct collaboration session.
    2.  Run `/session-insights` (or `session-insights {session-id}`) to generate a structured summary.
    3.  Copy the "Summary", "Accomplishments", and "Learnings" from the insights into the task body.
    4.  Link the task to the insights file.

#### 4. Process for Future Sessions
When starting a collaboration task:
1.  Create a task with `type: learn` (preferred for exploration) or `task`.
2.  Use the task to track *goals* of the collaboration.
3.  Perform the collaboration (in CLI or Web).
4.  **If CLI:** Use `/session-insights` to process the session.
    - This automatically generates a summary and stores it in `data/sessions/summaries/`.
    - Update the task with the generated summary.
5.  **If Web/External:** Save the transcript to `data/transcripts/...` manually, then summarize into the task.
6.  **Do not** paste the full chat log into the task.

## Acceptance Criteria

1. Raw transcripts are stored in `data/transcripts/` or `data/collaboration/`, never in task bodies.
2. Task bodies contain only a summary (approx. 500 chars) and a reference link to the full transcript.
3. The `/session-insights` skill is used to generate summaries for all CLI-based sessions.
4. Large transcripts (> 10KB) are handled via external reference as per P#69.

## Alignment with Heuristics
- **H1 (Self-Correction):** Reviewing the summary allows identifying if the session drifted.
- **H2 (Fail Fast):** Short summaries make it easier to spot dead-ends than reading 5k lines.
- **H5 (Documentation):** The spec ensures knowledge is captured (in insights) but kept organized (not cluttering task management).

## Related Specs

- [[session-insights-prompt]]
- [[workflow-system-spec]]
- [[session-insights-metrics-schema]]
