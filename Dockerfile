# Use Python 3.12 with Debian Bookworm slim for a minimal, compatible base
FROM python:3.12-slim-bookworm

# Create non-root user early so we can switch to it after system-level installs
RUN useradd -m -d /home/worker -s /bin/bash worker

# Set environment variables — HOME stays as /root during root-level installs
# to avoid polluting /home/worker with root-owned files. Switched after USER.
ENV ACA_DATA=/data \
    HOSTNAME=aops-crew \
    UV_INSTALL_DIR=/usr/local/bin \
    PYTHONUNBUFFERED=1 \
    NODE_VERSION=22

# ── Root-only: system packages and global tooling ──────────────────────

# Install system dependencies (including Node.js for Claude/Gemini CLIs, GitHub CLI, Docker CLI)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    gnupg \
    make \
    cron \
    ca-certificates \
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

# Install uv system-wide (standard for aops framework per P#93)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Gemini CLI, Claude Code, and code quality tools globally
RUN npm install -g @google/gemini-cli @anthropic-ai/claude-code markdownlint-cli2 dprint ccstatusline && npm cache clean --force

# Create data directory, hand ownership to worker
RUN mkdir -p /data && chown worker:worker /data

# ── Switch to non-root user for all remaining operations ───────────────

USER worker

# Now set HOME and PATH for the worker user
ENV HOME=/home/worker \
    PATH="/home/worker/.local/bin:/home/worker/.cargo/bin:$PATH"

# Install Rust toolchain via rustup
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --no-modify-path --profile minimal

# Install Python-based CLI tools as user (installs to ~/.local/bin)
RUN uv tool install ruff

# ── Install aops framework from GitHub (same as `make install`) ──────
# Claude plugin: installed from the GitHub repo marketplace (dist/aops-claude
# is committed to main by the build-extension workflow).
# Gemini extension: installed from the GitHub repo with --pre-release.
# pkb binary: downloaded from nicsuzor/mem releases.
#
# To test main before a stable release: `make prerelease && make build`
ARG AOPS_REPO_URL=https://github.com/nicsuzor/academicOps.git

# Install Claude plugin from GitHub marketplace (HTTPS — no SSH in containers).
# --sparse limits checkout to plugin directories only (faster, avoids full repo clone).
RUN claude plugin marketplace add ${AOPS_REPO_URL} --sparse .claude-plugin dist/aops-claude \
    && claude plugin marketplace update academicOps \
    && claude plugin install aops-core@academicOps

# Install pkb binary from nicsuzor/mem releases
RUN TMPDIR=$(mktemp -d) \
    && PLATFORM="x86_64-linux" \
    && MEM_TAG=$(curl -s https://api.github.com/repos/nicsuzor/mem/releases/latest \
         | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/') \
    && curl -fsSL "https://github.com/nicsuzor/mem/releases/download/${MEM_TAG}/mem-${MEM_TAG}-${PLATFORM}.tar.gz" \
         -o "${TMPDIR}/mem.tar.gz" \
    && tar xzf "${TMPDIR}/mem.tar.gz" -C "${TMPDIR}" \
    && cp "${TMPDIR}/pkb" "$HOME/.local/bin/pkb" \
    && chmod +x "$HOME/.local/bin/pkb" \
    && rm -rf "${TMPDIR}"

# Install Gemini extension from GitHub repo
RUN mkdir -p /home/worker/.gemini \
    && GEMINI_API_KEY=dummy-for-install gemini extensions install ${AOPS_REPO_URL} --consent --pre-release

# Set permissive extension enablement so hooks fire for any workspace path.
# `gemini extensions install` restricts to /home/<user>/* which doesn't match
# mounted worktrees (e.g. /workspace, /data, or deeply nested crew paths).
RUN if [ -f /home/worker/.gemini/extensions/extension-enablement.json ]; then \
    python3 -c "import json, pathlib; \
p = pathlib.Path('/home/worker/.gemini/extensions/extension-enablement.json'); \
d = json.loads(p.read_text()); \
[d.__setitem__(k, {**v, 'overrides': ['*']}) for k, v in d.items()]; \
p.write_text(json.dumps(d, indent=2))" ; \
    fi

# Install default ccstatusline and Claude Code settings.
# These defaults are overridden at runtime if the host stages replacements.
COPY --chown=worker:worker polecat/defaults/ccstatusline-settings.json /home/worker/.config/ccstatusline/settings.json
COPY --chown=worker:worker polecat/defaults/claude-settings.json /home/worker/.claude/settings.json

# Copy entrypoint script
COPY --chown=worker:worker polecat/entrypoint.sh /home/worker/entrypoint.sh
RUN chmod +x /home/worker/entrypoint.sh

# Make home dir and .claude writable for any UID — polecat crew runs containers
# as the host UID (non-root), which may differ from worker UID 1000.
# Remove .claude.json so the entrypoint can populate it from staging with correct ownership.
RUN chmod 777 /home/worker \
    && (chmod -R 777 /home/worker/.claude/ 2>/dev/null || true) \
    && (chmod -R 777 /home/worker/.cache/ 2>/dev/null || true) \
    && rm -f /home/worker/.claude.json

# Default command and entrypoint
ENTRYPOINT ["/home/worker/entrypoint.sh"]
CMD ["/bin/bash"]
