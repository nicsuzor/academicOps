#!/bin/bash
# scripts/verify-crew-sessions.sh — Verify crew session transcript persistence
#
# Runs a minimal Claude session inside Docker with a session_dir mount
# and verifies that JSONL transcript files appear on the host.
#
# Usage:
#   bash scripts/verify-crew-sessions.sh          # Human-readable output
#   bash scripts/verify-crew-sessions.sh --json   # Machine-readable output

set -euo pipefail

JSON_OUTPUT=false
if [[ "${1:-}" == "--json" ]]; then
    JSON_OUTPUT=true
fi

IMAGE_NAME="${POLECAT_DOCKER_IMAGE:-aops-crew}"
SESSION_DIR=$(mktemp -d)
WORKSPACE=$(mktemp -d)
SESSION_ID=$(python3 -c "import uuid; print(uuid.uuid4())")

cleanup() {
    rm -rf "$SESSION_DIR" "$WORKSPACE" 2>/dev/null || true
}
trap cleanup EXIT

# --- Check prerequisites ---

check_prereq() {
    local name="$1" cmd="$2"
    if ! eval "$cmd" &>/dev/null; then
        if $JSON_OUTPUT; then
            echo "{\"pass\": false, \"error\": \"$name not available\"}"
        else
            echo "FAIL: $name not available"
        fi
        exit 1
    fi
}

check_prereq "Docker" "command -v docker"
check_prereq "aops-crew image" "docker images $IMAGE_NAME --format '{{.Repository}}' | grep -q '$IMAGE_NAME'"

# Check for Claude auth
HAS_AUTH=false
if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
    HAS_AUTH=true
elif [[ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}" ]]; then
    HAS_AUTH=true
elif [[ -f "$HOME/.claude/.credentials.json" ]]; then
    HAS_AUTH=true
fi

if ! $HAS_AUTH; then
    if $JSON_OUTPUT; then
        echo "{\"pass\": false, \"error\": \"No Claude auth (ANTHROPIC_API_KEY or OAuth credentials)\"}"
    else
        echo "FAIL: No Claude auth available"
    fi
    exit 1
fi

# --- Run minimal Claude session in Docker ---

if ! $JSON_OUTPUT; then
    echo "Running Claude in Docker with session_dir mount..."
    echo "  Image:      $IMAGE_NAME"
    echo "  Session ID: $SESSION_ID"
    echo "  Session dir: $SESSION_DIR"
fi

# Initialize a git repo in workspace (Claude expects it)
git init "$WORKSPACE" --quiet
(cd "$WORKSPACE" && git commit --allow-empty -m "init" --quiet)

# Build docker command matching _build_docker_cmd pattern
DOCKER_CMD=(
    docker run --rm -i
    --user "$(id -u):$(id -g)"
    -v "$WORKSPACE:/workspace"
    -w /workspace
    -v "$SESSION_DIR:/home/worker/.claude/projects"
)

# Mount Claude auth
if [[ -f "$HOME/.claude.json" ]]; then
    DOCKER_CMD+=(-v "$HOME/.claude.json:/home/worker/.claude.json:ro")
fi
if [[ -f "$HOME/.claude/.credentials.json" ]]; then
    DOCKER_CMD+=(-v "$HOME/.claude/.credentials.json:/home/worker/.claude/.credentials.json:ro")
fi
if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
    DOCKER_CMD+=(-e "ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY")
fi
if [[ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}" ]]; then
    DOCKER_CMD+=(-e "CLAUDE_CODE_OAUTH_TOKEN=$CLAUDE_CODE_OAUTH_TOKEN")
fi

DOCKER_CMD+=(
    "$IMAGE_NAME"
    claude --dangerously-skip-permissions
    -p "Reply with exactly: session test"
    --output-format json
    --session-id "$SESSION_ID"
    --model haiku
    --max-turns 2
)

# Run with timeout
if timeout 90 "${DOCKER_CMD[@]}" >/dev/null 2>&1; then
    CLAUDE_EXIT=0
else
    CLAUDE_EXIT=$?
fi

# --- Verify results ---

JSONL_COUNT=$(find "$SESSION_DIR" -name "*.jsonl" 2>/dev/null | wc -l)
JSONL_FILES=$(find "$SESSION_DIR" -name "*.jsonl" 2>/dev/null)
TOTAL_SIZE=0
if [[ -n "$JSONL_FILES" ]]; then
    TOTAL_SIZE=$(wc -c $JSONL_FILES 2>/dev/null | tail -1 | awk '{print $1}')
fi

PASS=false
if [[ $JSONL_COUNT -gt 0 && $TOTAL_SIZE -gt 0 ]]; then
    PASS=true
fi

if $JSON_OUTPUT; then
    cat <<EOF
{
  "pass": $PASS,
  "session_id": "$SESSION_ID",
  "claude_exit_code": $CLAUDE_EXIT,
  "jsonl_files_found": $JSONL_COUNT,
  "total_bytes": $TOTAL_SIZE,
  "session_dir": "$SESSION_DIR",
  "files": [$(echo "$JSONL_FILES" | sed 's/.*/"&"/' | paste -sd, -)]
}
EOF
else
    echo ""
    if $PASS; then
        echo "PASS: Session transcripts persisted successfully"
    else
        echo "FAIL: No session transcripts found"
    fi
    echo "  Claude exit code: $CLAUDE_EXIT"
    echo "  JSONL files found: $JSONL_COUNT"
    echo "  Total bytes: $TOTAL_SIZE"
    if [[ -n "$JSONL_FILES" ]]; then
        echo "  Files:"
        echo "$JSONL_FILES" | sed 's/^/    /'
    fi
fi

$PASS
