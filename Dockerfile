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
#   local — copy the dist/ this checkout already built (`make build` /
#     build/build.py). Used by `make docker-build` for local dev builds, so
#     the image reflects your current source tree instead of whatever the
#     dist branch last published (which can lag current source — see #2208).
ARG AOPS_DIST_SOURCE=remote
ARG AOPS_REPO_URL
ARG AOPS_DIST_REF

FROM alpine/git:latest AS aops-dist-remote
ARG AOPS_REPO_URL
ARG AOPS_DIST_REF
# No default repository and no default branch: both name an installation, not
# this code. A remote build states them or fails here.
RUN [ -n "${AOPS_REPO_URL}" ] || { echo "FATAL: AOPS_DIST_SOURCE=remote requires --build-arg AOPS_REPO_URL. There is no default." >&2; exit 1; } \
    && [ -n "${AOPS_DIST_REF}" ] || { echo "FATAL: AOPS_DIST_SOURCE=remote requires --build-arg AOPS_DIST_REF. There is no default." >&2; exit 1; } \
    && git clone --depth 1 --branch "${AOPS_DIST_REF}" "${AOPS_REPO_URL}" /aops-dist

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
    && GO_ARCH=$(dpkg --print-architecture) \
    && curl -fsSL "https://go.dev/dl/go1.24.0.linux-${GO_ARCH}.tar.gz" | tar -C /usr/local -xz \
    && ln -s /usr/local/go/bin/* /usr/local/bin/ \
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

# Install rtk (Rust Token Killer) — the token-optimizing CLI proxy documented
# in ~/.claude/RTK.md on the host. The binary alone is inert: the savings
# come from the PreToolUse hook (`rtk hook claude`, installed for the worker
# user further down, after the plugin-install step writes the rest of
# settings.json) that rewrites commands in place before execution.
#
# Ships as the static musl build, not the .deb the host uses: the .deb
# Depends: libc6 (>= 2.39), but this image's base (python:3.12-slim-bookworm)
# ships glibc 2.36 — confirmed by hand: `dpkg -i` half-installs and the
# resulting binary fails at runtime with "GLIBC_2.39 not found". The musl
# build has no glibc dependency at all (`ldd` reports "statically linked")
# and runs identically here. Same amd64 arch as the host binary either way —
# this image is linux/amd64, and a host binary of the wrong arch would not be
# portable, but the musl tarball is fetched fresh from the same GitHub
# release the host's .deb came from, not copied off the host, so arch is
# whatever this build targets.
#
# Version pinned to match what's on the host (`dpkg -l rtk` on nicwin,
# 2026-08-13: 0.43.0-1). Bump deliberately via --build-arg RTK_VERSION, not
# by fetching "latest" — an unpinned hook that changes rewrite behavior under
# a worker mid-flight is worse than a stale one.
ARG RTK_VERSION=0.43.0
RUN RTK_URL="https://github.com/rtk-ai/rtk/releases/download/v${RTK_VERSION}/rtk-x86_64-unknown-linux-musl.tar.gz" \
    && curl -fsSL -o /tmp/rtk.tar.gz "$RTK_URL" \
    && tar -xzf /tmp/rtk.tar.gz -C /tmp \
    && install -m 755 /tmp/rtk /usr/local/bin/rtk \
    && rm -rf /tmp/rtk.tar.gz /tmp/rtk \
    && rtk --version

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

# Third-party imports the shipped plugin trees need from the system python3.
# `python3 ${CLAUDE_PLUGIN_ROOT}/polecat/cli.py` (the dispatch skill's documented
# invocation) imports click and yaml, and the dist trees ship no pyproject.toml,
# so there is no per-plugin venv to fall back on. The shipped hooks are
# stdlib-only and need nothing here.
RUN pip install --no-cache-dir click pyyaml \
    && python3 -c "import click, yaml"

# Install code quality tools globally (Claude/agy installed separately below).
# @playwright/mcp: pre-baked so agents can call playwright tools without a
# network download at session start.
RUN npm install -g markdownlint-cli2 dprint ccstatusline @playwright/mcp && npm cache clean --force

# Create data and workspace directories. World-writable/traversable rather
# than chown'd to worker: polecat crew containers run as the invoking host
# UID (`docker run -u $(id -u):$(id -g)`, lib/polecat/cli.py), which
# is worker's UID 1000 only by coincidence on a given host. A plain chown
# leaves any other UID unable to write /data (e.g. cope/rbg's layer-3 rules
# mount lands under here), silently and only on someone else's machine. Same
# pattern as the /home/worker chmod below — world-writable inside one
# container's own filesystem is not a container-isolation weakening; each
# container's filesystem is still exclusive to that container.
RUN mkdir -p /data /workspace && chmod 777 /data /workspace

# ── Switch to non-root user for all remaining operations ───────────────

USER worker

# Now set HOME and PATH for the worker user
ENV HOME=/home/worker \
    PATH="/home/worker/go/bin:/usr/local/go/bin:/home/worker/.local/bin:/home/worker/.cargo/bin:$PATH" \
    ANTIGRAVITY_ENABLE_TELEMETRY=1 \
    CLAUDE_CODE_ENABLE_TELEMETRY=1 \
    CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1 \
    ENABLE_BETA_TRACING_DETAILED=1 \
    OTEL_METRICS_EXPORTER=otlp \
    OTEL_LOGS_EXPORTER=otlp \
    OTEL_TRACES_EXPORTER=otlp \
    OTEL_EXPORTER_OTLP_PROTOCOL=grpc \
    OTEL_LOG_USER_PROMPTS=1 \
    OTEL_LOG_ASSISTANT_RESPONSES=1 \
    OTEL_LOG_TOOL_DETAILS=1 \
    OTEL_LOG_TOOL_CONTENT=1

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

# Install agystatusline for agy status line
RUN umask 000 && go install github.com/yuys13/agystatusline@latest

# ── Layer ordering from here down ──────────────────────────────────────
# Docker invalidates every layer AFTER the first cache miss, so the layers
# below are ordered by how often their inputs change:
#   1. toolchain installs that depend on nothing in the tree (rustup)
#   2. the project venv, keyed on pyproject.toml + uv.lock (dep bumps only)
#   3. the aops dist copy + plugin install, which changes on EVERY local
#      build because `make docker-build` rebuilds dist/ first
#   4. static config files and the entrypoint
# Anything expensive that sits below (3) is re-run AND re-exported on every
# single local rebuild even though none of its inputs moved.

# Install Rust toolchain (nothing in this image's build needs cargo/rustc —
# it's provided for agents that use it at runtime). It depends on nothing in
# the tree, so it belongs above the dist copy: parked below it, this ~16s
# install plus a fresh multi-hundred-MB toolchain export ran on every build.
# It stays below the ARG-busted claude/agy installs so a RUST_CACHEBUST bump
# invalidates as little as possible above it.
# RUST_CACHEBUST is intentionally unused in the RUN command — it only
# invalidates this layer so rebuilds can fetch the latest Rust toolchain.
ARG RUST_CACHEBUST
RUN umask 000 && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --no-modify-path --profile minimal

# Pre-build Python project venv at a stable image path.
# UV_PROJECT_ENVIRONMENT redirects uv away from the bind-mounted source dir (/workspace),
# preventing shebang conflicts (venv scripts baked with /home/worker paths, not /workspace)
# and eliminating per-container reinstalls on startup.
# --group dev: includes pre-commit and dprint-py needed for git commit hooks in the container.
# Keyed only on pyproject.toml + uv.lock, so it survives every build that
# only touched dist/ — the reason it sits above the dist copy rather than
# below it, where this ~20s sync re-ran and re-exported every time.
ENV UV_PROJECT_ENVIRONMENT=/home/worker/.venv
COPY --chown=worker:worker pyproject.toml uv.lock /tmp/aops-deps/
RUN umask 000 && cd /tmp/aops-deps && uv sync --frozen --no-install-project --group dev

# No pkb binary is installed: PKB is a REMOTE MCP server. The pkb plugin's
# scripts/run-mcp.sh resolves PKB_MCP_URL from the environment and runs
# `uvx fastmcp run "$PKB_MCP_URL"`. No URL is baked into this image.
#
# Warm uv's cache with that command's dependencies. Cold, `uvx --from
# fastmcp-slim[server]` resolves and downloads 67 packages on first use, which
# runs past the window a client waits for an MCP server to hand back its tool
# list — the server is left starting, no tools are declared, and the agent
# reports the MCP server as unavailable rather than as slow. Resolving them at
# build time makes the runtime start a cache hit. No URL is involved.
RUN uvx --from 'fastmcp-slim[server]' fastmcp --version

# Pre-create every dir the --chmod'd config COPYs below land in, in one
# layer. Without this BuildKit auto-creates the intermediate dirs and applies
# the COPY's --chmod to them, producing 0644 (non-traversable) via umask:
# 666 & ~022 = 644. Pre-existing dirs are left untouched by COPY. Batched
# here because none of these depend on anything below.
RUN umask 000 && mkdir -p /home/worker/.claude \
    /home/worker/.config/ccstatusline \
    /home/worker/.config/agystatusline \
    /home/worker/.gemini/antigravity-cli/cache

# ── Install aops framework from the source selected above ─────────────
# Both CLIs install from the SAME /tmp/aops-dist tree (either the single
# shallow clone or the local dist/ copy — see AOPS_DIST_SOURCE above) so they
# always get the same commit. The previous approach used two independent
# git clones that could diverge if the repo updated between them
# (see #1384: different gate_config.py versions crashed Gemini hooks).

# Fixup script for post-install Gemini/Antigravity config (see file for why).
COPY --chown=worker:worker lib/polecat/defaults/docker_gemini_fixups.py /home/worker/docker_gemini_fixups.py

# Both CLIs internally set 444 on git objects — chmod after each install.
#
# WHICH plugins install is read from the marketplace manifest shipped in the
# dist tree, which build/marketplace.py renders from build/marketplace.toml —
# the single source of truth for the plugin set (specs/ARCHITECTURE.md's plugin
# table). Every declared plugin except `ida` installs — polecat containers run
# autonomous worker agents, so `ida` (the interactive face) is explicitly not
# installed for either agy or claude.
#
# The Gemini CLI extension surface is deprecated and intentionally not
# installed here (matches `make install`, which doesn't install it either).
#
# $AOPS_DIST_SOURCE picks the marketplace root (see aops-dist-local /
# aops-dist-remote above for why these differ): local's /aops-dist/dist IS
# the self-contained marketplace root build/build.py produces; the published
# `dist` branch has `.claude-plugin/` AND every plugin dir (aops-claude,
# aops-agy, ...) at its own root — see build-extension.yml's
# "Publish distribution to dist" step. Both shapes put every plugin dir
# directly under $MP_ROOT, so all COPY/install targets below are
# $MP_ROOT-relative and need no further local/remote branching. Each plugin's
# per-client build dir is <name>-claude / <name>-agy.
#
# The marketplace NAME is always academicOps here, regardless of source.
# build/marketplace.py's generate_local_marketplace() names the dist/
# marketplace `aops` so a HOST `make install-dev` doesn't collide with a real
# `academicOps` release install on the same machine — but that coexistence
# concern doesn't apply inside this ephemeral image, and
# lib/polecat/cli.py's setup_staging() stages `pluginConfigs` under the
# key `aops-pkb@academicOps`. A local build that installed as `aops-pkb@aops` would
# silently fail to receive that staged config (pkb_mcp_url never reaching the
# plugin), so we rewrite the local marketplace.json's name to `academicOps`
# before installing, making local builds install under the exact same key
# production/CI builds use.
#
# `enabledPlugins` in ~/.claude/settings.json is generated from the same list:
# installing a plugin does not activate it, and a hand-maintained list here
# would silently drift from what shipped. `extraKnownMarketplaces` is dropped
# in the same pass — `marketplace add` records the build-time $MP_ROOT there,
# a path deleted before this layer ends. The marketplace's durable registration
# is known_marketplaces.json, repointed by fixup-marketplace-cache below.
COPY --from=aops-dist --chown=worker:worker /aops-dist /tmp/aops-dist
RUN umask 000 \
    && MP_NAME=academicOps \
    && if [ "$AOPS_DIST_SOURCE" = "local" ]; then \
        MP_ROOT=/tmp/aops-dist/dist; \
        python3 /home/worker/docker_gemini_fixups.py fixup-local-marketplace-name --marketplace-root "$MP_ROOT" --marketplace-name "$MP_NAME"; \
    else \
        MP_ROOT=/tmp/aops-dist; \
    fi \
    && PLUGINS="$(jq -r '.plugins[].name | select(. != "ida")' "$MP_ROOT/.claude-plugin/marketplace.json")" \
    && { [ -n "$PLUGINS" ] || { echo "FATAL: no plugins declared in $MP_ROOT/.claude-plugin/marketplace.json" >&2; exit 1; }; } \
    && echo "Installing plugins: $(echo $PLUGINS)" \
    && claude plugin marketplace add "$MP_ROOT" \
    && claude plugin marketplace update "$MP_NAME" \
    && for p in $PLUGINS; do claude plugin install "$p@$MP_NAME"; done \
    && { [ -f /home/worker/.claude/settings.json ] || echo '{}' > /home/worker/.claude/settings.json; } \
    && jq --arg mp "$MP_NAME" --arg plugins "$PLUGINS" \
        '.enabledPlugins = ($plugins | split("\n") | map(select(length > 0)) | map({key: (. + "@" + $mp), value: true}) | from_entries) | del(.extraKnownMarketplaces)' \
        /home/worker/.claude/settings.json > /tmp/settings.json \
    && mv /tmp/settings.json /home/worker/.claude/settings.json \
    && chmod -R a+rwX /home/worker/.claude \
    && jq -n --arg plugins "$PLUGINS" \
        '($plugins | split("\n") | map(select(length > 0)) | map({key: ("/home/worker/.gemini/config/plugins/" + .), value: "TRUST_FOLDER"}) | from_entries) + {"/home/worker/.config": "TRUST_FOLDER"}' \
        > /home/worker/.gemini/trustedFolders.json \
    && mkdir -p /home/worker/.gemini/antigravity-cli/plugins \
    && for p in $PLUGINS; do \
        src="$MP_ROOT/$p-agy"; \
        { [ -d "$src" ] || { echo "FATAL: $p is declared in the marketplace but has no agy build at $src" >&2; exit 1; }; } \
        && agy plugin install "$src"; \
    done \
    && chmod -R a+rwX /home/worker/.gemini \
    && python3 /home/worker/docker_gemini_fixups.py fixup-mcp-config-paths \
    && mkdir -p /home/worker/.claude/plugins/marketplaces/"$MP_NAME"/.claude-plugin \
    && cp "$MP_ROOT"/.claude-plugin/marketplace.json /home/worker/.claude/plugins/marketplaces/"$MP_NAME"/.claude-plugin/marketplace.json \
    # keep for now && rm -rf /tmp/aops-dist \
    && python3 /home/worker/docker_gemini_fixups.py fixup-marketplace-cache --marketplace-name "$MP_NAME"

# Register the rtk PreToolUse hook in the worker's settings.json — this is
# the half of rtk that actually delivers token savings (see the rtk install
# above). Run rtk's own installer rather than hand-writing the JSON: it
# merges into the existing file (preserving enabledPlugins written
# above it) instead of overwriting it, which is exactly how the hook got into
# ~/.claude/settings.json on the host (`rtk init --global --agent claude`,
# verified by diffing the host's settings.json against a fresh --dry-run of
# this same command). --hook-only skips writing RTK.md (its meta-commands
# doc) into the image; --auto-patch skips the interactive confirmation this
# non-interactive build can't answer. Must run after the plugin-install block
# above, which creates settings.json and writes enabledPlugins via
# jq — running rtk init before that would have its hook clobbered.
RUN umask 000 \
    && rtk init --global --agent claude --auto-patch --hook-only \
    && rm -f /home/worker/.claude/settings.json.bak \
    && jq -e '.hooks.PreToolUse[0].hooks[0].command == "rtk hook claude"' /home/worker/.claude/settings.json >/dev/null \
    && chmod -R a+rwX /home/worker/.claude

# No pkb binary is installed: PKB is a REMOTE MCP server. The pkb plugin's
# scripts/run-mcp.sh resolves PKB_MCP_URL from the environment and runs
# `uvx fastmcp run "$PKB_MCP_URL"`. No URL is baked into this image.
#
# Warm uv's cache with that command's dependencies. Cold, `uvx --from
# fastmcp-slim[server]` resolves and downloads 67 packages on first use, which
# runs past the window a client waits for an MCP server to hand back its tool
# list — the server is left starting, no tools are declared, and the agent
# reports the MCP server as unavailable rather than as slow. Resolving them at
# build time makes the runtime start a cache hit. No URL is involved.
RUN uvx --from 'fastmcp-slim[server]' fastmcp --version >/dev/null 2>&1 || true

# Install the default ccstatusline config.
# These defaults are overridden at runtime if the host stages replacements.
# This and the seeds below stay BELOW the plugin install: `claude plugin
# install` / `agy plugin install` write into ~/.claude, ~/.claude.json and
# ~/.gemini, so these files have to land after it to win. Only their parent
# dirs were hoisted (see the batched mkdir further up).
COPY --chown=worker:worker --chmod=666 lib/polecat/defaults/ccstatusline-settings.json /home/worker/.config/ccstatusline/settings.json
COPY --chown=worker:worker --chmod=666 lib/polecat/defaults/agystatusline-settings.json /home/worker/.config/agystatusline/settings.json
# Seed .claude.json with hasCompletedOnboarding so headless workers authenticated
# via CLAUDE_CODE_OAUTH_TOKEN skip the interactive theme/login prompts. The
# env-only auth model (lib/polecat/cli.py's get_env_forwards()) stages no
# files, so without this seed claude regenerates a minimal .claude.json that
# triggers onboarding even when the token is set.
COPY --chown=worker:worker --chmod=666 lib/polecat/defaults/claude-config.json /home/worker/.claude.json

# Seed agy's (Antigravity CLI) onboarding-complete marker so headless/crew
# workers skip its interactive first-run wizard (theme picker → migration →
# Terms-of-Service / data-collection consent). agy v1.0.13 introduced this
# wizard and gates it on ~/.gemini/antigravity-cli/cache/onboarding.json; the
# autonomous worker (interactive `agy -i`) cannot complete the TUI and never
# reaches a prompt (regression aops-d9cc656a, verified 2026-06-29). This is the
# agy analog of the Claude `hasCompletedOnboarding` seed above. Its cache dir
# is pre-created in the batched mkdir further up.
COPY --chown=worker:worker --chmod=666 lib/polecat/defaults/agy-onboarding.json /home/worker/.gemini/antigravity-cli/cache/onboarding.json
COPY --chown=worker:worker --chmod=666 lib/polecat/defaults/agy-settings.json /home/worker/.gemini/antigravity-cli/settings.json

# Copy entrypoint script
COPY --chown=worker:worker --chmod=777 lib/polecat/entrypoint.sh /home/worker/entrypoint.sh

# Make home dir itself traversable/writable for any UID — polecat crew runs
# containers as the host UID (non-root), which may differ from worker UID 1000.
# Everything *under* /home/worker is already world-writable thanks to umask 000
# in each install RUN above plus the targeted chmods for git-cloned trees, so
# no recursive walk is needed here.
RUN chmod 777 /home/worker

# Expose default container port 8080
EXPOSE 8080

# Default command and entrypoint
ENTRYPOINT ["/home/worker/entrypoint.sh"]
CMD ["/bin/bash"]
