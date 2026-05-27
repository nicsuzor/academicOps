# Use Python 3.12 with Debian Bookworm slim for a minimal, compatible base
FROM python:3.12-slim-bookworm

# Create non-root user early so we can switch to it after system-level installs
RUN useradd -m -d /home/worker -s /bin/bash worker

# Set environment variables — HOME stays as /root during root-level installs
# to avoid polluting /home/worker with root-owned files. Switched after USER.
ENV ACA_DATA=/data \
    AOPS=/app \
    HOSTNAME=aops-crew \
    UV_INSTALL_DIR=/usr/local/bin \
    PYTHONUNBUFFERED=1 \
    NODE_VERSION=22

# ── Root-only: system packages and global tooling ──────────────────────

# Install system dependencies (including Node.js for Claude/Gemini CLIs, GitHub CLI, Docker CLI).
# openssh-client (~5MB) lets workers ssh into other hosts (services-new, dev3, etc.) for
# ops debugging — inspecting docker/cron state, collecting evidence. No keys or known_hosts
# are baked into the image: keys are mounted at runtime (or forwarded via SSH agent), and
# host fingerprints are accepted via TOFU on first connection. Do NOT add bare keys here.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    build-essential \
    gnupg \
    cron \
    procps \
    ca-certificates \
    openssh-client \
    && curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash - \
    && apt-get install -y nodejs \
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | gpg --dearmor -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/docker-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian bookworm stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y gh docker-ce-cli \
    ripgrep fd-find bat jq less tree \
    && apt-get clean && rm -rf /var/lib/apt/lists/* \
    && ln -s /usr/bin/fdfind /usr/local/bin/fd \
    && ln -s /usr/bin/batcat /usr/local/bin/bat

# Pre-install Playwright's Chromium browser and its system dependencies.
# Marsha and other workers run browser verification via `playwright`; without
# this, each container has to run `npx playwright install-deps` at runtime —
# slow, often fails offline, and needs sudo under the `worker` user.
#
# `install-deps` auto-detects the distro and runs `apt-get install -y` for the
# chromium-required packages (libnss3, libatk-1.0, libcups2, fonts, ...). Must
# run as root (we still are here) before the USER switch further down.
# `playwright install chromium` downloads the browser binaries. We set
# PLAYWRIGHT_BROWSERS_PATH=/ms-playwright (system-wide) before the install so
# the binaries land in a location the unprivileged `worker` user can read at
# runtime. The env var stays set for all subsequent stages and containers.
#
# The MCP playwright server creates per-session cache subdirs (mcp-chrome-*)
# under this path at runtime, so it must be writable by any UID — polecat
# crew containers run as the host UID, which may not match worker. Use the
# same 777 pattern as /home/worker below.
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN npx --yes playwright@1.59.1 install-deps chromium \
    && npx --yes playwright@1.59.1 install chromium \
    && chmod -R a+rwX /ms-playwright \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install uv system-wide (standard for aops framework per P#93)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Gemini CLI and code quality tools globally (Claude installed separately below).
# @playwright/mcp: pre-baked so Gemini agents can call playwright tools without a
# network download at session start. The aops-core Gemini extension registers it as
# an MCP server in templates/aops-core.gemini-extension.json.
RUN npm install -g @google/gemini-cli markdownlint-cli2 dprint ccstatusline @playwright/mcp && npm cache clean --force

# Create data and workspace directories, hand ownership to worker
RUN mkdir -p /data /workspace && chown worker:worker /data /workspace

# ── Switch to non-root user for all remaining operations ───────────────

USER worker

# Now set HOME and PATH for the worker user
ENV HOME=/home/worker \
    PATH="/home/worker/.local/bin:/home/worker/.cargo/bin:$PATH"

# Install Claude Code via native installer — npm package lacks the full binary
# and causes .claude.json config migration issues on startup.
# CLAUDE_CODE_VERSION busts the Docker layer cache so rebuilds pick up the latest.
# Pass --build-arg CLAUDE_CODE_VERSION=x.y.z to pin, or leave empty to get latest.
ARG CLAUDE_CODE_VERSION
RUN umask 000 && curl -fsSL https://claude.ai/install.sh | bash \
    && claude --version > /home/worker/.claude-code-version 2>&1 \
    && cat /home/worker/.claude-code-version

# RUST_CACHEBUST is intentionally unused in the RUN command — it only invalidates
# this layer so rebuilds always fetch the latest Rust toolchain from rustup.
ARG RUST_CACHEBUST
RUN umask 000 && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --no-modify-path --profile minimal

# Install Python-based CLI tools as user (installs to ~/.local/bin)
RUN umask 000 && uv tool install ruff

# ── Install aops framework from GitHub ────────────────────────────────
# Both CLIs install from a SINGLE shallow clone of the dist repo so they
# always get the same commit. The previous approach used two independent
# git clones that could diverge if the repo updated between them
# (see #1384: different gate_config.py versions crashed Gemini hooks).
# pkb binary: downloaded separately from nicsuzor/mem releases.
ARG AOPS_REPO_URL=https://github.com/nicsuzor/aops.git

# Single clone → install both Claude plugin and Gemini extension from it.
# Both CLIs internally set 444 on git objects — chmod after each install.
RUN umask 000 && git clone --depth 1 ${AOPS_REPO_URL} /tmp/aops-dist \
    && claude plugin marketplace add /tmp/aops-dist \
    && claude plugin marketplace update academicOps \
    && claude plugin install aops-core@academicOps \
    && claude plugin install aops-tools@academicOps \
    && chmod -R a+rwX /home/worker/.claude \
    && mkdir -p /home/worker/.gemini \
    && echo '{"/tmp/aops-dist/aops-gemini": "TRUST_FOLDER", "/tmp/aops-dist/aops-tools-gemini": "TRUST_FOLDER", "/home/worker/.gemini/extensions/aops-core": "TRUST_FOLDER", "/home/worker/.gemini/extensions/aops-tools": "TRUST_FOLDER", "/home/worker/.config": "TRUST_FOLDER"}' > /home/worker/.gemini/trustedFolders.json \
    && GEMINI_API_KEY=dummy-for-install gemini extensions install /tmp/aops-dist/aops-gemini --consent --pre-release \
    && GEMINI_API_KEY=dummy-for-install gemini extensions install /tmp/aops-dist/aops-tools-gemini --consent --pre-release \
    && chmod -R a+rwX /home/worker/.gemini \
    && mkdir -p /home/worker/.claude/plugins/cache/academicOps/.claude-plugin \
    && cp /tmp/aops-dist/.claude-plugin/marketplace.json /home/worker/.claude/plugins/cache/academicOps/.claude-plugin/marketplace.json \
    && rm -rf /tmp/aops-dist \
    && python3 -c "import json, pathlib; \
cache = pathlib.Path('/home/worker/.claude/plugins/cache/academicOps'); \
km = pathlib.Path('/home/worker/.claude/plugins/known_marketplaces.json'); \
d = json.loads(km.read_text()); \
d['academicOps']['source']['path'] = str(cache); \
d['academicOps']['installLocation'] = str(cache); \
km.write_text(json.dumps(d, indent=2)); \
mp = cache / '.claude-plugin' / 'marketplace.json'; \
m = json.loads(mp.read_text()); \
for p in m.get('plugins', []): p_dir = cache / p['name']; p.update({'source': './' + p['name'] + '/' + next((d.name for d in p_dir.iterdir() if d.is_dir()), '')}) if p_dir.is_dir() else None; \
mp.write_text(json.dumps(m, indent=2))"

# Install pkb binary from nicsuzor/mem releases.
# Uses /releases list (not /latest) so empty releases with no uploaded assets are skipped.
RUN umask 000 && TMPDIR=$(mktemp -d) \
    && PLATFORM="x86_64-linux" \
    && MEM_TAG=$(curl -s https://api.github.com/repos/nicsuzor/mem/releases \
         | jq -r '[.[] | select(.assets | map(select(.name | endswith("'"${PLATFORM}"'.tar.gz"))) | length > 0)][0].tag_name') \
    && curl -fsSL "https://github.com/nicsuzor/mem/releases/download/${MEM_TAG}/mem-${MEM_TAG}-${PLATFORM}.tar.gz" \
         -o "${TMPDIR}/mem.tar.gz" \
    && tar xzf "${TMPDIR}/mem.tar.gz" -C "${TMPDIR}" \
    && cp "${TMPDIR}/pkb" "$HOME/.local/bin/pkb" \
    && chmod +x "$HOME/.local/bin/pkb" \
    && rm -rf "${TMPDIR}"

# Set permissive extension enablement so hooks fire for any workspace path.
# `gemini extensions install` restricts to /home/<user>/* which doesn't match
# mounted worktrees (e.g. /workspace, /data, or deeply nested crew paths).
RUN umask 000 && if [ -f /home/worker/.gemini/extensions/extension-enablement.json ]; then \
    python3 -c "import json, pathlib; \
p = pathlib.Path('/home/worker/.gemini/extensions/extension-enablement.json'); \
d = json.loads(p.read_text()); \
[d.__setitem__(k, {**v, 'overrides': ['*']}) for k, v in d.items()]; \
p.write_text(json.dumps(d, indent=2))" ; \
    fi

# Build-time version check: fail if Claude and Gemini hook Python sources
# diverge. hooks.json and router.sh differ by design (platform-specific event
# names and path variables), but .py files must be identical (see #1384).
RUN set -e; \
    CLAUDE_HOOKS=$(ls -d /home/worker/.claude/plugins/cache/academicOps/aops-core/*/hooks 2>/dev/null | head -1); \
    GEMINI_HOOKS=/home/worker/.gemini/extensions/aops-core/hooks; \
    if [ -z "$CLAUDE_HOOKS" ] || [ ! -d "$GEMINI_HOOKS" ]; then \
        echo "FATAL: Could not find hook directories for comparison"; exit 1; \
    fi; \
    cd "$CLAUDE_HOOKS"; \
    for f in *.py; do \
        [ -f "$f" ] || continue; \
        diff -q "$CLAUDE_HOOKS/$f" "$GEMINI_HOOKS/$f" >/dev/null 2>&1 || \
        { echo "FATAL: hooks/$f differs between Claude plugin and Gemini extension (see #1384)"; \
          diff "$CLAUDE_HOOKS/$f" "$GEMINI_HOOKS/$f" || true; exit 1; }; \
    done; \
    echo "Build check passed: hook Python sources match between Claude and Gemini"

