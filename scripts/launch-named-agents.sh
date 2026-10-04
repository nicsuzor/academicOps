#!/usr/bin/env bash
# launch-named-agents.sh
# Creates a 4-pane tmux session with persistent named agent sessions:
# - Top-Left:  ida (container session in $AOPS_IDA_DIR, runs $AOPS_IDA_CMD)
# - Top-Right: sara (local runner in $AOPS_SARA_DIR, runs $AOPS_SARA_CMD)
# - Bottom-Left: pauli (container session in $ACA_DATA, -n pauli)
# - Bottom-Right: plain shell
#
# Required environment:
#   AOPS_AGENT_CONTAINER  docker container that hosts ida and pauli
#   AOPS_IDA_DIR          ida's working directory inside that container
#   AOPS_IDA_CMD          command that starts ida inside that container
#   AOPS_SARA_DIR         sara's working directory on this host
#   AOPS_SARA_CMD         command that starts sara on this host
#   ACA_DATA              PKB data directory inside that container

set -euo pipefail

: "${AOPS_AGENT_CONTAINER:?AOPS_AGENT_CONTAINER must be set}"
: "${AOPS_IDA_DIR:?AOPS_IDA_DIR must be set}"
: "${AOPS_IDA_CMD:?AOPS_IDA_CMD must be set}"
: "${AOPS_SARA_DIR:?AOPS_SARA_DIR must be set}"
: "${AOPS_SARA_CMD:?AOPS_SARA_CMD must be set}"
: "${ACA_DATA:?ACA_DATA must be set}"

SESSION_NAME="${1:-agents}"

# 1. Create detached tmux session with first window
tmux new-session -d -s "$SESSION_NAME" -n "team"

# 2. Split horizontally to create top-right pane
tmux split-window -h -t "$SESSION_NAME:0"

# 3. Split top-left pane vertically to create bottom-left pane
tmux split-window -v -t "$SESSION_NAME:0.0"

# 4. Split top-right pane vertically to create bottom-right pane (plain shell)
tmux split-window -v -t "$SESSION_NAME:0.1"

# 5. Apply 2x2 tiled layout
tmux select-layout -t "$SESSION_NAME:0" tiled

# 6. Launch commands in respective panes
# Pane 0.0: ida (container, $AOPS_IDA_DIR)
tmux send-keys -t "$SESSION_NAME:0.0" "docker exec -it -w '$AOPS_IDA_DIR' '$AOPS_AGENT_CONTAINER' $AOPS_IDA_CMD" C-m

# Pane 0.1: sara (local host runner)
tmux send-keys -t "$SESSION_NAME:0.1" "cd '$AOPS_SARA_DIR' && $AOPS_SARA_CMD" C-m

# Pane 0.2: pauli (container, $ACA_DATA)
tmux send-keys -t "$SESSION_NAME:0.2" "docker exec -it -w '$ACA_DATA' '$AOPS_AGENT_CONTAINER' claude -n pauli --agent pauli" C-m

# Pane 0.3: plain shell, nothing launched

# Focus back on ida pane
tmux select-pane -t "$SESSION_NAME:0.0"

echo "Started tmux session '$SESSION_NAME' with 4 panes (ida, sara, pauli, shell)."
echo "Attach to session with: tmux attach -t $SESSION_NAME"
