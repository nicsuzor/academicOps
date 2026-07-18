# --- aops dist/ source selection ---------------------------------------
# The image needs the built dist/aops-* tree + .claude-plugin/marketplace.json.
# Two interchangeable sources, selected by AOPS_DIST_SOURCE. Both land at
# /aops-dist, but nested one level differently (the published `dist` BRANCH
# publishes plugin dirs + .claude-plugin/ at its own root, while the local
# COPY below lands the checkout's dist/ under /aops-dist/dist — the
# `claude plugin marketplace add`/`update`/install RUN block below branches on
# $AOPS_DIST_SOURCE to point $MP_ROOT at the right one for each, and every
# plugin dir sits directly under $MP_ROOT in both cases):
#   remote (default) — clone the published `dist` branch. Used by CI
#     (build-extension.yml builds the image right after publishing that
#     branch, so this is exactly the release just shipped).
#   local — copy the dist/ this checkout already built (`make build-dev` /
#     scripts/build.py). Used by `make build-docker` for local dev builds, so
#     the image reflects your current source tree instead of whatever the
#     dist branch last published (which can lag current source — see #2208).
ARG AOPS_DIST_SOURCE=remote
ARG AOPS_REPO_URL=https://github.com/nicsuzor/academicOps.git
ARG AOPS_DIST_REF=dist

FROM alpine/git:latest AS aops-dist-remote
ARG AOPS_REPO_URL
ARG AOPS_DIST_REF
RUN git clone --depth 1 --branch ${AOPS_DIST_REF} ${AOPS_REPO_URL} /aops-dist

FROM scratch AS aops-dist-local
COPY dist /aops-dist/dist

FROM aops-dist-${AOPS_DIST_SOURCE} AS aops-dist

# Use Python 3.12 with Debian Bookworm slim for a minimal, compatible base
FROM python:3.12-slim-bookworm

# Re-declared: ARGs don't cross a FROM boundary. Needed below to branch the
# plugin-install step on which /aops-dist shape we actually got.
ARG AOPS_DIST_SOURCE=remote

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

# Install code quality tools globally (Claude/agy installed separately below).
# @playwright/mcp: pre-baked so agents can call playwright tools without a
# network download at session start.
RUN npm install -g markdownlint-cli2 dprint ccstatusline @playwright/mcp && npm cache clean --force

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

# Install Antigravity CLI (agy)
ARG AGY_VERSION
RUN umask 000 && curl -fsSL https://antigravity.google/cli/install.sh | bash \
    && agy --version > /home/worker/.agy-version 2>&1 \
    && cat /home/worker/.agy-version

# Install Python-based CLI tools as user (installs to ~/.local/bin)
RUN umask 000 && uv tool install ruff

# ── Install aops framework from the source selected above ─────────────
# Both CLIs install from the SAME /tmp/aops-dist tree (either the single
# shallow clone or the local dist/ copy — see AOPS_DIST_SOURCE above) so they
# always get the same commit. The previous approach used two independent
# git clones that could diverge if the repo updated between them
# (see #1384: different gate_config.py versions crashed Gemini hooks).

# Fixup script for post-install Gemini/Antigravity config (see file for why).
COPY --chown=worker:worker aops-jr/polecat/defaults/docker_gemini_fixups.py /home/worker/docker_gemini_fixups.py

