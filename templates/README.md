# academicOps Templates

Reusable configuration files for repos using the academicOps framework.

## dprint.json

Fast Rust-based code formatter configuration for markdown, JSON, TOML, and YAML files.

**Setup:**

```bash
# Install dprint globally
npm i -g dprint

# Copy config to your repo root
cp $ACADEMICOPS/templates/dprint.json .

# Test
dprint check
dprint fmt
```

**Updating config across all repos:**

```bash
# Preview what would change
$ACADEMICOPS/scripts/sync_dprint_config.sh --dry-run

# Apply updates to all known repos
$ACADEMICOPS/scripts/sync_dprint_config.sh
```

## Using academicOps Pre-commit Hooks

Other repos can reference academicOps hooks instead of duplicating configuration.

**Example `.pre-commit-config.yaml`:**

```yaml
repos:
  # Standard file hygiene
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v6.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-toml

  # Python formatting
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.4
    hooks:
      - id: ruff
        args: [--fix, --unsafe-fixes, --exit-non-zero-on-fix]
      - id: ruff-format

  # academicOps framework hooks
  - repo: https://github.com/nicsuzor/academicOps
    rev: main # or specific tag
    hooks:
      - id: dprint
      - id: no-config-defaults
      - id: check-instruction-bloat
```

**Required:**

- `dprint` installed globally: `npm i -g dprint`
- `dprint.json` in repo root (copy from templates/)

**Note:** The parent `writing` repo uses `repo: local` since academicOps is a submodule there. Other standalone repos reference via GitHub URL.

## Maintenance

**When you update dprint.json:**

1. Edit `$ACADEMICOPS/templates/dprint.json`
2. Run `$ACADEMICOPS/scripts/sync_dprint_config.sh` to push to all repos
3. Commit the changes in each affected repo

This keeps all repos synchronized with a single source of truth.
