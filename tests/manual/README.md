# Manual Tests

This directory contains manual test scripts that are too complex or environment-specific for automated unit testing.

## test_remote_automation.sh

Tests that the framework can bootstrap itself in remote automation environments (CI, GitHub Actions, Claude Code Web, remote VMs) where:

- `$AOPS` is not pre-configured
- Only `$CLAUDE_PROJECT_DIR` is available
- No user-level setup (`~/.claude/`) exists

### What it tests:

1. **Session environment setup** - `session_env_setup.sh` derives `$AOPS` from `$CLAUDE_PROJECT_DIR`
2. **Settings configuration** - `settings-self.json` uses `$CLAUDE_PROJECT_DIR` instead of `$AOPS`
3. **Symlink correctness** - `.claude/settings.json` links to `settings-self.json`
4. **Sync script** - `sync_web_bundle.py --self` correctly uses `settings-self.json`
5. **Session persistence** - Environment variables are written to `$CLAUDE_ENV_FILE`

### Usage:

```bash
cd /path/to/academicOps
bash tests/manual/test_remote_automation.sh
```

### Expected output:

All 5 tests should pass with ✅ PASS messages. The script simulates a clean environment by unsetting `$AOPS` and setting only `$CLAUDE_PROJECT_DIR`.

### When to run:

- After modifying `session_env_setup.sh`
- After changes to `settings-self.json`
- After changes to `sync_web_bundle.py --self` logic
- Before deploying to CI/remote environments
- When troubleshooting remote automation issues

## Adding new manual tests

Manual tests should be added when:

1. The test requires specific environment simulation that's hard to mock
2. The test involves multiple system components (hooks, settings, scripts)
3. The test validates end-to-end workflows
4. The test requires manual verification of outputs

Keep manual tests focused, well-documented, and with clear pass/fail criteria.
