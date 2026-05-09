# crew_harness — agent-driven polecat crew probe

Minimal tmux harness. The user directs an agent to "go check whether `polecat
crew` is broken"; the agent uses this to spawn a real interactive session,
type at it, read the pane, and collect artifacts. The agent then judges the
result. No scenarios, no analyzer, no soak gates — that's by design.

## Usage from an agent

```bash
H=tests/harness/crew_harness.py

# Start a session — prints TMUX=, SINCE=, MARKER=
eval "$(uv run python $H start)"

# Drive it
uv run python $H send "$TMUX" 'who are you?' --wait 8
uv run python $H pane "$TMUX"

# Tear down + collect artifacts under tests/harness/artifacts/<name>/
uv run python $H end "$TMUX" "$SINCE" --marker "$MARKER" --out tests/harness/artifacts/probe1
```

`end` exits non-zero only if **no artifacts** landed under
`$AOPS_SESSIONS/{hooks,summaries,transcripts}` since `start`. Everything else
— "did SessionEnd fire", "does the response look right" — is for the calling
agent to read off the pane and the bundled files and judge.

## Backends and flags

- `-g` — gemini backend (default is claude).
- `--hooks` — turn on hooks (default crew runs with `hooks_enabled: false`, so
  no SessionEnd, no observability artifacts).
- `keys <tmux> <key>...` — send raw tmux key names (e.g. `Down Down Enter`)
  for navigating menus like the gemini "trust folders" prompt.

## What `end` collects

1. `pane.log` — the pane buffer at teardown.
2. `hooks/`, `summaries/`, `transcripts/` — anything in `$AOPS_SESSIONS` newer
   than the `MARKER` from `start`.
3. `container/<docker_name>/` — `docker cp` of `/home/worker/.gemini/tmp/`
   and `/home/worker/.claude/` out of every live `aops-crew` container, taken
   _before_ tmux is killed. Defends against wedged sessions whose hooks log
   only exists inside the container (see #939).

## Why no scenarios / analyzer / promotion gates

This is a harness, not a test suite. See issue #937 for the full thread.

## Known findings the harness has surfaced

- **#938** — `polecat crew` (claude) boots unauthenticated; the headless
  `.claude.json` template lacks `oauthAccount`/`hasCompletedOnboarding`, so
  workers re-run onboarding instead of picking up the staged `.credentials.json`.
- **#939** — Gemini crew hooks/transcripts only sync on clean polecat exit;
  wedged sessions lose observability unless extracted from the container.
