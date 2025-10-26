# Conventional Commits Format Guide

Complete reference for conventional commit message format.

## Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

## Components

### Type (Required)

The type of change being committed:

- **fix**: Bug fix (correlates with PATCH in semver)
- **feat**: New feature (correlates with MINOR in semver)
- **docs**: Documentation only changes
- **style**: Changes that don't affect code meaning (white-space, formatting, etc.)
- **refactor**: Code change that neither fixes a bug nor adds a feature
- **perf**: Performance improvement
- **test**: Adding missing tests or correcting existing tests
- **build**: Changes to build system or external dependencies
- **ci**: Changes to CI configuration files and scripts
- **chore**: Other changes that don't modify src or test files
- **revert**: Reverts a previous commit

### Scope (Optional but Recommended)

The area of the codebase being changed:

**Repository-specific examples**:

For bot/ repository:
- `prompts` - Agent instructions and definitions
- `infrastructure` - Scripts, hooks, configurations
- `docs` - Documentation files
- `skills` - Skill definitions

For application projects:
- `api` - API endpoints and routes
- `models` - Data models and schemas
- `ui` - User interface components
- `tests` - Test files
- `config` - Configuration files
- `auth` - Authentication/authorization
- `database` - Database migrations and queries

Choose scopes that make sense for your repository structure.

### Subject (Required)

Brief summary of the change:

- Use imperative, present tense: "change" not "changed" nor "changes"
- Don't capitalize first letter
- No period (.) at the end
- Limit to 72 characters or less
- Focus on WHY, not WHAT (the diff shows what changed)

**Good examples**:
- `fix validation error in login form`
- `add real-time notifications`
- `improve query performance for user search`

**Bad examples**:
- `Fixed bug` (too vague)
- `Changes to the authentication system` (not imperative, too vague)
- `Update README.md` (what's in the diff, not why it matters)

### Body (Optional)

Detailed explanation of the change:

- Use imperative, present tense (same as subject)
- Explain the motivation for the change
- Contrast with previous behavior
- Include relevant context
- Wrap at 72 characters

**Example**:
```
Refactor authentication to use JWT tokens instead of sessions.

The session-based approach was causing scalability issues with
distributed deployments. JWT tokens allow stateless authentication
and improve horizontal scaling.
```

### Footer (Optional)

Reference issues, breaking changes, or other metadata:

**Issue references**:
```
Fixes #123
Closes #456, #789
Relates to #101
```

**Breaking changes**:
```
BREAKING CHANGE: API endpoint /auth/login now requires email instead of username
```

**Claude Code attribution** (ALWAYS include):
```
🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

## Complete Examples

### Feature Addition

```
feat(auth): add password reset functionality

Implements email-based password reset workflow with secure tokens.
Tokens expire after 1 hour for security.

Fixes #42

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Bug Fix

```
fix(api): prevent duplicate user registration

Add unique constraint on email field and handle constraint violations
gracefully with 409 Conflict response.

Fixes #78

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Documentation

```
docs(readme): add installation instructions

Include prerequisites, setup steps, and common troubleshooting issues
to help new contributors get started quickly.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Refactoring

```
refactor(database): extract query logic to repository pattern

Separate database queries from business logic for better testability
and maintainability. No functional changes.

Relates to #101

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Test Addition

```
test(auth): add integration tests for login flow

Test successful login, invalid credentials, and account lockout after
multiple failed attempts.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Breaking Change

```
feat(api)!: change user response format

BREAKING CHANGE: User API now returns snake_case fields instead of
camelCase to match rest of API conventions.

Migration guide: Update client code to use snake_case field names
(e.g., first_name instead of firstName).

Fixes #234

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

Note the `!` after type/scope to indicate breaking change.

## Best Practices

1. **Keep commits atomic**: One logical change per commit
2. **Write meaningful subjects**: Reader should understand the change without seeing the diff
3. **Use body for context**: Explain why, not what (diff shows what)
4. **Reference issues**: Link commits to tracking system
5. **Be consistent**: Follow project conventions for scopes and types
6. **Keep it concise**: Subject under 72 chars, body wrapped at 72 chars

## Tools

Check commit message format:
```bash
# View last commit
git log -1

# View last commit with full message
git log -1 --format=%B
```

## Resources

- Conventional Commits specification: https://www.conventionalcommits.org/
- Semantic Versioning: https://semver.org/
