# Use Python 3.12 with Debian Bookworm slim for a minimal, compatible base
FROM python:3.12-slim-bookworm

# Set environment variables
ENV AOPS=/app \
    ACA_DATA=/data \
    HOME=/home/worker \
    UV_INSTALL_DIR=/usr/local/bin \
    UV_CACHE_DIR=/tmp/uv-cache \
    PATH="/root/.local/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    NODE_VERSION=22

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

# Install uv (standard for aops framework per P#93)
# Using direct download for better compatibility with x86_64
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Gemini CLI, Claude Code, and code quality tools globally
RUN npm install -g @google/gemini-cli @anthropic-ai/claude-code markdownlint-cli2 dprint && npm cache clean --force

# Install Python-based CLI tools
RUN uv tool install ruff

# Set workdir
WORKDIR /app

# Copy dependency files for layer caching
COPY pyproject.toml uv.lock ./

# Pre-install project dependencies (no-dev for lightweight production-ready image)
RUN uv sync --frozen --no-install-project --no-dev

# Copy the rest of the application
COPY . .

# Final sync to install the project itself
RUN uv sync --frozen --no-dev

# Create data directory for persistence
RUN mkdir -p /data

# Create /home/worker with open permissions — polecat crew runs containers
# as the host UID (non-root), which needs a writable HOME for .claude/ session data.
# Open permissions (777) because the host UID varies per machine.
RUN mkdir -p /home/worker && chmod 777 /home/worker

# Build distribution artifacts (Claude plugin package)
RUN uv run python scripts/build.py

# Install the aops-core Claude plugin with HOME=/home/worker so that
# known_marketplaces.json and all installLocation paths are written with the
# correct container path from the start. The host's ~/.claude is NOT mounted
# at build time, so these paths are stable and correct for all container runs.
RUN HOME=/home/worker claude plugin marketplace add /app \
    && HOME=/home/worker claude plugin install aops-core@aops

# Default command
CMD ["/bin/bash"]
