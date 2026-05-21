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

Separate from the in-session self-test above. Run when you need to prove that a fresh `polecat crew` (Claude or Gemini) actually launches with our infrastructure attached — typically after a change to `polecat/defaults/*-settings.json`, the entrypoint, plugin packaging, or a Claude Code / Gemini CLI upgrade.

**Mechanics:** drive an interactive crew under `tmux` per [[tests/harness/README.md]] — that file owns the tmux pattern, alias-resolution gotcha, and capture-pane recipe. Do not re-derive it.

**Before you blame the code: is the image fresh?** If you see something that looks like a regression on a recently-merged fix, check whether the container image actually contains that fix before filing a regression:

```
docker images aops-crew --format "{{.CreatedAt}}"           # image build time
git log -1 --format=%ci <commit-or-PR>                       # fix merge time
# AND diff the staged settings against current main:
docker run --rm --entrypoint cat aops-crew /home/worker/.claude/settings.json | diff - polecat/defaults/claude-settings.json
```

If the image predates the fix, or the staged file diverges from main, it's a stale image — rebuild (`make build-docker` or equivalent), don't file a regression. PRs that touch `Dockerfile`, `polecat/entrypoint.sh`, or anything baked into the image at build time CANNOT be picked up by a remount.

**What to verify (signals, not steps):**

- **Plugin loaded** — Claude footer should show our plugin enabled, not just "Anthropic marketplace installed". Gemini equivalent: aops extension listed in startup banner.
- **No folder-trust dialog** at Claude startup. If it appears, plugin loading is blocked → regression on [[aops-542d82d4]] / PR #1198.
- **Default mode sane** — Claude should NOT come up in plan mode by default in a polecat crew session. If it does, settings template isn't being applied.
- **SessionStart hook fired** — look for the aops-core SessionStart banner / hydration gate message in the pane, AND for a populated hooks JSONL at `~/.claude/projects/-workspace/<session>-session-hooks.jsonl` (Claude) or the Gemini-side equivalent under `$AOPS_SESSIONS`. Empty/missing JSONL = router not on the call path.
- **Skills available** — invoke a known skill (`/aops-core:aops`, `/plan`) and confirm it actually loads. "Skill not found" or silent no-op = plugin not enabled functionally even if files exist.
- **Subagent dispatch** — `Agent(subagent_type='aops-core:junior')` should succeed. File presence ≠ functional dispatch (see lessons in [[aops-7c45802b]]).
- **Gate env vars forwarded** — `docker exec <ctr> env | grep -E 'AOPS_|HYDRATION_|PKB_'`. Known-broken on the `polecat run` (task worker) path; works on `crew`. Don't assume parity.

**Reference run:** [[aops-7c45802b]] is the most recent end-to-end attempt, with the lessons about why file presence is not evidence of functional loading. Read it before starting — don't repeat the discovery.

**On failure:** record findings against the relevant PR/regression task (e.g. append to [[aops-542d82d4]] for folder-trust issues) rather than opening a new task per symptom. Multiple symptoms from one root cause belong on one node.

**Cleanup:** always `/exit` the tmux session before `kill-session` — `kill-session` SIGKILLs the docker client and skips artifact rescue. Then `docker stop` any orphaned `polecat-<crew>-*` containers and `polecat nuke <crew>` to clear the worktree.