# Both CLIs internally set 444 on git objects — chmod after each install.
#
# Exactly two plugins ship, for two surfaces (claude, agy): aops + aops-tools.
# The Gemini CLI extension surface is deprecated and intentionally not
# installed here (matches `make install`, which doesn't install it either).
#
# $AOPS_DIST_SOURCE picks the marketplace root (see aops-dist-local /
# aops-dist-remote above for why these differ): local's /aops-dist/dist IS
# the self-contained marketplace root build.py produces; the published `dist`
# branch has `.claude-plugin/` AND every plugin dir (aops-claude,
# aops-antigravity, ...) at its own root — see build-extension.yml's
# "Publish distribution to dist" step. Both shapes put every plugin dir
# directly under $MP_ROOT, so all COPY/install targets below are
# $MP_ROOT-relative and need no further local/remote branching.
#
# The marketplace NAME is always academicOps here, regardless of source.
# build.py's generate_local_marketplace() names the dist/ marketplace `aops`
# so a HOST `make install-dev` doesn't collide with a real `academicOps`
# release install on the same machine — but that coexistence concern doesn't
# apply inside this ephemeral image, and aops-jr/polecat/cli.py's setup_staging()
# stages `pluginConfigs` under the hardcoded key `aops@academicOps`. A local
# build that installed as `aops@aops` would silently fail to receive that
# staged config (pkb_mcp_url never reaching the plugin), so we rewrite the
# local marketplace.json's name to `academicOps` before installing, making
# local builds install under the exact same key production/CI builds use.
COPY --from=aops-dist --chown=worker:worker /aops-dist /tmp/aops-dist
RUN umask 000 \
    && MP_NAME=academicOps \
    && if [ "$AOPS_DIST_SOURCE" = "local" ]; then \
        MP_ROOT=/tmp/aops-dist/dist; \
        python3 /home/worker/docker_gemini_fixups.py fixup-local-marketplace-name --marketplace-root "$MP_ROOT" --marketplace-name "$MP_NAME"; \
    else \
        MP_ROOT=/tmp/aops-dist; \
    fi \
    && claude plugin marketplace add "$MP_ROOT" \
    && claude plugin marketplace update "$MP_NAME" \
    && claude plugin install aops@"$MP_NAME" \
    && claude plugin install aops-tools@"$MP_NAME" \
    && chmod -R a+rwX /home/worker/.claude \
    && mkdir -p /home/worker/.gemini \
    && echo '{"/home/worker/.gemini/antigravity-cli/plugins/aops": "TRUST_FOLDER", "/home/worker/.gemini/antigravity-cli/plugins/aops-tools": "TRUST_FOLDER", "/home/worker/.config": "TRUST_FOLDER"}' > /home/worker/.gemini/trustedFolders.json \
    && mkdir -p /home/worker/.gemini/antigravity-cli/plugins \
    && cp -r "$MP_ROOT"/aops-antigravity /home/worker/.gemini/antigravity-cli/plugins/aops \
    && agy plugin install /home/worker/.gemini/antigravity-cli/plugins/aops \
    && cp -r "$MP_ROOT"/aops-tools-antigravity /home/worker/.gemini/antigravity-cli/plugins/aops-tools \
    && agy plugin install /home/worker/.gemini/antigravity-cli/plugins/aops-tools \
    && chmod -R a+rwX /home/worker/.gemini \
    && python3 /home/worker/docker_gemini_fixups.py fixup-mcp-config-paths \
    && mkdir -p /home/worker/.claude/plugins/marketplaces/"$MP_NAME"/.claude-plugin \
    && cp "$MP_ROOT"/.claude-plugin/marketplace.json /home/worker/.claude/plugins/marketplaces/"$MP_NAME"/.claude-plugin/marketplace.json \
    && rm -rf /tmp/aops-dist \
    && python3 /home/worker/docker_gemini_fixups.py fixup-marketplace-cache --marketplace-name "$MP_NAME"

# NOTE: no pkb binary is installed — PKB ships as a REMOTE MCP server (aops's
# scripts/run-mcp.sh resolves PKB_MCP_URL and runs `uvx fastmcp run "$PKB_MCP_URL"`).
# The vestigial nicsuzor/mem binary download was removed with the plumbing in PR #1615.

# NOTE: Claude/Gemini hook .py sources cannot diverge (see #1384) — scripts/build.py
# copies both from the single aops/hooks source dir into every platform's dist/
# output, so a build-time diff here would only ever re-confirm what the build
# pipeline already guarantees by construction. Removed as a redundant, image-build-
# time-costly check; drift would show up as a build.py bug, not a runtime one.

# Pre-bake Python venvs for Claude plugins AND agy
# (Antigravity CLI) plugins in one pass so the first hook call always
# fast-paths to $HOOK_DIR/.venv/bin/python (router.sh fallback is `uv run`,
# which resolves the lockfile live on every cold start).
#
# Cold-start matters most for PreToolUse, which has a 5000ms timeout in
# hooks.json. An inline `uv` build on first call (fetch/resolve pydantic, etc.)
# can exceed that window and produce `Tool call denied by jsonhook__hooks_*`
# (agy) or a stalled tool call (Claude). Symmetric pre-bake here + the same
# pre-bake at `make install-{claude,agy}` time eliminates the cold-start
# failure for every client.
#
# Asymmetric pre-bake (one CLI frozen, the other JIT) is a footgun: a broken
# uv.lock ships silently on the pre-baked side while the JIT side self-heals.
# Symmetric pre-bake + smoke test catches lock drift at build time.
#
# UV_PROJECT_ENVIRONMENT is unset so each venv lives inside its own plugin/
# extension dir, independent of the root project venv at /home/worker/.venv
# (built below).
RUN umask 000 && set -e && \
    for d in /home/worker/.claude/plugins/cache/*/*/*/ \
             /home/worker/.gemini/extensions/*/ \
             /home/worker/.gemini/antigravity-cli/plugins/*/ ; do \
        if [ -f "${d}pyproject.toml" ]; then \
            (cd "$d" \
                && env -u UV_PROJECT_ENVIRONMENT uv sync --frozen \
                && ./.venv/bin/python -c "import psutil, pydantic, yaml") ; \
        fi ; \
    done

