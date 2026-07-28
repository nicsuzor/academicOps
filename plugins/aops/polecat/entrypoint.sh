#!/bin/bash
# Container entrypoint: configure git, install the scoped credential helper,
# apply staged config, then exec the agent CLI.
#
# Every value comes from the environment. Nothing is defaulted here.

set -euo pipefail

if [ -z "${GIT_AUTHOR_NAME:-}" ] || [ -z "${GIT_AUTHOR_EMAIL:-}" ]; then
    echo "FATAL: GIT_AUTHOR_NAME and GIT_AUTHOR_EMAIL must be set. There is no default identity." >&2
    exit 1
fi
export GIT_COMMITTER_NAME="${GIT_COMMITTER_NAME:-$GIT_AUTHOR_NAME}"
export GIT_COMMITTER_EMAIL="${GIT_COMMITTER_EMAIL:-$GIT_AUTHOR_EMAIL}"

git config --global user.name "$GIT_AUTHOR_NAME"
git config --global user.email "$GIT_AUTHOR_EMAIL"

# Rewrite SSH remotes to HTTPS: a worktree created with an SSH remote on the
# host has no usable key in here.
git config --global url."https://github.com/".insteadOf "git@github.com:"

if [ -z "${AOPS_BOT_GH_TOKEN:-}" ]; then
    echo "FATAL: AOPS_BOT_GH_TOKEN is not set. Polecat requires it for repository access." >&2
    exit 1
fi
export GH_TOKEN="$AOPS_BOT_GH_TOKEN"
export GITHUB_TOKEN="$AOPS_BOT_GH_TOKEN"
git config --global credential.helper \
    "!f() { echo username=x-access-token; echo \"password=\$GH_TOKEN\"; }; f"

# No SSH agent, no interactive prompt: auth resolves from the token or fails.
export SSH_AUTH_SOCK=""
export GIT_TERMINAL_PROMPT=0

# Copy staged config into $HOME, overwriting image defaults. Copying rather
# than mounting avoids an overlayfs bug that treats file mounts as
# directories; --no-preserve avoids permission errors when the container runs
# under a different UID than the image's user.
#
# Process substitution, not a pipe: a piped `while` runs in a subshell where
# `exit 1` would only leave the subshell and the script would continue.
if [ -d /tmp/staging ]; then
    while read -r src; do
        dest="$HOME/${src#/tmp/staging/}"
        mkdir -p "$(dirname "$dest")"
        if [ "$dest" = "$HOME/.claude/settings.json" ] && [ -f "$dest" ]; then
            # Merge, do not overwrite. The baked settings file is the source of
            # truth for enabledPlugins — the key that activates the plugins and
            # their hooks. The staged file carries only per-session overlays and
            # has no such key, so a plain overwrite deactivates everything.
            merged="$(mktemp)"
            if jq -s '.[0] * .[1]' "$dest" "$src" > "$merged" && [ -s "$merged" ]; then
                cp --no-preserve=mode,ownership "$merged" "$dest"
                rm -f "$merged"
            else
                rm -f "$merged"
                echo "Error: failed to merge staged settings '$src' into '$dest'" >&2
                exit 1
            fi
        elif ! cp --no-preserve=mode,ownership "$src" "$dest"; then
            echo "Error: failed to copy staged file '$src' to '$dest'" >&2
            exit 1
        fi
    done < <(find /tmp/staging -type f)
fi

# Keep .config traversable for multi-UID runs.
chmod 777 "$HOME/.config" 2>/dev/null || true

exec "$@"
