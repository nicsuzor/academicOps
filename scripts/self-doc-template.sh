#!/bin/bash
################################################################################
# Self-Documenting Script Template
################################################################################
#
# PURPOSE:
#   This is a template for creating self-documenting shell scripts that follow
#   the academicOps documentation philosophy. Scripts should explain themselves
#   through comprehensive inline documentation and --help output, eliminating
#   the need for separate README.md files.
#
# USAGE:
#   ./self-doc-template.sh [OPTIONS] <required_arg>
#
#   Copy this file as a starting point for new scripts:
#     cp .academicOps/scripts/self-doc-template.sh .academicOps/scripts/my-new-script.sh
#
# OPTIONS:
#   -h, --help              Show this help message and exit
#   -v, --verbose           Enable verbose output
#   -n, --dry-run           Show what would be done without doing it
#   -f, --force             Skip confirmation prompts
#   -o, --output <path>     Output file path (default: stdout)
#
# ARGUMENTS:
#   <required_arg>          Description of required positional argument
#
# EXAMPLES:
#   # Basic usage with required argument
#   ./self-doc-template.sh my-input-file
#
#   # With optional output file
#   ./self-doc-template.sh --output results.txt my-input-file
#
#   # Dry run to preview actions
#   ./self-doc-template.sh --dry-run --verbose my-input-file
#
#   # Force mode (skip confirmations)
#   ./self-doc-template.sh --force my-input-file
#
# EXIT CODES:
#   0   Success
#   1   General error
#   2   Invalid arguments
#   3   Missing dependencies
#   4   Permission denied
#
# ENVIRONMENT VARIABLES:
#   MY_VAR          Optional configuration (default: "default_value")
#   DEBUG           Set to "1" for debug output
#
# DEPENDENCIES:
#   - bash >= 4.0
#   - jq (for JSON processing)
#   - curl (for API calls)
#
# FILES:
#   Input:  Reads from <required_arg>
#   Output: Writes to --output or stdout
#   Temp:   Creates temporary files in /tmp/scriptname-*
#
# NOTES:
#   - This script is idempotent (safe to run multiple times)
#   - Uses fail-fast approach (set -euo pipefail)
#   - Cleans up temporary files on exit
#
# DESIGN DECISIONS:
#   Why use bash instead of Python?
#     - Simpler for file operations and process orchestration
#     - No virtual environment dependencies
#     - More portable for system-level tasks
#
#   Why --help instead of README.md?
#     - Documentation stays current with code
#     - Users get help where they use the script
#     - No separate file to maintain
#     - Single source of truth
#
# AUTHOR:
#   Created by academicOps agent framework
#   Based on academicOps documentation philosophy
#
################################################################################

# Fail fast: exit on error, undefined variables, or pipe failures
set -euo pipefail

# Default values for optional parameters
VERBOSE=false
DRY_RUN=false
FORCE=false
OUTPUT=""
MY_VAR="${MY_VAR:-default_value}"
DEBUG="${DEBUG:-0}"

# Color codes for output (disabled if not a terminal)
if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    NC='\033[0m' # No Color
else
    RED=''
    GREEN=''
    YELLOW=''
    NC=''
fi

################################################################################
# Helper Functions
################################################################################

# Print help message by extracting header comment
show_help() {
    # Extract lines from start of comment block to end marker
    sed -n '2,/^################################################################################$/p' "$0" | \
        sed 's/^# //; s/^#//' | \
        head -n -1  # Remove the final delimiter line
    exit 0
}

# Print error message to stderr and exit
error() {
    echo -e "${RED}ERROR: $1${NC}" >&2
    exit "${2:-1}"
}

# Print warning message to stderr
warn() {
    echo -e "${YELLOW}WARNING: $1${NC}" >&2
}

# Print info message (only if verbose)
info() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "${GREEN}INFO: $1${NC}" >&2
    fi
}

# Debug output (only if DEBUG=1)
debug() {
    if [[ "$DEBUG" == "1" ]]; then
        echo -e "DEBUG: $1" >&2
    fi
}

# Check if required command exists
require_command() {
    if ! command -v "$1" &> /dev/null; then
        error "Required command not found: $1" 3
    fi
}

# Clean up temporary files on exit
cleanup() {
    local exit_code=$?
    debug "Cleaning up temporary files..."
    # Add cleanup commands here
    # rm -f /tmp/scriptname-*
    exit $exit_code
}

# Set up trap for cleanup on exit
trap cleanup EXIT INT TERM

################################################################################
# Argument Parsing
################################################################################

# Parse command-line arguments
POSITIONAL_ARGS=()

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -n|--dry-run)
            DRY_RUN=true
            info "Dry run mode enabled"
            shift
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -o|--output)
            OUTPUT="$2"
            shift 2
            ;;
        -*|--*)
            error "Unknown option: $1" 2
            ;;
        *)
            POSITIONAL_ARGS+=("$1")
            shift
            ;;
    esac
done

# Restore positional parameters
set -- "${POSITIONAL_ARGS[@]}"

# Validate required arguments
if [[ $# -lt 1 ]]; then
    error "Missing required argument. Run with --help for usage." 2
fi

REQUIRED_ARG="$1"
debug "Required argument: $REQUIRED_ARG"

################################################################################
# Dependency Checking
################################################################################

# Check for required commands
require_command "jq"
require_command "curl"

# Validate input file exists (if applicable)
if [[ ! -f "$REQUIRED_ARG" ]]; then
    error "Input file not found: $REQUIRED_ARG" 1
fi

################################################################################
# Main Script Logic
################################################################################

main() {
    info "Starting script execution..."
    info "Input: $REQUIRED_ARG"

    # Step 1: Describe what you're doing
    info "Step 1: Processing input..."

    if [[ "$DRY_RUN" == "true" ]]; then
        echo "[DRY RUN] Would process: $REQUIRED_ARG"
        echo "[DRY RUN] Would output to: ${OUTPUT:-stdout}"
        return 0
    fi

    # Step 2: Actual processing
    # Replace with your logic
    local result
    result=$(cat "$REQUIRED_ARG")

    # Step 3: Output results
    if [[ -n "$OUTPUT" ]]; then
        echo "$result" > "$OUTPUT"
        info "Results written to: $OUTPUT"
    else
        echo "$result"
    fi

    info "Script completed successfully"
}

# Execute main function
main

exit 0
