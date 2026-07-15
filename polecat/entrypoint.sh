#!/bin/bash

# Configure git identity if not already set in environment.
# These variables are forwarded by polecat/cli.py but can be defaulted here.
export GIT_AUTHOR_NAME="${GIT_AUTHOR_NAME:-aops-bot}"  # allow-fallback: git identity defaults
export GIT_AUTHOR_EMAIL="${GIT_AUTHOR_EMAIL:-aops-bot@users.noreply.github.com}"  # allow-fallback: git identity defaults
export GIT_COMMITTER_NAME="${GIT_COMMITTER_NAME:-$GIT_AUTHOR_NAME}"
export GIT_COMMITTER_EMAIL="${GIT_COMMITTER_EMAIL:-$GIT_AUTHOR_EMAIL}"

# Apply to global git config inside the container.
git config --global user.name "$GIT_AUTHOR_NAME"
git config --global user.email "$GIT_AUTHOR_EMAIL"

# Force HTTPS for all GitHub operations (rewrite SSH remotes to HTTPS).
# This ensures that even if a worktree was created with an SSH remote on the host,
# the container will use HTTPS for all git commands.
git config --global url."https://github.com/".insteadOf "git@github.com:"

# GitHub authentication — AOPS_BOT_GH_TOKEN is the only accepted credential.
if [ -z "$AOPS_BOT_GH_TOKEN" ]; then
    echo "FATAL: AOPS_BOT_GH_TOKEN is not set. Polecat requires this token for GitHub access." >&2
    exit 1
fi

export GH_TOKEN="$AOPS_BOT_GH_TOKEN"
export GITHUB_TOKEN="$AOPS_BOT_GH_TOKEN"

git config --global credential.helper "!f() { echo username=x-access-token; echo \"password=\$GH_TOKEN\"; }; f"

# Enforce isolation: Disable SSH and interactive prompts.
export SSH_AUTH_SOCK=""
export GIT_TERMINAL_PROMPT=0

# Copy staged auth files into $HOME (avoids overlayfs file-mount bug on macOS
# where chmod 777 on $HOME causes runc to treat file mounts as directories).
# Copy staged files, overwriting image defaults. Use --no-preserve to avoid
# permission errors when running as a different UID than the image's worker user.
#
# NOTE: Uses process substitution (< <(find ...)) instead of a pipe so the
# while loop runs in the current shell. A piped `| while` runs in a subshell,
# where `exit 1` only exits the subshell — the script would continue silently.
if [ -d /tmp/staging ]; then
    while read -r src; do
        dest="$HOME/${src#/tmp/staging/}"
        mkdir -p "$(dirname "$dest")"
        if [ "$dest" = "$HOME/.claude/settings.json" ] && [ -f "$dest" ]; then
            # Merge, don't overwrite: the baked settings.json
            # (polecat/defaults/claude-settings.json) is the single source of
            # truth for `enabledPlugins` — the key that actually activates the
            # aops/aops-tools plugins (MCP servers + hooks). The staged file
            # (polecat/cli.py setup_staging()) carries only per-session
            # overlays (model, pluginConfigs.pkb_mcp_url) and has no
            # `enabledPlugins` key at all. A plain overwrite here silently
            # deactivated every plugin inside the container (aops_20d97385).
            # `jq -s '.[0] * .[1]'` shallow-merges dest then src: baked-only
            # keys (enabledPlugins, statusLine, autoMode) survive, staged-only
            # keys (pluginConfigs) are added, and staged wins on any key both
            # define (model).
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

# Belt-and-suspenders: ensure .config is traversable for multi-UID environments.
# Containers built from images predating the Dockerfile umask fix may have
# .config at 0644 (non-traversable); this self-heals them on startup.
chmod 777 "$HOME/.config" 2>/dev/null || true

# Note: Claude settings.json injection (pkb_mcp_url via pluginConfigs) is staged
# at launch time by polecat/cli.py setup_staging() and merged into the baked
# settings.json above (preserving enabledPlugins). Direct container invocations
# that bypass cli.py will have agy working (PKB_MCP_URL inherited from env) but
# Claude missing pkb_mcp_url — and no staged settings.json to merge at all, so
# the baked enabledPlugins-bearing file is used untouched.

# Execute the agent command (e.g., claude, gemini, bash).
exec "$@"
