---
name: github-issue
description: Manage GitHub issues across any repository with exhaustive search, precise documentation, and proactive updates. Search existing issues before creating new ones, format technical content clearly, link commits and PRs, and maintain issue lifecycle. Works universally - not specific to any project or framework. Use when documenting bugs, tracking features, updating issue status, or searching for related work.
---

# GitHub Issue Management

## Overview

Manage the complete lifecycle of GitHub issues in any repository: search exhaustively for existing issues, create well-formatted new issues, update with new information, link commits and PRs, and maintain clear status. This skill provides universal GitHub issue operations without framework-specific knowledge.

## When to Use This Skill

Use github-issue when:

1. **Documenting a problem or bug** - Need to create or update a GitHub issue
2. **Searching for existing work** - Check if a problem or feature is already tracked
3. **After committing code** - Link commits to related issues
4. **Updating issue status** - Add new information, findings, or progress
5. **Managing issue lifecycle** - Close resolved issues, reopen regressions

**Concrete trigger examples**:
- "Search for issues related to database timeout errors"
- "Create an issue for the authentication bug we just found"
- "Update issue #42 with the commit that fixed it"
- "Find all open issues tagged with 'performance'"
- "Close issue #17 as resolved"

## Core Workflow

This skill uses a **workflow-based** structure centered on the GitHub issue lifecycle.

### Workflow Decision Tree

```
START: Problem, feature, or update identified
↓
Q1: Does an existing issue cover this?
├─ UNKNOWN → Search for existing issues (Step 1)
└─ KNOWN → Is it already tracked?
    ├─ YES → Update existing issue (Step 3)
    └─ NO → Create new issue (Step 2)
```

## Step 1: Search for Existing Issues

**Objective**: Find existing issues before creating duplicates. Always search exhaustively using multiple strategies.

### Search Strategies

**MANDATORY**: Use at least 3 different search approaches before concluding no match exists.

#### Strategy A: Error Message / Technical Term Search

Search for exact phrases from error messages, stack traces, or technical terms:

```bash
gh issue list --repo <owner/repo> --search "error message exact phrase" --state all

# Examples
gh issue list --repo myorg/myapp --search "ConnectionTimeoutError" --state all
gh issue list --repo myorg/myapp --search "ECONNREFUSED 127.0.0.1:5432" --state all
```

**When to use**: You have specific error text or technical identifiers.

#### Strategy B: Keyword Combination Search

Search using combinations of relevant keywords:

```bash
gh issue list --repo <owner/repo> --search "keyword1 keyword2 keyword3" --state all

# Examples
gh issue list --repo myorg/myapp --search "database timeout production" --state all
gh issue list --repo myorg/myapp --search "authentication 401 login" --state all
```

**When to use**: Describing a problem by its symptoms or components.

#### Strategy C: Component / File Path Search

Search by affected components, modules, or file paths:

```bash
gh issue list --repo <owner/repo> --search "path:src/auth" --state all
gh issue list --repo <owner/repo> --search "component-name" --state all

# Examples
gh issue list --repo myorg/myapp --search "AuthService" --state all
gh issue list --repo myorg/myapp --search "path:api/handlers" --state all
```

**When to use**: Problem is localized to specific code areas.

#### Strategy D: Label and Metadata Filters

Search using labels, milestones, authors, or dates:

```bash
# By label
gh issue list --repo <owner/repo> --label bug --state all
gh issue list --repo <owner/repo> --label "needs-investigation" --state all

# By author
gh issue list --repo <owner/repo> --author username --state all

# Recent issues (combined with keyword search)
gh issue list --repo <owner/repo> --search "keyword" --state all --limit 20

# By assignee
gh issue list --repo <owner/repo> --assignee username --state all
```

**When to use**: Narrowing results by context (who reported, when, what type).

#### Strategy E: Closed Issues Check

Don't forget to search closed issues - problems can resurface:

```bash
gh issue list --repo <owner/repo> --search "keyword" --state closed

# Check recently closed
gh issue list --repo <owner/repo> --state closed --limit 20
```

