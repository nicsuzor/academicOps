# Lightweight pre-built sandbox base for academicOps agents
FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    jq \
    ripgrep \
    make \
    ca-certificates \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Meet sbx requirements:
# 1. Non-root agent user at UID 1000
# 2. /home/agent owned by agent
# 3. Passwordless sudo
# 4. Preserve proxy environment variables across sudo
RUN useradd -m -u 1000 -s /bin/bash agent \
    && echo 'agent ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/agent \
    && echo 'Defaults env_keep += "HTTP_PROXY HTTPS_PROXY NO_PROXY http_proxy https_proxy no_proxy"' >> /etc/sudoers.d/agent \
    && chmod 0440 /etc/sudoers.d/agent

# Install uv and uvx to /usr/local/bin
RUN curl -LsSf https://astral.sh/uv/install.sh | env CARGO_DIST_FORCE_INSTALL_DIR=/usr/local/bin sh

# Install agy CLI and place on /usr/local/bin
RUN curl -fsSL https://antigravity.google/cli/install.sh | bash \
    && install -m 0755 /root/.local/bin/agy /usr/local/bin/agy \
    && rm -rf /root/.local

# Install pkb CLI
RUN curl -fsSL https://raw.githubusercontent.com/nicsuzor/mem/main/install.sh | bash

# Pre-cache FastMCP server dependencies for agent user so runtime launch is immediate
RUN sudo -u agent uvx --from 'fastmcp-slim[server]' fastmcp --version >/dev/null 2>&1 || true

USER agent
WORKDIR /home/agent
ENV HOME=/home/agent \
    PATH="/home/agent/.local/bin:/usr/local/bin:$PATH" \
    PYTHONUNBUFFERED=1

CMD ["/bin/bash"]
