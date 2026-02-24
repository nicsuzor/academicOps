#!/usr/bin/env bash
# Format all code before committing
# Run this before staging files to avoid pre-commit failures

set -e

echo "=== Formatting Python with ruff ==="
uv run ruff format .
uv run ruff check --fix . || true

echo ""
echo "=== Formatting Markdown/JSON/TOML with dprint ==="
uv run dprint fmt

echo ""
echo "=== Done ==="
