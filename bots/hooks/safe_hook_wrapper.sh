#!/bin/bash
# Safe Hook Wrapper: Prevents recursive failures by checking file existence first
# Usage: safe_hook_wrapper.sh <python_script> [args...]
#
# Returns:
#   0: Script executed successfully
#   1: Script file not found or not executable (safe failure)
#   Other: Actual script exit code

# Get the script path from the first argument
SCRIPT_PATH="$1"
shift  # Remove first argument, leaving only additional args

# Check if script path was provided
if [ -z "$SCRIPT_PATH" ]; then
    echo "Error: No script path provided" >&2
    exit 1
fi

# Check if the script file exists
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "Error: Script file not found: $SCRIPT_PATH" >&2
    exit 1
fi

# Check if the script is readable
if [ ! -r "$SCRIPT_PATH" ]; then
    echo "Error: Script file not readable: $SCRIPT_PATH" >&2
    exit 1
fi

# Execute the Python script with remaining arguments
# Pass through stdin, stdout, stderr, and exit code
exec uv run python3 "$SCRIPT_PATH" "$@"
