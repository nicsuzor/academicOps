# Use Python 3.12 with Debian Bookworm slim for a minimal, compatible base
FROM python:3.12-slim-bookworm

# Create non-root user early so we can switch to it after system-level installs
RUN useradd -m -d /home/worker -s /bin/bash worker

# Set environment variables — HOME stays as /root during root-level installs
# to avoid polluting /home/worker with root-owned files. Switched after USER.
ENV AOPS=/app \
    ACA_DATA=/data \
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
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install uv system-wide (standard for aops framework per P#93)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Gemini CLI, Claude Code, and code quality tools globally
RUN npm install -g @google/gemini-cli @anthropic-ai/claude-code markdownlint-cli2 dprint && npm cache clean --force

# Install aops and pkb binaries from authoritative releases
RUN TMPDIR=$(mktemp -d) \
    && PLATFORM="x86_64-linux" \
    && MEM_LATEST=$(gh api repos/nicsuzor/mem/releases/latest --jq .tag_name) \
    && curl -fsSL "https://github.com/nicsuzor/mem/releases/download/${MEM_LATEST}/mem-${MEM_LATEST}-${PLATFORM}.tar.gz" -o "${TMPDIR}/mem.tar.gz" \
    && tar xzf "${TMPDIR}/mem.tar.gz" -C "${TMPDIR}" \
    && cp "${TMPDIR}/pkb" "/usr/local/bin/pkb" \
    && chmod +x "/usr/local/bin/pkb" \
    && AOPS_LATEST=$(gh api repos/nicsuzor/aops-dist/releases/latest --jq .tag_name) \
    && curl -fsSL "https://github.com/nicsuzor/aops-dist/releases/download/${AOPS_LATEST}/aops-claude-linux-x86_64.tar.gz" -o "${TMPDIR}/aops.tar.gz" \
    && tar xzf "${TMPDIR}/aops.tar.gz" -C "${TMPDIR}" \
    && if [ -f "${TMPDIR}/aops" ]; then cp "${TMPDIR}/aops" "/usr/local/bin/aops"; chmod +x "/usr/local/bin/aops"; fi \
    && rm -rf "${TMPDIR}"

# Create app and data directories, hand ownership to worker
RUN mkdir -p /app /data && chown worker:worker /app /data

# ── Switch to non-root user for all remaining operations ───────────────

WORKDIR /app
USER worker

# Now set HOME and PATH for the worker user
ENV HOME=/home/worker \
    PATH="/home/worker/.local/bin:$PATH"

# Install Python-based CLI tools as user (installs to ~/.local/bin)
RUN uv tool install ruff

# Copy dependency files for layer caching
COPY --chown=worker:worker pyproject.toml uv.lock ./

# Pre-install project dependencies (no-dev for lightweight production-ready image)
RUN uv sync --frozen --no-install-project --no-dev

# Copy the rest of the application
COPY --chown=worker:worker . .

# Final sync to install the project itself
RUN uv sync --frozen --no-dev

# Build distribution artifacts (Claude plugin package)
RUN uv run python scripts/build.py --pkb-binary /usr/local/bin/pkb

# Install the aops-core Claude plugin. HOME is already /home/worker so
# known_marketplaces.json and installLocation paths are correct from the start.
RUN claude plugin marketplace add /app \
    && claude plugin install aops-core@aops

# Install the aops-core Gemini extension from local build artifacts.
# Pre-create .gemini directory (gemini CLI needs it for project registry).
# Use a dummy GEMINI_API_KEY to bypass auth check during install.
# --consent bypasses the interactive consent prompt.
RUN mkdir -p /home/worker/.gemini \
    && GEMINI_API_KEY=dummy-for-install gemini extensions install /app/dist/aops-gemini --consent

# Make home dir and plugin dirs writable for any UID — polecat crew runs
# containers as the host UID (non-root), which may differ from the worker
# UID created above. Open permissions because the host UID varies per machine.
RUN chmod 777 /home/worker \
    && chmod -R a+w /home/worker/.claude/plugins/ 2>/dev/null || true

# Default command
CMD ["/bin/bash"]
