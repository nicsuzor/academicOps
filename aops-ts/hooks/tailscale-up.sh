#!/usr/bin/env bash
# aops-ts SessionStart hook — bring Tailscale up in remote/cloud sessions so
# tailnet services (e.g. the PKB MCP at *.ts.net) resolve.
#
# Opt-in by design: this lives in the standalone `aops-ts` plugin, NOT aops-core.
# Enable it only in environments that should join the tailnet.
#
# Division of labour:
#   - The environment's setup/init script INSTALLS tailscale (needs root +
#     curl|sh, and runs at container init — where TS_AUTHKEY is NOT yet present).
#   - This hook brings the tailnet UP at session start, where TS_AUTHKEY IS
#     injected. It installs nothing.
#
# No-ops (exit 0) unless: remote session, TS_AUTHKEY set, tailscale installed.
# It always exits 0 — a tailscale hiccup must never block SessionStart.

set -uo pipefail
exec 1>&2   # SessionStart stdout is injected into the model context — keep it empty

[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0
[ -n "${TS_AUTHKEY:-}" ] || { echo "[aops-ts] TS_AUTHKEY not set; skipping tailscale bring-up."; exit 0; }
command -v tailscale >/dev/null 2>&1 || {
  echo "[aops-ts] tailscale not installed — add the install line to your environment setup script; skipping."
  exit 0
}

# Some remote environments run the session as a non-root user; tailscale(d) then
# needs sudo. Use passwordless sudo when available, else run direct (works as root).
SUDO=""
if [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
  SUDO="sudo -n"
fi

# Log to a user-writable dir: the shell performs the redirect (as the session
# user), so /var/log would fail with "permission denied" for non-root even under sudo.
LOG="${TMPDIR:-/tmp}/tailscaled.log"

# Already connected? Nothing to do (daemon + state persist within a container).
if $SUDO tailscale status >/dev/null 2>&1; then
  echo "[aops-ts] tailscale already up as $($SUDO tailscale ip -4 2>/dev/null | head -1)"
  exit 0
fi

# Daemon is per-process (the container cache keeps files, not processes) — start it if absent.
if ! pgrep -x tailscaled >/dev/null 2>&1; then
  $SUDO mkdir -p /var/lib/tailscale /var/run/tailscale
  $SUDO setsid tailscaled \
    --state=/var/lib/tailscale/tailscaled.state \
    --socket=/var/run/tailscale/tailscaled.sock \
    --tun=tailscale0 \
    >"$LOG" 2>&1 </dev/null & disown || true
  # Wait for the socket, but fail fast if the daemon dies (missing tun, fatal error)
  # instead of blocking session start for the full 15s.
  for _ in $(seq 1 30); do
    [ -S /var/run/tailscale/tailscaled.sock ] && break
    pgrep -x tailscaled >/dev/null 2>&1 || break
    sleep 0.5
  done
fi

if $SUDO tailscale up --authkey="${TS_AUTHKEY}" \
     --hostname="claude-web-${HOSTNAME:-sandbox}" \
     --accept-routes --accept-dns=true; then
  echo "[aops-ts] tailscale up as $($SUDO tailscale ip -4 2>/dev/null | head -1)"
else
  echo "[aops-ts] 'tailscale up' failed; see $LOG"
fi

exit 0
