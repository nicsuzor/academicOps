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

Just re-run the init script - it overwrites dprint.json:

```bash
$ACADEMICOPS/scripts/init_project_standards.sh /home/nic/src/buttermilk
$ACADEMICOPS/scripts/init_project_standards.sh /home/nic/src/zotmcp
# ... etc
```

## Pre-commit Configuration

Standard pre-commit setup includes:

- **File hygiene** (trailing whitespace, EOF, line endings)
- **Syntax checks** (YAML, JSON, TOML)
- **shellcheck** - Shell script linting
- **eslint** - JavaScript/TypeScript linting
- **ruff** - Python linting + formatting
- **dprint** - Fast formatting (markdown, JSON, TOML, YAML, TS/JS, CSS, etc.)
- **academicOps hooks** (no-config-defaults, instruction-bloat)

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
2. Re-run `init_project_standards.sh` on each repo (it overwrites)
3. Commit the changes in each affected repo

The init script is idempotent - safe to run repeatedly.
