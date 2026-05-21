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

### Methodology

The job is to discriminate **"infrastructure files are present"** from **"infrastructure actually fires on first use."** Most regressions live in that gap. Run both clients (Claude and Gemini) — they share components but install them via different paths, so asymmetric breakage is common.

For each client (Claude default, `-g` for Gemini), walk these layers in order. Stop and capture evidence at the first failing layer — later layers depend on earlier ones.

#### 0. Image freshness

`docker images aops-crew --format '{{.CreatedAt}}'` vs the timestamp of the last commit touching `Dockerfile`, `polecat/defaults/*`, the entrypoint, or anything bundled into the plugin. If older → `make build-docker` first. Skipping this is how a stale image gets blamed on a code regression.

#### 1. Container starts and surfaces the right boot signals

Spin via tmux (mechanics in `tests/harness/README.md`). Wait for the CLI to render, then `capture-pane -p -S -2000`. Look for **what would be missing if a layer were broken**, not just for the happy-path banner. Examples:

- aops-core SessionStart / router banner present → router hook wired.
- Plan mode active (`polecat crew` passes `--permission-mode=plan`).
- No folder-trust dialog, no onboarding prompt, no auth-pending screen.

Absence of any of these is a signal — note which boot signal is missing before sending any prompt.

Do NOT use footer text ("plugin enabled" vs. "marketplace installed") as a boot signal. Upstream CLIs change footer copy without semantic meaning, and the string doesn't reliably distinguish "discovered" from "loaded" anyway. Plugin-loaded is proven functionally at §4 (skill + subagent execute) and §5 (PKB MCP tool actually answers), not visually at boot.

#### 2. First UserPromptSubmit actually runs

Boot signals can pass while hooks are wedged. Send one trivial prompt and capture the pane. The discriminator is: does the agent respond, or does the CLI print `● UserPromptSubmit operation blocked by hook: ...`? An inline hook-blocked message is the loudest possible regression signal — it means the hook fired (good) and errored (bad). Treat the error text as primary evidence; do not paraphrase.

#### 3. Container-environment sanity (only relevant if §2 failed, or to pre-empt)

Hook failures are usually one of: missing pre-built artifact, UID mismatch, or filesystem ownership. Cheap to check:

- `docker exec <ctr> id` — does the UID resolve to a name? If not, the container is running as the host UID and any image-owned directory is potentially un-writable.
- For each hook entry point, does its expected fast-path artifact actually exist? (e.g. a router that prefers a pre-built `.venv` should find one; if it falls back, the fallback path must also work for the non-image UID.) Compare Claude's plugin install path against Gemini's extension install path — asymmetric pre-installs are a recurring class of bug.
- Plugin install location vs. expected location — Claude installs from marketplace into a cache dir, Gemini ships components in the image. They diverge.

#### 4. Skill + subagent exercise (only meaningful once §2 passes)

Send one prompt that invokes a skill (`/aops-core:aops`) and one that dispatches a subagent (`Agent(subagent_type='aops-core:junior')`). "Silently no-op" is a failure mode — verify both produced visible output, not just that the prompt returned.

#### 5. Observability — hooks logged, MCP reachable

- **Hook JSONL** at `~/.claude/projects/-workspace/*-session-hooks.jsonl` inside the container. Populated = hooks fully wired, empty = router not on the call path, missing = hook log path env var misconfigured. An empty file after §4 means hooks failed silently rather than blocked loudly.
- **PKB MCP connectivity:** `docker exec <ctr> sh -c 'echo "$PKB_MCP_URL" && curl -sS -o /dev/null -w "%{http_code}\n" "$PKB_MCP_URL"'`. 406 is fine (MCP rejects GET); connection refused / timeout / empty URL is not.
- **PKB MCP functional:** confirm via §4's `/aops-core:aops` that an `mcp__plugin_aops-core_pkb__*` tool actually answered. "Tool not found" or "connection refused" here = PKB plugin not wired even though the Claude/Gemini plugin loaded.

#### 6. Cleanup

`/exit` → `tmux kill-session` → `polecat nuke <crew>`. **`kill-session` without `/exit` SIGKILLs the docker client and skips artifact rescue.** Repeat for the other client.

### On failure

File one issue per **root cause**, not per symptom. UID-mismatch + missing venv + permission denied are one bug; banner-missing + hook-blocked + empty JSONL are usually the same bug. The hook-blocked error text usually points straight at the broken layer — quote it verbatim in the issue and identify which layer (§1–§5) it belongs to.

Append evidence to the existing PR / regression task when one already exists (e.g. [[aops-542d82d4]] for folder-trust) rather than opening a new task per symptom — multiple symptoms from one root cause belong on one node.

### Reference runs

- [[aops-7c45802b]] — file presence is not evidence of functional loading.
- GH #1237 — Claude plugin cache had no pre-built `.venv`, fast path missed, uv fallback hit EACCES under host UID. Caught at §2 (first UserPromptSubmit). Would have been invisible at §1 because boot signals were green.
