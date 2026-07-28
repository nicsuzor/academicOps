# Agentic E2E Certification — All-Surfaces Smoke Matrix + Container Deep-Dive

Verify the aops plugins actually WORK — hooks, MCP, skills, subagent tool binding — on
every surface they ship to. **Judgment is non-delegable**: you (the driving agent) read
the evidence and issue verdicts; a script's exit code or a single string match never
substitutes. The old two-track protocol's forensics mechanics live on in
[[09-session-hook-forensics]] and [[11-self-test]].

**Quiescence rule (applies everywhere):** never evaluate a loading screen. If the pane
shows a spinner or `Working...`, sleep and re-capture until the final response and a
clean prompt are visible. Passing a test without observing its final state is a failure
of your judgment, not a pass.

A **persistently blank pane — no spinner, no text at all** — is a different failure
signature from a busy spinner, not just a slower version of the same thing: it can mean
an unrendered confirmation dialog (a trust prompt, an onboarding wizard) is sitting there
waiting for input nobody sent, which looks identical to a dead hang from the process
state alone (alive, idle, zero CPU). Before concluding the worker is truly stuck, check
for exactly this — sending one blind `Enter` is a cheap, non-destructive way to find out
(`aops_cbeb71dc`: this is exactly what an unattended agy dispatch hit).

**Computed ≠ Delivered ≠ Seen:** a hooks-JSONL record proves a gate _computed_ output;
`exit_code: 0` plus the client wire payload proves it was _delivered_; only the rendered
transcript/pane proves the agent or user _saw_ it. State which layer each piece of
evidence proves. Full treatment: [[09-session-hook-forensics]].

## 1. The surface matrix

Seven surfaces receive the same plugins through five different channels, and the same
backend tools appear under **different prefixes per surface**. A wrong-prefix call fails
with `No such tool available` — that is a _binding_ finding, not a server-health finding;
never confuse the two.

| # | Surface                              | Install channel                                                                                              | Expected services-MCP tool prefix                                                                                        |
| - | ------------------------------------ | ------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------ |
| 1 | Claude Code CLI (terminal)           | `make install-cowork` → `dist/cowork` directory marketplace, user scope                                      | `mcp__plugin_aops_services__*`; plus `mcp__services__*` while the canonical user-level server exists in `~/.claude.json` |
| 2 | Claude Code GUI (desktop app)        | same user-scope install — but GUI env ≠ shell env (PATH!)                                                    | same as #1                                                                                                               |
| 3 | Cowork, on-computer                  | desktop app mirrors user scope on restart                                                                    | `mcp__plugin_aops_services__*`                                                                                           |
| 4 | Cowork, cloud + desktop connected    | desktop syncs local installs into the session (no zip upload needed)                                         | `mcp__remote-devices__plugin_aops_services__*`                                                                           |
| 5 | Cloud Claude Code (claude.ai/code)   | the project's committed setup (`.claude/setup.sh` / settings) — plugin names must match the current ship set | `mcp__plugin_aops_services__*`                                                                                           |
| 6 | Polecat container, `--client claude` | `polecat run`/`polecat crew` + `entrypoint.sh` + `aops-jr/polecat/defaults/claude-settings.json`             | `mcp__plugin_aops_services__*`                                                                                           |
| 7 | Polecat container, `--client agy`    | same dispatch, agy client                                                                                    | agy namespace; NO `agy plugin list` — check `~/.gemini/antigravity-cli/plugins/` structurally                            |

Surfaces 1–5 are quick probes (§2). Surfaces 6–7 add the container deep-dive (§3) —
run both clients with the same prompt so results are comparable; asymmetric breakage is
itself a finding.

## 2. Per-surface probe (run on EVERY surface)

Five checks, in order. Each verdict needs its receipt (command + output, pane capture,
or `file:line`).

1. **Plugins present.** `claude plugin list` (CLI/GUI/cloud-CC/polecat-claude), the
   Customize pane (Cowork), or the session's plugin list (cloud Cowork). Expect exactly
   the intended set for that surface; on polecat, also positively confirm `aops-cowork`
   and `aops-ts` are **absent**.
