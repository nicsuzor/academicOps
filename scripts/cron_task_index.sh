#!/bin/bash
# Cron wrapper: regenerate task index
#
# Scans $ACA_DATA for task files and rebuilds index.json and INDEX.md.
# Called by cron every 5 minutes.
#
# Exit codes:
#   0 - Success
#   1 - Error (missing dependencies, script failure)

set -euo pipefail

# Ensure PATH includes uv (cron runs with minimal PATH)
export PATH="/opt/nic/bin:$PATH"

# Change to framework root
cd "$(dirname "$0")/.."

# Set ACA_DATA if not already set
export ACA_DATA="${ACA_DATA:-/home/nic/writing/data}"

# Run the index regeneration
uv run python scripts/regenerate_task_index.py