# Pre-bake Python venvs for BOTH Claude plugins and Gemini extensions in one
# pass so the BeforeAgent hook always fast-paths to $HOOK_DIR/.venv/bin/python
# (router.sh fallback is `uv run`, which resolves the lockfile live on every
# cold start).
#
# Asymmetric pre-bake (one CLI frozen, the other JIT) is a footgun: a broken
# uv.lock ships silently on the pre-baked side while the JIT side self-heals.
# Symmetric pre-bake + smoke test catches lock drift at build time.
#
# UV_PROJECT_ENVIRONMENT is unset so each venv lives inside its own plugin/
# extension dir, independent of the root project venv at /home/worker/.venv
# (built below).
RUN umask 000 && set -e && \
    for d in /home/worker/.claude/plugins/cache/academicOps/*/*/ \
             /home/worker/.gemini/extensions/*/ ; do \
        if [ -f "${d}pyproject.toml" ]; then \
            (cd "$d" \
                && env -u UV_PROJECT_ENVIRONMENT uv sync --frozen \
                && ./.venv/bin/python -c "import psutil, pydantic, yaml") ; \
        fi ; \
    done

# Pre-build Python project venv at a stable image path.
# UV_PROJECT_ENVIRONMENT redirects uv away from the bind-mounted source dir (/workspace),
# preventing shebang conflicts (venv scripts baked with /home/worker paths, not /workspace)
# and eliminating per-container reinstalls on startup.
# Layer cache: only invalidates when pyproject.toml or uv.lock changes — all expensive
# installs above stay cached across dep bumps.
# --extra dev: includes pre-commit and dprint-py needed for git commit hooks in the container.
ENV UV_PROJECT_ENVIRONMENT=/home/worker/.venv
COPY --chown=worker:worker pyproject.toml uv.lock /tmp/aops-deps/
RUN umask 000 && cd /tmp/aops-deps && uv sync --frozen --no-install-project --group dev

# Install default ccstatusline and Claude Code settings.
# These defaults are overridden at runtime if the host stages replacements.
# Pre-create .config so Docker COPY doesn't auto-create it — BuildKit applies
# --chmod to auto-created intermediate dirs, producing 0644 (non-traversable)
# via umask: 666 & ~022 = 644. Pre-existing dirs are left untouched by COPY.
RUN umask 000 && mkdir -p /home/worker/.config/ccstatusline
COPY --chown=worker:worker --chmod=666 polecat/defaults/ccstatusline-settings.json /home/worker/.config/ccstatusline/settings.json
COPY --chown=worker:worker --chmod=666 polecat/defaults/claude-settings.json /home/worker/.claude/settings.json
# Seed .claude.json with hasCompletedOnboarding so headless workers authenticated
# via CLAUDE_CODE_OAUTH_TOKEN skip the interactive theme/login prompts. The
# env-only auth model (polecat/cli.py:_require_claude_oauth_or_exit) stages no
# files, so without this seed claude regenerates a minimal .claude.json that
# triggers onboarding even when the token is set.
COPY --chown=worker:worker --chmod=666 polecat/defaults/claude-config.json /home/worker/.claude.json

# Copy entrypoint script
COPY --chown=worker:worker --chmod=777 polecat/entrypoint.sh /home/worker/entrypoint.sh

# Make home dir itself traversable/writable for any UID — polecat crew runs
# containers as the host UID (non-root), which may differ from worker UID 1000.
# Everything *under* /home/worker is already world-writable thanks to umask 000
# in each install RUN above plus the targeted chmods for git-cloned trees, so
# no recursive walk is needed here.
RUN chmod 777 /home/worker

# Default command and entrypoint
ENTRYPOINT ["/home/worker/entrypoint.sh"]
CMD ["/bin/bash"]
