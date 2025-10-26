---
name: error
description: Quick experiment outcome logging to academicOps - works from any repository
---

# Quick Error/Outcome Logger

Quickly log experiment outcomes, agent failures, or observations to the academicOps repository without the full /log-failure diagnostic workflow.

## Usage

```
/error <brief description of what happened>
```

**Examples**:
- `/error agent blamed upstream library instead of taking responsibility`
- `/error experiment failed - agent still writes to accomplishments.md during email processing`
- `/error success - tool failure protocol working, agent stopped after 2 attempts`

## Your Task

1. **Get repository**: Use repository from CLAUDE.md (logs to nicsuzor/academicOps regardless of current directory).

2. **Get experiment context** from user's description:
   - What failed/succeeded?
   - Which experiment (if mentioned)?
   - Issue number (if mentioned)?

3. **Quick log format**:
   ```markdown
   ## [Date] Quick Log: [Brief title]

   **Observation**: [User's description]

   **Context**: [Any relevant issue numbers, experiment files, or components]

   **Logged by**: /error command
   ```

4. **Determine destination**:

   **IF user mentions issue number** (e.g., "issue 155" or "#155"):
   - Post as comment to that issue

   **ELSE IF user mentions recent experiment** (check `experiments/` for recent files):
   - Post to related issue from experiment metadata
   - OR append to experiment file Results section

   **ELSE** (no clear destination):
   - Ask user: "Should I log this to an existing issue number, or create new issue?"

5. **Log it**:
   ```bash
   # If posting to issue
   gh issue comment [number] --repo nicsuzor/academicOps --body "$(cat <<'EOF'
   [Your formatted log]
   EOF
   )"

   # If appending to experiment file
   # Use Edit tool to add to Results or Outcome section
   ```

6. **Confirm** to user:
   - "Logged to issue #[number]" OR
   - "Appended to experiment file [path]"

## What NOT to do

- ❌ Don't create full diagnostic analysis
- ❌ Don't search for root causes
- ❌ Don't propose solutions
- ❌ Don't create new experiment logs (unless user explicitly asks)
- ❌ Don't run enforcement hierarchy decision tree
- ❌ Don't invoke trainer workflow

## What to DO

- ✅ Just capture the observation quickly
- ✅ Link to relevant issues/experiments if obvious
- ✅ Keep it under 5 lines
- ✅ Get it logged and move on

## Examples

**User**: `/error agent blamed upstream library`

**You**:
```bash
gh issue comment 155 --repo nicsuzor/academicOps --body "## 2025-10-24 Quick Log: Agent defensive behavior

**Observation**: Agent blamed upstream library instead of taking responsibility for failure.

**Logged by**: /error command"
```

Response to user: "Logged to issue #155"

---

**User**: `/error experiment working - accomplishments boundary respected`

**You**:
```bash
gh issue comment 152 --repo nicsuzor/academicOps --body "## 2025-10-24 Quick Log: Success

**Observation**: Experiment working - accomplishments boundary respected.

**Logged by**: /error command"
```

Response to user: "Logged to issue #152"

---

**User**: `/error new pattern - agents keep forgetting to commit after finishing work`

**You**: "Should I log this to an existing issue number, or create new issue?"

(Wait for user response, then log accordingly)

## Note

This command always logs to nicsuzor/academicOps (documented in CLAUDE.md).