**When to use**: Always check - today's bug might be yesterday's "resolved" issue.

### Search Workflow Example

```bash
# 1. Search by exact error
gh issue list --repo myorg/api --search "TimeoutError: Connection timed out" --state all

# 2. Search by keywords
gh issue list --repo myorg/api --search "database connection timeout" --state all

# 3. Search by component
gh issue list --repo myorg/api --search "DatabaseClient" --state all

# 4. Search by label
gh issue list --repo myorg/api --label "database" --state all

# 5. Review results, look for matches
# 6. If no matches found, proceed to create new issue
```

### Viewing Issue Details

Once you find potential matches, review them:

```bash
gh issue view <number> --repo <owner/repo>

# With comments
gh issue view <number> --repo <owner/repo> --comments

# Examples
gh issue view 42 --repo myorg/api
gh issue view 123 --repo myorg/api --comments
```

**Check for**:
- Is this the same problem?
- Is it still open or was it resolved?
- Are there workarounds or ongoing discussion?
- Should I update this issue or create a new one?

## Step 2: Create New Issue

**Objective**: Document a problem or feature request with all necessary information for others to understand and act on it.

**ONLY create new issues when**:
- Exhaustive search (3+ strategies) confirms no existing issue covers this
- The problem is distinct enough to warrant separate tracking
- You have sufficient information to create a complete, actionable issue

### Issue Creation Workflow

#### 2.1: Prepare Issue Content

Gather required information:

**For bugs**:
- Clear problem summary
- Steps to reproduce
- Expected vs. actual behavior
- Environment details (OS, versions, etc.)
- Error messages and stack traces
- Related file paths or components

**For features**:
- Clear feature description
- Use case / motivation
- Proposed approach (if any)
- Alternatives considered
- Impact / priority

#### 2.2: Choose Title

**Good titles** are:
- Concise (< 80 characters)
- Specific (not vague)
- Searchable (include key terms)

**Examples**:

❌ Bad: "Fix the bug"
✅ Good: "DatabaseClient times out on large queries (>10k rows)"

❌ Bad: "Add feature"
✅ Good: "Add support for PostgreSQL connection pooling"

❌ Bad: "Error in production"
✅ Good: "AuthService returns 500 when token expired (production only)"

#### 2.3: Format Issue Body

Use markdown for clarity. Standard structure:

```markdown
## Problem Summary

[1-2 sentence description of the issue]

## Reproduction Steps

1. [Step 1]
2. [Step 2]
3. [Observe error]

## Expected Behavior

[What should happen]

## Actual Behavior

[What actually happens]

## Error Details

```
[Error message, stack trace - use code blocks]
```

## Environment

- OS: [e.g., Ubuntu 22.04]
- Version: [e.g., v2.1.0]
- Dependencies: [relevant versions]

## Additional Context

[Screenshots, logs, related issues, attempted fixes]

## Related

- Related to #[number]
- Blocks #[number]
- Depends on #[number]
```

#### 2.4: Select Labels

Common label patterns (varies by repository):

**Type labels**:
- `bug` - Something broken
- `enhancement` / `feature` - New functionality
- `documentation` - Docs issues
- `question` - Needs clarification

**Priority labels**:
- `critical` / `high-priority` - Urgent, blocking
- `low-priority` - Nice to have

**Status labels**:
- `needs-investigation` - Requires more info
- `ready` - Ready to work on
- `in-progress` - Being worked on

**Component labels** (repo-specific):
- `database`, `api`, `frontend`, `auth`, etc.

#### 2.5: Execute Issue Creation

```bash
gh issue create --repo <owner/repo> \
  --title "Issue title here" \
  --body "$(cat <<'EOF'
## Problem Summary

Description here.

## Reproduction Steps

1. Step 1
2. Step 2

## Error Details

```
Error text here
```
EOF
)" \
  --label "bug,needs-investigation"

# Example
gh issue create --repo myorg/api \
  --title "DatabaseClient timeout on large queries" \
  --body "$(cat <<'EOF'
## Problem Summary

DatabaseClient times out when executing queries that return >10k rows.

## Reproduction Steps

1. Connect to production database
2. Execute: SELECT * FROM large_table LIMIT 15000
3. Observe timeout after 30 seconds

## Expected Behavior

Query should complete or use pagination automatically.

## Actual Behavior

TimeoutError: Connection timed out after 30s

## Error Details

```
TimeoutError: Connection timed out
  at DatabaseClient.execute (src/db/client.ts:45)
  at QueryHandler.run (src/api/handlers/query.ts:78)
