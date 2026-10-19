# Diagnostic gotchas

| Symptom | Cause | Fix |
| - | - | - |
| `no server running on /tmp/tmux-...` | Inline tmux command failed in `/bin/sh -c` on quoting or missing PATH exports | Use the `/tmp/launch-$TMUX_NAME.sh` wrapper |
| Session log directory named after the prompt string | `-p` passed after `run` without `--`; Click parsed it as `--project` | Put `--` before agent flags and prompts |
| `agy` stuck at a Google OAuth prompt | `GEMINI_CONFIG_DIR` missing or lacks `antigravity-oauth-token` | Set `GEMINI_CONFIG_DIR=~/.gemini` and ensure the token exists |
| `agy` auth fails in earlier/later runs but a fresh one-shot startup succeeds | Token refresh write-back fails when `antigravity-oauth-token` symlinks to a read-only creds mount | Inspect prior failing session logs for `Failed to save refreshed token: … read-only file system` and check token mount writability |
| `docker logs <container>` empty for `agy` | `agy` redirects to internal log files | Read `$AOPS_SESSIONS/.../agy-cli.log` |
| `fatal: not a git repository` in the container | `-d` was given a linked git worktree, whose `.git` file points outside the mount | Use a full clone for `-d`, or register a project mapping in `$POLECAT_HOME/local.yaml` and pass `-p <project>` |
| Premature `agy` boot-failure report | Pane captured during the 2–3 s `⚠ Verifying your account...` race | Wait for the header plan name before inspecting |
| `⚠ Agent execution terminated due to error` + an error ID, nothing else | agy agent frontmatter names a tool absent from its registry | `grep "not found in registry" <session>/agy-cli.log`; drop the offending names from `build/tool_map.toml`'s `accepted_tools` |
| Headless `agy` returns `"error":"context canceled"` with work half-done | Job outran `--print-timeout` (default `5m0s`) | Compare `duration_seconds` against the timeout; re-run with an explicit `--print-timeout` |
| `delivery_guard_failed` after a probe that wrote files | The probe's own artefacts are uncommitted in the workspace | Expected for a write probe; confirm the named files are the probe's before treating it as a defect |
