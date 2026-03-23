#!/bin/bash

# Configure git identity if not already set in environment.
# These variables are forwarded by polecat/cli.py but can be defaulted here.
export GIT_AUTHOR_NAME="${GIT_AUTHOR_NAME:-aops-bot}"
export GIT_AUTHOR_EMAIL="${GIT_AUTHOR_EMAIL:-aops-bot@users.noreply.github.com}"
export GIT_COMMITTER_NAME="${GIT_COMMITTER_NAME:-$GIT_AUTHOR_NAME}"
export GIT_COMMITTER_EMAIL="${GIT_COMMITTER_EMAIL:-$GIT_AUTHOR_EMAIL}"

# Apply to global git config inside the container.
git config --global user.name "$GIT_AUTHOR_NAME"
git config --global user.email "$GIT_AUTHOR_EMAIL"

# Force HTTPS for all GitHub operations (rewrite SSH remotes to HTTPS).
# This ensures that even if a worktree was created with an SSH remote on the host,
# the container will use HTTPS for all git commands.
git config --global url."https://github.com/".insteadOf "git@github.com:"

# Handle GitHub authentication via PAT if provided.
# AOPS_BOT_GH_TOKEN is the primary secret; GH_TOKEN is the standard for gh CLI.
TOKEN="${GH_TOKEN:-$AOPS_BOT_GH_TOKEN}"

if [ -n "$TOKEN" ]; then
    export GH_TOKEN="$TOKEN"
    export GITHUB_TOKEN="$TOKEN"

    # gh CLI uses GH_TOKEN from the environment automatically — no login needed.
    # Configure a universal git credential helper for HTTPS so git push/pull
    # works with the token. This covers both gh-aware and plain-git operations.
    git config --global credential.helper "!f() { echo username=x-access-token; echo \"password=\$GH_TOKEN\"; }; f"
fi

# Enforce isolation: Disable SSH and interactive prompts.
export SSH_AUTH_SOCK=""
export GIT_TERMINAL_PROMPT=0

# Copy staged auth files into $HOME (avoids overlayfs file-mount bug on macOS
# where chmod 777 on $HOME causes runc to treat file mounts as directories).
# Copy staged files, overwriting image defaults. Use --no-preserve to avoid
# permission errors when running as a different UID than the image's worker user.
if [ -d /tmp/staging ]; then
    find /tmp/staging -type f | while read -r src; do
        dest="$HOME/${src#/tmp/staging/}"
        mkdir -p "$(dirname "$dest")"
        cp --no-preserve=mode,ownership "$src" "$dest" 2>/dev/null || true
    done
fi

# Execute the agent command (e.g., claude, gemini, bash).
exec "$@"
