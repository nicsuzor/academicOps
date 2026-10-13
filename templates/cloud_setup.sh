#!/bin/bash

## Set up claude code in cloud vm. Modify as required.

set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

export no_proxy="${no_proxy:+$no_proxy,}ts.net,.ts.net"
export NO_PROXY="$no_proxy"

#apt-get update && apt-get install -y openssh-client rsync

# 1) Runtime credential helper — emits the token fresh, never written to the cached snapshot
cat > /usr/local/bin/gh-token-askpass <<'EOF'
#!/bin/bash
case "$1" in
  *Username*) echo "x-access-token" ;;
  *Password*) echo "${GITHUB_TOKEN}" ;;
esac
EOF

chmod +x /usr/local/bin/gh-token-askpass

# 2) Identity rewrite with a LONGER prefix than the proxy rule (…/<owner>/<repo> beats https://github.com/)
#    -> canonical github URLs for your repos resolve direct instead of via the repository-scoped proxy
git config --global url."https://github.com/nicsuzor/academicOps".insteadOf "https://github.com/nicsuzor/academicOps"
git config --global core.askPass /usr/local/bin/gh-token-askpass

# 3) Now the marketplaces in .claude/settings.json (extraKnownMarketplaces, ref: dist) can fetch.
#    Optional explicit kick if auto-registration still doesn't trigger on boot:
claude plugin marketplace add nicsuzor/aops
claude plugin install ida@academicOps
claude plugin install aops-debug@academicOps
claude plugin install tools@academicOps
claude plugin install rbg@academicOps

# 4) Auto-mode trust rules as a managed-settings drop-in (the classifier ignores
#    autoMode in repo settings). Set CLAUDE_AUTO_MODE_SETTINGS_REPO (a git URL)
#    and CLAUDE_AUTO_MODE_SETTINGS_PATH (a settings JSON in that repo holding an
#    autoMode block). The repo is fetched with git, the same direct route and
#    askPass token as step 2.
if [ -n "${CLAUDE_AUTO_MODE_SETTINGS_REPO:-}" ]; then
  git config --global url."$CLAUDE_AUTO_MODE_SETTINGS_REPO".insteadOf "$CLAUDE_AUTO_MODE_SETTINGS_REPO"
  auto_mode_repo="$(mktemp -d)"
  auto_mode_json="$(mktemp)"
  git clone --quiet --depth 1 --no-checkout --filter=blob:none \
    "$CLAUDE_AUTO_MODE_SETTINGS_REPO" "$auto_mode_repo"
  git -C "$auto_mode_repo" show "HEAD:${CLAUDE_AUTO_MODE_SETTINGS_PATH:?CLAUDE_AUTO_MODE_SETTINGS_PATH unset}" > "$auto_mode_json"
  python3 -c 'import json, sys; assert "autoMode" in json.load(open(sys.argv[1])), "no autoMode block"' "$auto_mode_json"
  install -d -m 0755 /etc/claude-code/managed-settings.d
  install -m 0644 "$auto_mode_json" /etc/claude-code/managed-settings.d/auto-mode.json
  rm -rf "$auto_mode_repo" "$auto_mode_json"
fi
