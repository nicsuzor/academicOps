#!/bin/bash
# Required environment variables (set in the session env before running):
#   TS_AUTHKEY=YOUR_KEY
#   PKB_MCP_URL=YOUR_PKB

set -euo pipefail

# 1) Install Tailscale (binary cached; no key needed at this phase).
command -v tailscale >/dev/null 2>&1 || curl -fsSL https://tailscale.com/install.sh | sh

# 1) Runtime credential helper — emits the token fresh, never written to the cached snapshot
cat > /usr/local/bin/gh-token-askpass <<'EOF'
#!/bin/bash
case "$1" in
  *Username*) echo "x-access-token" ;;
  *Password*) echo "${GITHUB_TOKEN}" ;;
esac
EOF

chmod +x /usr/local/bin/gh-token-askpass

# 2) Identity rewrite with a LONGER prefix than the proxy rule (…/nicsuzor/ beats https://github.com/)
#    -> canonical github URLs for your repos resolve direct instead of via the brain-scoped proxy
git config --global url."https://github.com/nicsuzor/academicOps".insteadOf "https://github.com/nicsuzor/academicOps"
git config --global core.askPass /usr/local/bin/gh-token-askpass

# 3) Now the marketplaces in .claude/settings.json (extraKnownMarketplaces, ref: dist) can fetch.
#    Optional explicit kick if auto-registration still doesn't trigger on boot:
claude plugin marketplace add nicsuzor/academicOps#dist || true
claude plugin marketplace update academicOps || true

if [ -n "${PKB_MCP_URL:-}" ]; then
  claude plugin install pkb@academicOps --config pkb_mcp_url="${PKB_MCP_URL}"
else
  claude plugin install pkb@academicOps
fi
claude plugin install ida@academicOps
claude plugin install orchestrate@academicOps
claude plugin install rbg@academicOps
claude plugin install ts@academicOps
claude plugin install tools@academicOps
claude plugin install aops-debug@academicOps
