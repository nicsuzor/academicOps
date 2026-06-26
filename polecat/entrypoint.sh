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
        if ! cp --no-preserve=mode,ownership "$src" "$dest"; then
            echo "Error: failed to copy staged file '$src' to '$dest'" >&2
            exit 1
        fi
    done < <(find /tmp/staging -type f)
fi

# Belt-and-suspenders: ensure .config is traversable for multi-UID environments.
# Containers built from images predating the Dockerfile umask fix may have
# .config at 0644 (non-traversable); this self-heals them on startup.
chmod 777 "$HOME/.config" 2>/dev/null || true

# Seed the aops-core plugin's userConfig from PKB_MCP_URL.
#
# The Claude build of aops-core declares `userConfig.pkb_mcp_url` and substitutes
# it into the pkb MCP server's env block as `${user_config.pkb_mcp_url}`. That
# value normally comes from an interactive enable-time prompt persisted to
# settings.json — which never happens in a headless container. Claude Code's MCP
# launcher does NOT propagate this process's env to the server, so simply having
# PKB_MCP_URL exported here is not enough; it must reach run-mcp.sh via the
# userConfig→env substitution. We therefore write the value the container was
# given (PKB_MCP_URL, forwarded by polecat/cli.py per agent-env-map.conf) into
# settings.json under pluginConfigs["aops-core@academicOps"].options.pkb_mcp_url,
# the exact location Claude Code reads for `${user_config.pkb_mcp_url}`.
#
# If PKB_MCP_URL is unset we do NOT invent a value: run-mcp.sh then hard-fails
# (no ~/.env.local fallback), surfacing the misconfiguration instead of silently
# connecting to nothing.
if [ -n "$PKB_MCP_URL" ]; then
    SETTINGS="$HOME/.claude/settings.json"
    if ! PKB_MCP_URL="$PKB_MCP_URL" SETTINGS="$SETTINGS" python3 - <<'PY'
import json, os, pathlib, sys

path = pathlib.Path(os.environ["SETTINGS"])
url = os.environ["PKB_MCP_URL"]
try:
    data = json.loads(path.read_text()) if path.exists() else {}
except (OSError, ValueError) as exc:
    print(f"WARN: could not read {path} ({exc}); starting from empty settings", file=sys.stderr)
    data = {}

cfg = data.setdefault("pluginConfigs", {}).setdefault("aops-core@academicOps", {})
cfg.setdefault("options", {})["pkb_mcp_url"] = url

path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(data, indent=2) + "\n")
print(f"Seeded pkb_mcp_url into {path} (pluginConfigs.aops-core@academicOps.options)", file=sys.stderr)
PY
    then
        echo "WARN: failed to seed pkb_mcp_url into settings.json; pkb MCP may not connect." >&2
    fi

    # Inject PKB_MCP_URL into Antigravity (agy) MCP config.
    #
    # Antigravity is unlike Claude: its mcp_config.json supports a per-server
    # `env` block, but it does NOT expand `${VAR}` references (unlike Gemini CLI)
    # and has no plugin userConfig mechanism. So neither the Claude userConfig
    # path nor Gemini's `${PKB_MCP_URL}` form works — we must write the LITERAL
    # resolved URL into the pkb server's `env` block. agy installs the plugin to
    # two locations (the source plugin dir under antigravity-cli/plugins and the
    # registered copy under config/plugins); patch every aops-core mcp_config.json
    # that declares a pkb server so whichever agy reads is covered.
    # agy reads its config from <GEMINI_CLI_HOME>/.gemini (polecat sets
    # GEMINI_CLI_HOME=/home/worker in-container); fall back to $HOME/.gemini.
    # Glob from the .gemini dir itself — Python's recursive `**` does NOT descend
    # into hidden directories, so rooting at the dotdir is required to reach the
    # baked plugins.
    if [ -n "$GEMINI_CLI_HOME" ]; then
        AGY_GEMINI_DIR="$GEMINI_CLI_HOME/.gemini"
    else
        AGY_GEMINI_DIR="$HOME/.gemini"
    fi
    PKB_MCP_URL="$PKB_MCP_URL" AGY_GEMINI_DIR="$AGY_GEMINI_DIR" python3 - <<'PY' || echo "WARN: failed to inject PKB_MCP_URL into agy mcp_config.json; agy pkb MCP may not connect." >&2
import glob, json, os, sys

url = os.environ["PKB_MCP_URL"]
home = os.environ["AGY_GEMINI_DIR"]
patched = 0
for path in glob.glob(f"{home}/**/mcp_config.json", recursive=True):
    try:
        data = json.loads(open(path).read())
    except (OSError, ValueError):
        continue
    pkb = data.get("mcpServers", {}).get("pkb")
    if not isinstance(pkb, dict):
        continue
    pkb.setdefault("env", {})["PKB_MCP_URL"] = url
    open(path, "w").write(json.dumps(data, indent=2) + "\n")
    print(f"Injected literal PKB_MCP_URL into {path} (mcpServers.pkb.env)", file=sys.stderr)
    patched += 1
if patched == 0:
    print("Note: no agy mcp_config.json with a pkb server found (non-agy image?).", file=sys.stderr)
PY
fi

# Execute the agent command (e.g., claude, gemini, bash).
exec "$@"
