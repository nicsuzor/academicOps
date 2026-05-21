# Self-Test Workflow

1. Hook Gates Verification
   Testing the four layers of session infrastructure:

- SessionStart: Verify that principles are loaded and the session env file is correctly written.
- MCP & PKB Integration: Test semantic search and verify that task metadata (like goals: []) and state transitions are properly indexed and that the remote Rust server is accessible and responsive.
- PreToolUse: Validate the blocking gates: write operation should be prohibited by hydration gate.
- PKB write: verify that you can create a task for this self-test session and that claiming it is sufficient to open the previously blocked gates.
- RBG enforcer: ensure you can invoke the RBG periodic compliance enforcer with the instructions given
- Skills: Invoke core framework skills like /plan, /aops, and /remember to verify they load and execute.
- Subagents: Dispatch subagents (e.g., junior or marsha) to ensure inter-agent coordination and context passing work without dropping threads.
- Polecats: verify that you can dispatch remote polecat workers (both gemini and claude) over SSH on the correct host.
- Stop Gates: Verify stop is prevented before handover
- Handover: verify that /dump (handover) command provides useful instructions and that you are able to execute them all.
- Open stop gates (Important!): verify that you are not prevented from stopping after invoking the handover as directed.

IMPORTANT: All of the information required to undertake these tasks should be provided in your context at startup, within hooks, and in the files you are referred to. If you find you do not have sufficient information to know how to complete a task, HALT, and report the FAILURE to provide adequate instruction. Do NOT go looking or guessing for information that should be provided in advance.

---

## 2. Polecat session validation (hooks / plugins / skills)

Separate from the in-session self-test above. Run when you need to prove that a fresh `polecat crew` (Claude or Gemini) actually launches with our infrastructure attached — typically after a change to `polecat/defaults/*-settings.json`, the entrypoint, plugin packaging, or a Claude Code / Gemini CLI upgrade. Mechanics (tmux pattern, alias-resolution, `capture-pane`) live in [[tests/harness/README.md]] — don't re-derive.

### The recipe

1. **Image fresh?** `docker images aops-crew --format '{{.CreatedAt}}'` vs `git log -1 --format=%ci <last polecat/defaults or Dockerfile commit>`. If older → rebuild first. Skipping this step is how you misattribute a stale image to a regression.

2. **Spin Claude crew via tmux** (mechanics in `tests/harness/README.md`). Wait ~30s, `capture-pane`.

3. **Opening pane must show**:
   - aops-core SessionStart banner (router fired)
   - Plugin enabled in footer (not just "Anthropic marketplace installed")
   - No folder-trust dialog
   - Not defaulted to plan mode

4. **Then exercise it** — send one prompt that invokes a skill (`/aops-core:aops`) and one that dispatches a subagent (`Agent(subagent_type='aops-core:junior')`). Both must actually run, not silently no-op.

5. **Check the hook JSONL** at `~/.claude/projects/-workspace/*-session-hooks.jsonl` inside the container — populated = hooks fully wired, empty = router not on call path.

6. **PKB MCP reachable from inside the container.** Two layers:
   - **Connectivity:** `docker exec <ctr> sh -c 'echo "$PKB_MCP_URL" && curl -sS -o /dev/null -w "%{http_code}\n" "$PKB_MCP_URL"'` — env var set, endpoint answers.
   - **Functional:** send the agent a prompt that calls a PKB tool (`mcp__plugin_aops-core_pkb__search` for any term, or `/aops-core:aops` which loads the `aops-state` document). A "tool not found" or "connection refused" here = PKB plugin not wired, even if the Claude Code plugin loaded fine.

7. **Repeat for Gemini** (`-g`).

8. **Cleanup**: `/exit` → `tmux kill-session` → `docker stop` → `polecat nuke <crew>`. `kill-session` without `/exit` SIGKILLs the docker client and skips artifact rescue.

### On failure

Append evidence to the existing PR / regression task (e.g. [[aops-542d82d4]] for folder-trust) rather than opening a new task per symptom — multiple symptoms from one root cause belong on one node.

**Reference run:** [[aops-7c45802b]] is the most recent end-to-end attempt, with the lessons about why file presence is not evidence of functional loading.