```

## Environment

- Version: v2.1.0
- Database: PostgreSQL 14
- Connection pool: 10 max connections
EOF
)" \
  --label "bug,database,high-priority"
```

**Return**: Issue URL and number to user.

## Step 3: Update Existing Issue

**Objective**: Add new information to an existing issue - findings, progress, commits, or status changes.

### When to Update (Not Create New)

Update existing issues when:
- New information about the same problem
- Commit addresses the issue
- Status change (in progress, blocked, resolved)
- Related findings or workarounds discovered
- Clarifications or additional context

### Adding Comments

```bash
gh issue comment <number> --repo <owner/repo> --body "Comment text"

# With heredoc for multiline
gh issue comment <number> --repo <owner/repo> --body "$(cat <<'EOF'
## Update: [Date or context]

New information here.

**Details**:
- Finding 1
- Finding 2

**Next steps**:
- Action item
EOF
)"

# Example
gh issue comment 42 --repo myorg/api --body "$(cat <<'EOF'
## Update: Fix Deployed

The database timeout fix has been deployed to production.

**Changes**:
- Increased connection pool size to 20
- Added query timeout of 60s (up from 30s)
- Implemented cursor-based pagination for large result sets

**Monitoring**:
- No timeouts observed in past 24 hours
- Query performance improved by 40%

Closing this issue as resolved. Will reopen if timeouts recur.
EOF
)"
```

### Linking Commits and PRs

**When commit addresses an issue**:

```bash
gh issue comment <number> --repo <owner/repo> --body "Fixed in commit <SHA>"

# Example
gh issue comment 42 --repo myorg/api --body "Fixed in commit a1b2c3d: Increase connection pool and add pagination"
```

**Conventional commit messages** (in the commit itself):

```bash
git commit -m "fix(database): Increase connection pool and add pagination

Resolves timeout issues with large queries by:
- Increasing max connections to 20
- Adding cursor-based pagination
- Setting query timeout to 60s

Fixes #42"
```

**For pull requests**:

Use GitHub keywords in PR description:
- `Fixes #42` - Closes issue when PR merges
- `Closes #42` - Same as Fixes
- `Resolves #42` - Same as Fixes
- `Related to #42` - Links but doesn't close

### Closing Issues

Close issues when definitively resolved:

```bash
gh issue close <number> --repo <owner/repo> --comment "Closing reason"

# Example
gh issue close 42 --repo myorg/api --comment "Resolved by commit a1b2c3d. No timeouts in 7 days of production monitoring."
```

**Do NOT close if**:
- Not verified in production
- Workaround only (not root cause fix)
- Uncertain if resolved
- User hasn't confirmed

### Reopening Issues

If a closed issue recurs:

```bash
gh issue reopen <number> --repo <owner/repo> --comment "Reason for reopening"

# Example
gh issue reopen 42 --repo myorg/api --comment "Timeout errors have resumed in production as of 2025-10-21. Original fix insufficient for queries >50k rows."
```

## Step 4: Repository Verification (Security)

**CRITICAL**: Before ANY GitHub write operation, verify the correct repository.

### Verification Protocol

**MANDATORY before**:
- Creating issues
- Adding comments
- Closing/reopening issues
- Any `gh` command that writes

```bash
# Step 1: Verify repository ownership
gh repo view <owner/repo> --json owner -q '.owner.login'

# Step 2: Verify repository name
gh repo view <owner/repo> --json nameWithOwner -q '.nameWithOwner'

# Step 3: Confirm matches expected target
# Expected output should match what you intend

# Example
gh repo view myorg/api --json owner -q '.owner.login'
# Output: myorg
# Confirmed: Correct owner

gh repo view myorg/api --json nameWithOwner -q '.nameWithOwner'
# Output: myorg/api
# Confirmed: Correct repository
```

