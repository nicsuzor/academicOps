#!/usr/bin/env bash
# launch-named-agents.sh
# Creates a 4-pane tmux session with persistent named agent sessions:
# - Top-Left:  ida (Discord interface / host session in /workspace/junior/ida, -n ida)
# - Top-Right: sara (WSL host runner via ssh wsl in ~/junior/dispatch, -n sara)
# - Bottom-Left: pauli (PKB writer in /data, -n pauli)
# - Bottom-Right: blank (reserved for OpenClaw)

set -euo pipefail

SESSION_NAME="${1:-agents}"

# 1. Create detached tmux session with first window
tmux new-session -d -s "$SESSION_NAME" -n "team" -c "/workspace/junior/ida"

# 2. Split horizontally to create top-right pane
tmux split-window -h -t "$SESSION_NAME:0" -c "/workspace/junior/dispatch"

# 3. Split top-left pane vertically to create bottom-left pane
tmux split-window -v -t "$SESSION_NAME:0.0" -c "/data"

# 4. Split top-right pane vertically to create bottom-right pane (blank / openclaw)
tmux split-window -v -t "$SESSION_NAME:0.1"

# 5. Apply 2x2 tiled layout
tmux select-layout -t "$SESSION_NAME:0" tiled

# 6. Launch commands in respective panes
# Pane 0.0: ida
tmux send-keys -t "$SESSION_NAME:0.0" "cd /workspace/junior/ida && claude -n ida --agent ida" C-m

# Pane 0.1: sara (on WSL host via ssh wsl)
tmux send-keys -t "$SESSION_NAME:0.1" "ssh wsl 'cd ~/junior/dispatch && claude -n sara --agent ida'" C-m

# Pane 0.2: pauli (nicdev container, /data)
tmux send-keys -t "$SESSION_NAME:0.2" "cd /data && claude -n pauli --agent pauli" C-m

# Pane 0.3: blank placeholder for openclaw
tmux send-keys -t "$SESSION_NAME:0.3" "echo 'OpenClaw pane (reserved for future integration)'" C-m

# Focus back on ida pane
tmux select-pane -t "$SESSION_NAME:0.0"

echo "Started tmux session '$SESSION_NAME' with 4 panes (ida, sara, pauli, openclaw)."
echo "Attach to session with: tmux attach -t $SESSION_NAME"
