# Cross-Repo Hook Distribution

academicOps provides shared pre-commit hooks that can be used across all your repos.

## Quick Setup for New Repos

**1. Install dprint globally (one-time):**

```bash
npm i -g dprint
```

**2. Copy dprint config to your repo:**

```bash
cp $ACADEMICOPS/templates/dprint.json .
```

**3. Create `.pre-commit-config.yaml`:**

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
        exclude: |
          (?x)^(
            \.vscode/.*\.json|
            \.claude/.*\.json|
            .*\.ipynb
          )$
      - id: check-toml
      - id: mixed-line-ending
        args: ["--fix=lf"]

  # Python (if applicable)
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.4
    hooks:
      - id: ruff
        args: [--fix, --unsafe-fixes, --exit-non-zero-on-fix]
      - id: ruff-format

  # academicOps framework hooks
  - repo: https://github.com/nicsuzor/academicOps
    rev: main
    hooks:
      - id: dprint
      - id: no-config-defaults # Python only
      - id: check-instruction-bloat # If using academicOps patterns
```

**4. Install and test:**

```bash
pre-commit install
pre-commit run --all-files
```

## Available Hooks

### `dprint`

Fast Rust-based formatter for markdown, JSON, TOML, and YAML.

- **Requires:** `dprint` installed globally, `dprint.json` in repo root
- **Formats:** `.md`, `.json`, `.toml`, `.yaml`
- **Speed:** 10-100x faster than prettier

### `no-config-defaults`

Enforces fail-fast philosophy: no `.get()` with defaults in config code.

- **Language:** Python
- **Pattern:** Detects `config.get('key', default)`
- **Enforcement:** Blocks commits with config defaults
- **See:** [Issue #100](https://github.com/nicsuzor/academicOps/issues/100)

### `check-instruction-bloat`

Prevents agent instruction files from growing beyond maintainability thresholds.

- **Language:** Markdown
- **Thresholds:** >25 lines OR >20% growth
- **Philosophy:** Use scripts/hooks/config instead of instructions
- **See:** [Issue #116](https://github.com/nicsuzor/academicOps/issues/116)

## Special Case: Parent Repo with academicOps Submodule

The `writing` repo contains academicOps as a submodule at `aops/`, so it uses `repo: local` instead:

```yaml
# Custom project-specific hooks (from academicOps submodule)
- repo: local
  hooks:
    - id: dprint
      entry: dprint fmt --config dprint.json
      language: system
      # ... rest of config
    - id: no-config-defaults
      entry: python aops/scripts/check_config_defaults.py
      language: system
      # ... rest of config
```

## Updating Hooks

**For hook users:**

Update the `rev:` in your `.pre-commit-config.yaml`:

```yaml
- repo: https://github.com/nicsuzor/academicOps
  rev: main # or specific tag like v1.0.0
```

Then run:

```bash
pre-commit autoupdate
pre-commit run --all-files
```

**For hook developers:**

Modify `.pre-commit-hooks.yaml` in academicOps, commit, and push. Users get updates on next `pre-commit autoupdate`.

## Customizing dprint Config

Edit `dprint.json` to customize formatting:

```json
{
  "markdown": {
    "lineWidth": 120,
    "textWrap": "never" // or "always" to wrap prose
  },
  "json": {
    "indentWidth": 2
  }
}
```

Full config docs: https://dprint.dev/plugins/

## Troubleshooting

**Hook fails with "dprint: command not found":**

```bash
npm i -g dprint
```

**Hook runs but finds no files:**

Check `dprint.json` excludes don't match your files.

**Want to skip a hook temporarily:**

```bash
SKIP=dprint git commit -m "message"
```

**Disable hooks entirely:**

```bash
pre-commit uninstall
```
