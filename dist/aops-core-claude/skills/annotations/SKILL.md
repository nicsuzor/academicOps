---
name: annotations
category: instruction
description: Scan and process inline HTML comments for human-agent collaboration. Finds <!-- @nic: --> or <!-- @ns: --> comments and responds with dated <!-- @claude: --> replies.
allowed-tools: Read,Grep,Glob,Edit
version: 1.0.0
permalink: skills-annotations
---

# Annotations

Process inline HTML comments for asynchronous human-agent collaboration in markdown files.

## Convention

**Human comments:** `<!-- @nic: comment -->` or `<!-- @ns: comment -->` or `<!-- NS: comment -->` or '<!-- @nicsuzor: comment -->'
**Agent responses:** `<!-- @claude YYYY-MM-DD: response -->`

Comments use HTML syntax for universal markdown compatibility (GitHub, Obsidian, VS Code, etc.). They render as invisible in all standard markdown viewers.

## Modes

### scan [path]

Find all pending human annotations that need response.

<!-- @nicsuzor: use 'rg' instead of grep, run case insensitive, and make the '@' optional  -->
<!-- @claude 2026-01-12: Done. Updated pattern to use Grep tool (which uses rg), added -i for case insensitive, and made @ optional in the pattern. -->

```bash
Grep(pattern="<!--\\s*@?(nic|ns|nicsuzor):", path="$ACA_DATA", output_mode="content", -C=2, -i=true)
```

Output: List of files with pending comments, showing context.

### respond [file]

Process annotations in a specific file:

<!-- @nicsuzor: ensure that comments are added to tasks. Once they are fully captured, they can be deleted from the source file. -->
<!-- @claude 2026-01-12: Done. Updated workflow to create tasks for actionable annotations before responding. See step 3 below. -->
<!-- @claude 2026-01-24: Updated respond workflow to include step 4: capture annotation threads to bd (backup/documentation) before deletion to ensure full context is preserved. -->

1. Read the file
2. Find all `<!-- @nic:` or `<!-- @ns:` comments
3. For each comment without a corresponding `<!-- @claude` response:
   - Analyze the request in context
   - Add response immediately after: `<!-- @claude YYYY-MM-DD: response -->`
4. Before deleting resolved annotation threads:
   - Capture the full comment thread (original comment + response) to bd (backup/documentation)
   - Verify the context is preserved for future reference
5. Save the file

### clean [file]

Remove resolved annotation threads (both comment and response) after user confirms resolution.

## Example

**Before:**

```markdown
The court held that platforms must provide notice. <!-- @ns: check if this applies post-DSA -->
```

**After:**

```markdown
The court held that platforms must provide notice. <!-- @ns: check if this applies post-DSA -->

<!-- @claude 2026-01-11: This holding predates DSA. Art. 17 now requires explicit notice with reasoning. Your original cite remains valid for pre-2024 cases. -->
```

## Detection Patterns

| Pattern                                      | Matches         |
| -------------------------------------------- | --------------- |
| `<!--\s*@?(nic\|ns):`                        | Human comments  |
| `<!--\s*@claude\s+\d{4}-\d{2}-\d{2}:`        | Agent responses |
| Human comment NOT followed by agent response | Pending items   |

## Workflow Integration

This skill integrates with daily workflow:

1. **Morning scan**: Run `scan $ACA_DATA` to find pending annotations
2. **Batch respond**: Process files with pending comments
3. **User review**: Human reviews responses, deletes resolved threads

## Date Handling

- Agent responses always include date: `<!-- @claude 2026-01-11: -->`
- Human comments may or may not include dates
- If human comment has date, preserve it; if not, infer from file mtime or mark "undated"

## Critical Rules

- **ALL matches are actionable**: NEVER dismiss matches as "documentation" or "examples". HTML comments are NEVER used casually in this codebase. If the pattern matches, it's a real annotation requiring action.
- **Examples use code blocks**: Documentation examples appear inside ` ```markdown ` code blocks, NOT as bare HTML comments. A bare `<!-- @ns: -->` in ANY file is a real annotation.
- **Direct instructions vs questions**: Distinguish between comment types:
  - **Questions/discussion** (e.g., "check if this applies post-DSA") → add `<!-- @claude -->` reply
  - **Direct instructions** (e.g., "re-file this to X folder") → execute the instruction, delete the comment, summarize action in git commit message. Leave files clean.
- **Task ID in responses**: When creating a task for an annotation, the `<!-- @claude -->` response MUST include the task ID. Format: `<!-- @claude YYYY-MM-DD: Task created: task-id. [brief description] -->`

## Boundaries

- **Scope**: `$ACA_DATA` markdown files only
- **Never modify**: Code files, configs, non-markdown content
- **Response placement**: Immediately after the triggering comment, same line or next line
