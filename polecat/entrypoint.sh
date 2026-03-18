#!/bin/bash
set -e

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

    # Authenticate GitHub CLI (gh).
    # This enables 'gh pr create', 'gh issue view', etc. inside the agent.
    if command -v gh >/dev/null 2>&1; then
        echo "$GH_TOKEN" | gh auth login --with-token
        # Configure gh to act as a git credential helper.
        gh auth setup-git
    else
        # Fallback: Configure a universal git credential helper for HTTPS.
        # This ensures that even tools not aware of 'gh' can still push/pull.
        # We use $GH_TOKEN from the environment so the token isn't baked into the config file.
        git config --global credential.helper "!f() { echo username=x-access-token; echo \"password=\$GH_TOKEN\"; }; f"
    fi
fi

# Enforce isolation: Disable SSH and interactive prompts.
export SSH_AUTH_SOCK=""
export GIT_TERMINAL_PROMPT=0

# Execute the agent command (e.g., claude, gemini, bash).
exec "$@"
