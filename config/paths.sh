#!/bin/bash
# Path configuration for academicOps
# This file provides environment-based path resolution for multi-machine deployment

# Detect the base directory based on where this script is located
# This works regardless of which machine the system runs on
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Set default parent directory if not already set
# Users can override this by setting ACADEMIC_OPS_ROOT before sourcing this file
if [ -z "$ACADEMIC_OPS_ROOT" ]; then
    # Default: parent directory of the bot repository
    ACADEMIC_OPS_ROOT="$(cd "$BOT_ROOT/.." && pwd)"
    export ACADEMIC_OPS_ROOT
fi

# Export standardized paths
export ACADEMICOPS="$BOT_ROOT"
export ACADEMICOPS_DATA="$ACADEMIC_OPS_ROOT/data"
export ACADEMICOPS_DOCS="$ACADEMIC_OPS_ROOT/docs"
export ACADEMICOPS_PROJECTS="$ACADEMIC_OPS_ROOT/projects"
export ACADEMICOPS_SCRIPTS="$BOT_ROOT/scripts"

# Validation function to ensure required directories exist
validate_paths() {
    local missing_dirs=()

    [ ! -d "$ACADEMIC_OPS_ROOT" ] && missing_dirs+=("ACADEMIC_OPS_ROOT: $ACADEMIC_OPS_ROOT")
    [ ! -d "$ACADEMICOPS" ] && missing_dirs+=("ACADEMICOPS: $ACADEMICOPS")
    [ ! -d "$ACADEMICOPS_DATA" ] && missing_dirs+=("ACADEMICOPS_DATA: $ACADEMICOPS_DATA")

    if [ ${#missing_dirs[@]} -gt 0 ]; then
        echo "ERROR: Missing required directories:" >&2
        for dir in "${missing_dirs[@]}"; do
            echo "  - $dir" >&2
        done
        return 1
    fi
    return 0
}

# Print current configuration (useful for debugging)
print_config() {
    echo "Academic Ops Path Configuration:"
    echo "  ACADEMIC_OPS_ROOT: $ACADEMIC_OPS_ROOT"
    echo "  ACADEMICOPS: $ACADEMICOPS"
    echo "  ACADEMICOPS_DATA: $ACADEMICOPS_DATA"
    echo "  ACADEMICOPS_DOCS: $ACADEMICOPS_DOCS"
    echo "  ACADEMICOPS_PROJECTS: $ACADEMICOPS_PROJECTS"
    echo "  ACADEMICOPS_SCRIPTS: $ACADEMICOPS_SCRIPTS"
}