2. **Hooks fire.** Start a session; expect the SessionStart banner ("aOps plugin
   loaded") and the UserPromptSubmit hydration reminder on your first prompt. Absent
   hooks on GUI-launched surfaces but present in terminal = the PATH class of failure
   (hook commands must bootstrap via `ensure-path.sh`).
3. **MCP alive.** Ask the session to call the surface's expected-prefix `pkb__status`
   tool. Expect the mem binary version + git hash. Record both the prefix that worked
   and the version returned — version skew across surfaces is a finding.
4. **Subagent binding.** Delegate the same status call to a subagent (`pauli` or
   `ida`). This is the check that catches allowlist/namespace mismatches: the agent
   frontmatter must carry a wildcard matching THIS surface's prefix. A subagent
   reporting `No such tool available` for every variant = binding gap, file it.
5. **Negative check.** Confirm the _wrong_ prefix fails (e.g. `mcp__services__*` on a
   surface with no user-level server). If a supposedly absent name resolves, a
   duplicate registration exists — that's the double-loading class of defect.

**Known failure modes to check before filing anything new** (each has a receipt in the
PKB): unset `pkb_mcp_url` userConfig silently overriding shell env (`mem-8108ff8c`);
github-source marketplaces nuked by Cowork restarts (install from a directory
marketplace); agent allowlist wildcards not matching the surface's prefix
(`mem_5b124540`); YAML frontmatter escapes rejected by the claude.ai upload validator;
stale plugin names in cloud setup scripts.

## 3. Container deep-dive (surfaces 6–7)

Run when polecat infra, gate definitions, the plugin allowlist, or `entrypoint.sh`
changed — or as a periodic audit. Reuse the boot sequence and plugin pre-check from
[[11-self-test#2-polecat-session-validation]]; forensics mechanics from
[[09-session-hook-forensics]]. Dispatch with the real `polecat run`/`polecat crew` CLI —
never a hand-rolled tmux session, which bypasses the container, `polecat.yaml`, and
credential scoping.

State these axes up front, then judge each with evidence (pass / fail / inconclusive):

1. **Hooks** fire for the events that occurred (Computed layer), delivered cleanly
   (`exit_code: 0`, no stderr), and expected user-facing text actually appears in the
   pane (Seen layer).
2. **Responses** are appropriate to the prompt and any gate constraint — the agent
   waits/complies rather than routing around a block. Test the full block-and-satisfy
   flow: trigger the gate, satisfy it, verify the original task resumes.
3. **Execution** — at least one real tool/shell call returns genuine success inside the
   container. "Blocked by a gate as designed" is a different axis, not a failure here.
4. **Gates** — triggers in `aops/lib/gates/definitions.py` match the tools actually
   invoked and produce the right `GateTransition` at the right turn; runtime gate modes
   match `PolecatConfig.for_mode(...)` for the dispatch mode. A `block` gate that never
   visibly blocks anything is **inconclusive**, not a pass.
5. **Plugins** — exactly the allowlisted set (diff against
   `aops-jr/polecat/defaults/claude-settings.json` `enabledPlugins`), with positive-absence
   checks for everything else.
6. **Credentials** — bot identity only: `git config user.name/email`,
   `env | grep -i 'GIT_\|GH_\|GITHUB_'`, `SSH_AUTH_SOCK` unset, HTTPS-forced
   `insteadOf` active, no personal tokens reachable. If the observed identity doesn't
   match the requirement, HALT and file a PKB task — do not silently pass and do not
   patch `entrypoint.sh` inline during a verification run.

## 4. Closing pipeline

1. **Render the transcript yourself** (`python3 aops/scripts/transcript.py <session>.jsonl
   -o e2e-<timestamp>`) before delegating — pin the artifact; never let a reviewer
   go hunting for "a session matching this description" (stale same-named sessions
   linger and keep refreshing mtimes).
2. **marsha** extracts verbatim proof from the RAW logs (hook exit codes, context
   injections reaching the prompt, per-axis evidence for containers), scoped to exactly
   the artifacts you hand her.
3. **rbg** rules on the pinned abridged transcript + marsha's evidence: data boundaries,
   honest epistemics, halt-on-failure. If a ruling cites an artifact you didn't hand it,
   the ruling is invalid — re-pin and re-invoke.
4. **Certification report** back to the user: the §1 matrix as a verdict table (surface ×
   five probes × verdict × receipt), container axes if run, and every failure filed as
   one PKB task per root cause (not per symptom). Clean up: `/exit`,
   `tmux kill-session`, `polecat nuke`.
