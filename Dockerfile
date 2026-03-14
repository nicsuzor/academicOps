# Use Python 3.12 with Debian Bookworm slim for a minimal, compatible base
FROM python:3.12-slim-bookworm

# Set environment variables
ENV AOPS=/app \
    ACA_DATA=/data \
    UV_INSTALL_DIR=/usr/local/bin \
    PATH="/root/.local/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    NODE_VERSION=22

# Install system dependencies (including Node.js for Claude/Gemini CLIs and GitHub CLI)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    make \
    cron \
    ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash - \
    && apt-get install -y nodejs \
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install -y gh \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install uv (standard for aops framework per P#93)
# Using direct download for better compatibility with x86_64
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Gemini CLI and Claude Code globally
RUN npm install -g @google/gemini-cli @anthropic-ai/claude-code

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

# Default command
CMD ["/bin/bash"]
