#!/bin/bash
# AcademicOps Formatting Pipeline
# This script runs the full formatting and linting pipeline used by the project.
# It matches the tools and configurations defined in .pre-commit-config.yaml.

set -euo pipefail

# Ensure we are in the repo root
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

# Bootstrap PATH if possible
[[ -f "aops-core/scripts/ensure-path.sh" ]] && source "aops-core/scripts/ensure-path.sh"

echo "--- 🎨 Formatting with dprint (Markdown/JSON/TOML) ---"
uv run dprint fmt --allow-no-files

echo "--- 🐍 Formatting with ruff ---"
# ruff format formats files in-place
uv run ruff format .

echo "--- 🔍 Linting with ruff (auto-fix) ---"
# ruff check --fix auto-fixes what it can
uv run ruff check --fix .

echo "--- 🏛️  Checking framework integrity ---"
# This mirrors the check-framework-integrity hook
uv run python scripts/check_framework_integrity.py

echo "--- ✓ Formatting complete ---"