# NOTE: the build-time "agy PreToolUse-allow" regression assertion that used to
# live here (guarding aops-aa4c85a6 — a stale baked router.sh emitting {} for a
# PreToolUse ALLOW event) has been removed: aops/hooks/router.py no longer
# implements PreToolUse or any tool-gating at all (it only injects
# reminder/hydrate context on PostInvocation/PreInvocation for agy and
# Stop/SubagentStop/UserPromptSubmit for claude — see the file). That whole
# tool-allow/deny mechanism (aops-core/lib/automode.py, the gates workflow) was
# removed in the same large refactor that broke scripts/install.py. If it's
# rebuilt, a fresh build-time assertion belongs here again.

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
COPY --chown=worker:worker --chmod=666 aops-jr/polecat/defaults/ccstatusline-settings.json /home/worker/.config/ccstatusline/settings.json
COPY --chown=worker:worker --chmod=666 aops-jr/polecat/defaults/claude-settings.json /home/worker/.claude/settings.json
# Seed .claude.json with hasCompletedOnboarding so headless workers authenticated
# via CLAUDE_CODE_OAUTH_TOKEN skip the interactive theme/login prompts. The
# env-only auth model (aops-jr/polecat/cli.py:_require_claude_oauth_or_exit) stages no
# files, so without this seed claude regenerates a minimal .claude.json that
# triggers onboarding even when the token is set.
COPY --chown=worker:worker --chmod=666 aops-jr/polecat/defaults/claude-config.json /home/worker/.claude.json

# Seed agy's (Antigravity CLI) onboarding-complete marker so headless/crew
# workers skip its interactive first-run wizard (theme picker → migration →
# Terms-of-Service / data-collection consent). agy v1.0.13 introduced this
# wizard and gates it on ~/.gemini/antigravity-cli/cache/onboarding.json; the
# autonomous worker (interactive `agy -i`) cannot complete the TUI and never
# reaches a prompt (regression aops-d9cc656a, verified 2026-06-29). This is the
# agy analog of the Claude `hasCompletedOnboarding` seed above. Pre-create the
# cache dir so BuildKit doesn't auto-create it 0644 (non-traversable).
RUN umask 000 && mkdir -p /home/worker/.gemini/antigravity-cli/cache
COPY --chown=worker:worker --chmod=666 aops-jr/polecat/defaults/agy-onboarding.json /home/worker/.gemini/antigravity-cli/cache/onboarding.json

# Install Rust toolchain (nothing in this image's build needs cargo/rustc —
# it's provided for agents that use it at runtime). Deliberately placed this
# late, after the aops framework clone/install and all the uv-sync venv
# pre-bakes above: those are the expensive layers, and Docker's cache
# invalidates every layer AFTER the first one that misses. RUST_CACHEBUST
# only invalidates this layer and the (cheap) ones below it, so a forced
# rustup refresh no longer forces a re-clone + re-install of the whole
# framework and a re-sync of every plugin venv.
# RUST_CACHEBUST is intentionally unused in the RUN command — it only
# invalidates this layer so rebuilds can fetch the latest Rust toolchain.
ARG RUST_CACHEBUST
RUN umask 000 && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --no-modify-path --profile minimal

# Copy entrypoint script
COPY --chown=worker:worker --chmod=777 aops-jr/polecat/entrypoint.sh /home/worker/entrypoint.sh

# Make home dir itself traversable/writable for any UID — polecat crew runs
# containers as the host UID (non-root), which may differ from worker UID 1000.
# Everything *under* /home/worker is already world-writable thanks to umask 000
# in each install RUN above plus the targeted chmods for git-cloned trees, so
# no recursive walk is needed here.
RUN chmod 777 /home/worker

# Default command and entrypoint
ENTRYPOINT ["/home/worker/entrypoint.sh"]
CMD ["/bin/bash"]
