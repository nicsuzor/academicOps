#!/usr/bin/env bash
# Robustly derive the Windows username for the current WSL session.
#
# Prints the username on stdout and exits 0 on success. On failure, prints a
# diagnostic to stderr and exits 1 — callers MUST treat a nonzero exit as
# fatal and halt, never silently skip the caller's operation. This replaces
# the old inline `cmd.exe /c "echo %USERNAME%"` one-liner in
# package-cowork-windows, which swallowed cmd.exe failures (2>/dev/null with
# no exit-code check) and silently produced an EMPTY username, building a
# bogus /mnt/c/Users//Downloads path that the caller then "skipped" as if it
# were a legitimate absence (task_bec9d6a1).
#
# Override: set WIN_USER in the environment to skip derivation entirely.
set -euo pipefail

if [ -n "${WIN_USER:-}" ]; then
	echo "$WIN_USER"
	exit 0
fi

# Preferred: ask Windows itself via cmd.exe — works even when the WSL user
# and Windows user differ, or /mnt/c/Users has multiple profiles.
if command -v cmd.exe >/dev/null 2>&1; then
	CANDIDATE="$(cmd.exe /c "echo %USERNAME%" 2>/dev/null | tr -d '\r\n' || true)"
	if [ -n "$CANDIDATE" ] && [ -d "/mnt/c/Users/$CANDIDATE" ]; then
		echo "$CANDIDATE"
		exit 0
	fi
fi

# Fallback: enumerate /mnt/c/Users for exactly one plausible per-user
# profile directory, excluding the well-known system/shared entries. Only
# usable when there is a single unambiguous candidate.
if [ -d /mnt/c/Users ]; then
	CANDIDATES=()
	while IFS= read -r -d '' dir; do
		base="$(basename "$dir")"
		case "$base" in
		Public | Default | "Default User" | "All Users" | desktop.ini) continue ;;
		esac
		CANDIDATES+=("$base")
	done < <(find /mnt/c/Users -mindepth 1 -maxdepth 1 -type d -print0 2>/dev/null)

	if [ "${#CANDIDATES[@]}" -eq 1 ]; then
		echo "${CANDIDATES[0]}"
		exit 0
	fi
fi

{
	echo "ERROR: could not determine the Windows username."
	echo "  cmd.exe was unavailable/failed, and /mnt/c/Users has zero or"
	echo "  multiple candidate profile directories, so no single answer is safe"
	echo "  to guess. Set WIN_USER=<name> in the environment and retry."
} >&2
exit 1
