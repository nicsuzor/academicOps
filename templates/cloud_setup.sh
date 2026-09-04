#!/bin/bash

## Set up claude code in cloud vm. Modify as required.

set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

PKB_SERVER=""
EMAIL_SERVER=""

# 0) Accept apt release-info changes up front. The base image's ondrej/php PPA
#    renamed its Label ("PPA for PHP" -> "Use packages.sury.org/php instead"),
#    which makes every `apt-get update` hard-fail (exit 100) until accepted —
#    including the one buried inside Tailscale's install.sh. This drop-in applies
#    to ALL apt calls regardless of ordering, so it must come first.
echo 'Acquire::AllowReleaseInfoChange "true";' > /etc/apt/apt.conf.d/99allow-releaseinfo-change

# 1) Install Tailscale (binary cached; no key needed at this phase).
#    install.sh runs its own `apt-get install`, which has hit transient 503s
#    against pkgs.tailscale.com — retry before giving up, since the mcp
#    endpoints below need the tailnet up anyway.
if ! command -v tailscale >/dev/null 2>&1; then
  attempt=1
  until curl -fsSL https://tailscale.com/install.sh | sh; do
    if [ "$attempt" -ge 5 ]; then
      echo "tailscale install failed after $attempt attempts" >&2
      exit 1
    fi
    echo "tailscale install attempt $attempt failed, retrying in 10s..." >&2
    sleep 10
    attempt=$((attempt + 1))
  done
fi

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
#claude plugin install james@academicOps
claude plugin install pkb@academicOps
claude plugin install ts@academicOps
claude plugin install tools@academicOps
claude plugin install ida@academicOps
claude plugin install rbg@academicOps

# env vars don't resolve this early in the boot process, declare them above.
claude mcp add --transport http --scope local services ${PKB_SERVER}
claude mcp add --transport http --scope local email ${EMAIL_SERVER}