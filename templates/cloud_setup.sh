#!/bin/bash

## Set up claude code in cloud vm. Modify as required.

set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

# 0) Accept apt release-info changes up front. The base image's ondrej/php PPA
#    renamed its Label ("PPA for PHP" -> "Use packages.sury.org/php instead"),
#    which makes every `apt-get update` hard-fail (exit 100) until accepted —
#    including the one buried inside Tailscale's install.sh. This drop-in applies
#    to ALL apt calls regardless of ordering, so it must come first.
echo 'Acquire::AllowReleaseInfoChange "true";' > /etc/apt/apt.conf.d/99allow-releaseinfo-change

# 1) Install Tailscale (binary cached; no key needed at this phase).
command -v tailscale >/dev/null 2>&1 || curl -fsSL https://tailscale.com/install.sh | sh

apt-get install -y openssh-client rsync

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
claude plugin marketplace add nicsuzor/academicOps#dist
claude plugin install aops@academicOps --config pkb_mcp_url="PKB_SERVER"
claude plugin install aops-ts@academicOps
claude plugin install aops-tools@academicOps
# env vars don't resolve this early in the boot process.
claude mcp add --transport http --scope local services "PKB_SERVER" 