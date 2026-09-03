# Lightweight sandbox base for academicOps agents
FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    jq \
    ripgrep \
    ca-certificates \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/bin:/usr/local/bin:$PATH" \
    PYTHONUNBUFFERED=1

WORKDIR /workspace
CMD ["/bin/bash"]
