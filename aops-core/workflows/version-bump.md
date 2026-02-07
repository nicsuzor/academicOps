---
id: version-bump
category: operations
bases: []
---

# Version Bump Workflow

Bumps the academicOps version, builds distributions, and installs locally for both Gemini CLI and Claude Code.

## Routing Signals

- "bump version", "release", "update packages"
- Releasing a new version of academicOps
- After completing features that need local testing

## NOT This Workflow

- Publishing to marketplace (requires git push + separate release process)
- Hotfixes that need immediate deployment

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

### Phase 4: Install Locally

**Gemini CLI** (from academicOps root):
```bash
gemini extensions uninstall aops-core
gemini extensions link ./dist/aops-gemini --consent
```

**Claude Code:**
```bash
claude plugin update aops-core@aops
```

**Gate**: Both commands succeed without error

### Phase 5: Verify Installation

- Gemini: Run `/diag` in new session, check version
- Claude: Start new session, verify plugin loads with correct version

## Verification Checklist

- [ ] Version bumped in pyproject.toml
- [ ] dist/aops-gemini built with matching version
- [ ] dist/aops-claude built with matching version
- [ ] Gemini extension linked locally
- [ ] Claude plugin updated locally
- [ ] Both CLIs functional with new version
