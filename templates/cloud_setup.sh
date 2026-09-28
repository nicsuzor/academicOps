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

# 2) Identity rewrite with a LONGER prefix than the proxy rule (…/nicsuzor/ beats https://github.com/)
#    -> canonical github URLs for your repos resolve direct instead of via the brain-scoped proxy
git config --global url."https://github.com/nicsuzor/academicOps".insteadOf "https://github.com/nicsuzor/academicOps"
git config --global core.askPass /usr/local/bin/gh-token-askpass

# 3) Now the marketplaces in .claude/settings.json (extraKnownMarketplaces, ref: dist) can fetch.
#    Optional explicit kick if auto-registration still doesn't trigger on boot:
claude plugin marketplace add nicsuzor/aops
claude plugin install ida@academicOps
claude plugin install aops-debug@academicOps
claude plugin install tools@academicOps
claude plugin install rbg@academicOps