**Security checklist**:
- [ ] Repository owner verified (not hallucinated)
- [ ] Repository name matches expected target
- [ ] Not posting to wrong account or unrelated repository

**NEVER**:
- Skip verification
- Assume repository names
- Post without confirming ownership

**Rationale**: Prevents leaking sensitive information to wrong GitHub repositories.

## Formatting Best Practices

### Code Blocks

Always use proper markdown code blocks for code, errors, logs:

````markdown
```bash
command here
```

```python
code here
```

```
plain text output or errors
```
````

### Lists and Structure

Use markdown formatting for readability:

**Bullet points**:
```markdown
- Point 1
- Point 2
  - Nested point
```

**Numbered lists**:
```markdown
1. Step 1
2. Step 2
3. Step 3
```

**Headers**:
```markdown
## Section Header
### Subsection Header
```

### Technical Details

**Good examples**:

✅ Include file paths:
```
Error in src/database/client.ts:45
```

✅ Include versions:
```
- Node.js: v18.17.0
- PostgreSQL: 14.2
```

✅ Include exact error messages:
```
TimeoutError: Connection timed out after 30000ms
```

❌ Vague descriptions:
```
There's an error in the database code
```

❌ No specifics:
```
It doesn't work in production
```

## Anti-Patterns to Avoid

**Don't create duplicate issues**:
- ❌ Skip search, create immediately
- ✅ Search with 3+ strategies, verify no match

**Don't create vague issues**:
- ❌ Title: "Fix bug"
- ✅ Title: "DatabaseClient timeout on queries >10k rows"

**Don't forget verification**:
- ❌ `gh issue create --repo username/project` (assumed username)
- ✅ Verify owner first, then create

**Don't over-comment**:
- ❌ Add comment for every tiny update
- ✅ Group related updates into meaningful comments

**Don't close prematurely**:
- ❌ Close issue when code merged (not verified)
- ✅ Close after production verification

**Don't leave orphan issues**:
- ❌ Create issue, never update status
- ✅ Update when commits land, when resolved, when blocked

## Quick Reference

### Search for Issues

```bash
# Multiple search strategies
gh issue list --repo <owner/repo> --search "keywords" --state all
gh issue list --repo <owner/repo> --label "label-name" --state all
gh issue list --repo <owner/repo> --author username --state all

# View issue details
gh issue view <number> --repo <owner/repo> --comments
```

### Create Issue

```bash
# Verify repository first (MANDATORY)
gh repo view <owner/repo> --json owner -q '.owner.login'

# Create issue with proper formatting
gh issue create --repo <owner/repo> \
  --title "Clear, specific title" \
  --body "$(cat <<'EOF'
Formatted content here
EOF
)" \
  --label "bug,component"
```

### Update Issue

```bash
# Add comment
gh issue comment <number> --repo <owner/repo> --body "$(cat <<'EOF'
Update content
EOF
)"

# Close issue
gh issue close <number> --repo <owner/repo> --comment "Resolution details"

# Reopen issue
gh issue reopen <number> --repo <owner/repo> --comment "Recurrence details"
```

### Common Workflows

**Bug reported → Document**:
1. Search for existing issue (3+ strategies)
2. If not found: Create with reproduction steps, error details
3. Label appropriately (bug, component, priority)

**Commit made → Link to issue**:
1. Find related issue number
2. Add comment linking commit
3. Update issue status if resolved

**Issue resolved → Close**:
1. Verify resolution in production
2. Close with verification details
3. Reference fixing commit/PR

## Success Criteria

A well-managed issue achieves:

- ✅ No duplicates (exhaustive search performed)
- ✅ Clear, searchable title
- ✅ Complete technical details (reproduction, environment, errors)
- ✅ Proper formatting (markdown, code blocks)
- ✅ Appropriate labels
- ✅ Linked to related commits, PRs, issues
- ✅ Updated status reflects reality
- ✅ Closed only when verified resolved
