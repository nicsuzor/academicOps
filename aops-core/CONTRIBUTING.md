# Contributing to academicOps

## Core Principle: No Input-Rewriting Shims

**Do not write input-mutation or parameter-alias layers that paper over API mismatches.**

If agents are calling a tool with the wrong parameter names or structure, the fix is **one of**:

1. **Fix the agent** — ensure prompts and examples teach the correct calling convention
2. **Fix the server/tool** — if the API is confusing or inconsistent, change the server-side interface instead
3. **Fix the docs** — ensure examples and reference material show the correct usage

**Do not** create a shim layer in hooks or middleware that:

- Aliases one parameter name to another (`path` → `id`)
- Rewrites the input structure before passing it to the tool
- Silently transforms user input to "fix" their calls

### Why This Matters

Shim layers:

- **Hide root-cause bugs** — agents never learn the correct API, so the bug persists forever
- **Accumulate technical debt** — each new alias or transform makes the next shim harder to reason about
- **Violate the hook contract** — hook output schema violations trigger UI errors that confuse users
- **Are hard to remove** — once agents learn to rely on the shim, removing it breaks their workflows

### Historical Example

In `aops-core/hooks/router.py`, a PKB alias-rewrite block (removed in task-40390848) did all of these:

- Aliased `path` → `id`, `task_id` → `id`, `task_title` → `title`
- Emitted `updatedInput` as a JSON string (violating the `dict` schema)
- Caused "Hook JSON output validation failed" errors every time it fired
- Hid the fact that the PKB server's API was incomplete

The fix: rewrite all examples and prompts to use the correct parameter names, then **delete the shim entirely**.

### When You Hit This Situation

If you find agents are calling a tool incorrectly:

1. **Diagnose** — is it a docs problem, API design problem, or agent training problem?
2. **Fix at the source** — update docs/prompts, or fix the server interface
3. **Verify** — ensure fresh agent sessions call the tool correctly without workarounds
4. **Delete the shim** — remove any temporary aliases or rewrites
5. **Add a lint rule** — prevent new code from reintroducing the anti-pattern

See [task-40390848](https://github.com/nicsuzor/aops/issues/search?q=task-40390848) for the full case study and lint rule (`check_no_pkb_path_aliases.py`).
