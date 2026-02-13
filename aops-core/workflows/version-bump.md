---
id: version-bump
category: operations
bases: []
---

# Version Bump Workflow

Bumps the academicOps version, builds distributions, pushes to github, and installs from the official distribution package.

## Routing Signals

- "bump version", "release", "update packages"
- Releasing a new version of academicOps
- After completing features ready for release

## NOT This Workflow

- Local development testing (use git worktrees or direct source)
- Hotfixes that skip the build/test cycle

## Phases

### Phase 1: Bump Version

1. Run: `uv run python scripts/bump_version.py`
2. Observe output showing old → new version

**Note**: Script only bumps patch version (e.g., 0.1.5 → 0.1.6). For major/minor bumps, edit `pyproject.toml` manually.

**Gate**: Script outputs "Bumped version from X to Y"

### Phase 2: Build Distributions

1. Run: `uv run python scripts/build.py`
2. Wait for completion (creates dist/aops-gemini, dist/aops-claude, dist/aops-antigravity)

**Gate**: All three dist directories exist and contain updated manifests

### Phase 3: Verify Versions Match

Check version consistency across:

- `pyproject.toml` (source of truth)
- `dist/aops-gemini/gemini-extension.json`
- `dist/aops-claude/plugin.json`

**Gate**: All three show identical version numbers

### Phase 4: Commit and Push

1. Commit all changes: `git add -A && git commit -m "chore: bump version to X.Y.Z"`
2. Push to trigger distribution: `git push origin main`

**Gate**: Push succeeds

### Phase 5: Wait for GitHub Actions

1. Check action status: `gh run list --limit 1`
2. Wait for completion: `gh run watch` (or poll until status is "completed")
3. Verify success: `gh run view --log` if needed

**Gate**: GitHub Actions workflow completes successfully

### Phase 6: Install from Distribution

**Claude Code:**

```bash
command claude plugin marketplace update aops && command claude plugin install aops-core@aops
```

**Gemini CLI:**

```bash
command gemini extensions uninstall aops-core && command gemini extensions install git@github.com:nicsuzor/aops-dist.git --consent --auto-update --pre-release
```

**Note**: Gemini requires uninstall before reinstall. Claude's install command handles updates automatically.

**Gate**: Both commands succeed without error

### Phase 7: Verify Installation

Check version information with:

- Claude code: `command claude plugin list`
- Gemini extension: `command gemini extensions list`

**Gate**: Both CLIs show correct new version

### Phase 8: Post-Release QA

Run the smoke test to verify the installed distribution works correctly.

1. Run Claude test:
   ```bash
   command claude --permission-mode bypassPermissions --output-format json --print "What time is it?"
   ```

2. Run Gemini test:
   ```bash
   command gemini --approval-mode yolo --output-format stream-json --p "What time is it?"
   ```

3. Generate transcripts:
   ```bash
   uv run python $AOPS/aops-core/scripts/transcript.py --recent
   ```

4. Find and review transcripts:
   ```bash
   fd --newer 10m -e md . ~/writing/sessions/
   ```

5. Assess each transcript for framework markers and correct behavior

**Gate**: Both clients answer correctly without excessive friction. Log any regressions as P1 bugs.

See [[manual-qa]] for detailed transcript analysis instructions.

## Verification Checklist

- [ ] Version bumped in pyproject.toml
- [ ] dist/aops-gemini built with matching version
- [ ] dist/aops-claude built with matching version
- [ ] Changes committed and pushed
- [ ] GitHub Actions completed successfully
- [ ] Claude plugin updated from distribution
- [ ] Gemini extension updated from distribution
- [ ] Both CLIs functional with new version
- [ ] Post-release QA passed (Phase 8) - transcripts reviewed, no regressions
