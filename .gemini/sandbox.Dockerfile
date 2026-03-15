# aops Gemini sandbox image
#
# Used by pc crew -g to run Gemini tool calls (bash, file ops) in an isolated
# container. The Gemini CLI runs on the host; this image only executes tools.
#
# Build: make build-sandbox
# Use:   GEMINI_SANDBOX_IMAGE=aops-sandbox gemini --sandbox
#
# Intentionally leaner than the main Dockerfile — no AI CLIs needed here.
FROM python:3.12-slim-bookworm

ENV AOPS=/app \
    ACA_DATA=/data \
    UV_INSTALL_DIR=/usr/local/bin \
    PATH="/root/.local/bin:$PATH" \
    PYTHONUNBUFFERED=1

# System tools needed by aops crew workers
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    make \
    ca-certificates \
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install -y gh \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install uv (P#93: run Python via uv)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

WORKDIR /app

# Pre-install Python dependencies for layer caching
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Copy project and do final install
COPY . .
RUN uv sync --frozen --no-dev

RUN mkdir -p /data

# Create worker home for non-root polecat execution
RUN mkdir -p /home/worker && chmod 777 /home/worker

CMD ["/bin/bash"]
