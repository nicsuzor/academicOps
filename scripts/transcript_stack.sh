#!/usr/bin/env bash
set -Eeuo pipefail

# Start AgentsView and keep agy-reader running so Antigravity CLI transcripts
# are converted into .trajectory.json sidecars for AgentsView.
#
# Usage:
#   ./start-agent-transcript-stack.sh
#   ./start-agent-transcript-stack.sh --install-user-service   # Linux/systemd user autostart
#   ./start-agent-transcript-stack.sh --uninstall-user-service

APP_NAME="agent-transcript-stack"
LOG_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/$APP_NAME"
LOG_FILE="$LOG_DIR/$APP_NAME.log"
WATCH_INTERVAL="${AGY_READER_WATCH_INTERVAL:-30s}"
AGENTSVIEW_PORT="${AGENTSVIEW_PORT:-8080}"
SERVICE_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
SERVICE_FILE="$SERVICE_DIR/$APP_NAME.service"
SCRIPT_PATH="$(readlink -f "$0" 2>/dev/null || python3 -c 'import os,sys; print(os.path.abspath(sys.argv[1]))' "$0")"

mkdir -p "$LOG_DIR"

ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() { printf '[%s] %s\n' "$(ts)" "$*" | tee -a "$LOG_FILE" >&2; }
have() { command -v "$1" >/dev/null 2>&1; }

install_user_service() {
  if ! have systemctl; then
    log "systemctl not found; cannot install a systemd user service on this machine."
    exit 1
  fi
  mkdir -p "$SERVICE_DIR"
  cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=AgentsView + agy-reader transcript stack
After=default.target

[Service]
Type=simple
ExecStart=$SCRIPT_PATH
Restart=always
RestartSec=15
Environment=AGY_READER_WATCH_INTERVAL=$WATCH_INTERVAL
Environment=AGENTSVIEW_PORT=$AGENTSVIEW_PORT

[Install]
WantedBy=default.target
EOF
  systemctl --user daemon-reload
  systemctl --user enable --now "$APP_NAME.service"
  log "Installed and started user service: $SERVICE_FILE"
  log "Status: systemctl --user status $APP_NAME.service"
}

uninstall_user_service() {
  if have systemctl; then
    systemctl --user disable --now "$APP_NAME.service" 2>/dev/null || true
    rm -f "$SERVICE_FILE"
    systemctl --user daemon-reload || true
  fi
  log "Uninstalled user service if it existed."
}

case "${1:-}" in
  --install-user-service) install_user_service; exit 0 ;;
  --uninstall-user-service) uninstall_user_service; exit 0 ;;
  -h|--help)
    sed -n '1,24p' "$SCRIPT_PATH"
    exit 0
    ;;
esac

log "Starting $APP_NAME"
log "Log file: $LOG_FILE"

# 1) Start AgentsView. On first run it discovers/indexes historical supported sessions.
if have agentsview; then
  log "Starting AgentsView on http://127.0.0.1:$AGENTSVIEW_PORT"
  agentsview serve --port "$AGENTSVIEW_PORT" --background >>"$LOG_FILE" 2>&1 || \
    log "AgentsView may already be running, or failed to start; continuing."
elif have uvx; then
  log "agentsview binary not found; trying uvx agentsview serve --background"
  uvx agentsview serve --port "$AGENTSVIEW_PORT" --background >>"$LOG_FILE" 2>&1 || \
    log "uvx agentsview failed; install AgentsView and rerun."
else
  log "WARNING: agentsview not found. Install it, then rerun this script."
fi

# Extract likely agy JSON-RPC port. The agy daemon binds a different port every session.
# Manual checks if auto-detection fails:
#   ss -tlnp 2>/dev/null | grep agy                  # Linux
#   lsof -iTCP -sTCP:LISTEN -anP | grep agy          # macOS
# agy exposes two localhost ports; the lower one is the JSON-RPC endpoint.
detect_agy_daemon_url() {
  if [[ -n "${ANTIGRAVITY_DAEMON_URL:-}" ]]; then
    printf '%s\n' "$ANTIGRAVITY_DAEMON_URL"
    return 0
  fi

  local ports=""
  if have ss; then
    ports="$({ ss -tlnp 2>/dev/null || true; } | awk '
      /agy/ {
        for (i=1; i<=NF; i++) {
          if ($i ~ /127\.0\.0\.1:[0-9]+$/ || $i ~ /\[::1\]:[0-9]+$/) {
            sub(/^.*:/, "", $i); print $i
          }
        }
      }' | sort -n | uniq)"
  elif have lsof; then
    ports="$(lsof -iTCP -sTCP:LISTEN -anP 2>/dev/null | awk '/agy/ { sub(/^.*:/, "", $9); print $9 }' | sort -n | uniq)"
  fi

  if [[ -n "$ports" ]]; then
    printf 'http://127.0.0.1:%s\n' "$(printf '%s\n' "$ports" | head -n 1)"
    return 0
  fi
  return 1
}

# 2) Keep agy-reader running. This is the historical-ingest line:
#    --watch polls the whole session root and writes sidecars for ANY .pb whose
#    .trajectory.json sidecar is missing or older than the .pb file.
while true; do
  if ! have agy-reader; then
    log "WARNING: agy-reader not found. Install with: go install github.com/mjacobs/agy-reader@latest"
    sleep 60
    continue
  fi

  if daemon_url="$(detect_agy_daemon_url)"; then
    export ANTIGRAVITY_DAEMON_URL="$daemon_url"
    log "Starting agy-reader watch against $ANTIGRAVITY_DAEMON_URL"
    agy-reader --watch --watch-interval="$WATCH_INTERVAL" >>"$LOG_FILE" 2>&1 || \
      log "agy-reader exited; will retry after a short delay."
  else
    log "No running agy daemon found. Start 'agy' in a project; retrying in 30s."
    sleep 30
  fi

done
