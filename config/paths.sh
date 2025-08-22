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
    export ACADEMIC_OPS_ROOT="$(cd "$BOT_ROOT/.." && pwd)"
fi

# Export standardized paths
export ACADEMIC_OPS_BOT="$BOT_ROOT"
export ACADEMIC_OPS_DATA="$ACADEMIC_OPS_ROOT/data"
export ACADEMIC_OPS_DOCS="$ACADEMIC_OPS_ROOT/docs"
export ACADEMIC_OPS_PROJECTS="$ACADEMIC_OPS_ROOT/projects"
export ACADEMIC_OPS_SCRIPTS="$BOT_ROOT/scripts"

# Validation function to ensure required directories exist
validate_paths() {
    local missing_dirs=()
    
    [ ! -d "$ACADEMIC_OPS_ROOT" ] && missing_dirs+=("ACADEMIC_OPS_ROOT: $ACADEMIC_OPS_ROOT")
    [ ! -d "$ACADEMIC_OPS_BOT" ] && missing_dirs+=("ACADEMIC_OPS_BOT: $ACADEMIC_OPS_BOT")
    [ ! -d "$ACADEMIC_OPS_DATA" ] && missing_dirs+=("ACADEMIC_OPS_DATA: $ACADEMIC_OPS_DATA")
    
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
    echo "  ACADEMIC_OPS_BOT: $ACADEMIC_OPS_BOT"
    echo "  ACADEMIC_OPS_DATA: $ACADEMIC_OPS_DATA"
    echo "  ACADEMIC_OPS_DOCS: $ACADEMIC_OPS_DOCS"
    echo "  ACADEMIC_OPS_PROJECTS: $ACADEMIC_OPS_PROJECTS"
    echo "  ACADEMIC_OPS_SCRIPTS: $ACADEMIC_OPS_SCRIPTS"
}