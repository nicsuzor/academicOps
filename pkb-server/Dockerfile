# Lightweight container for the PKB MCP HTTP server.
# Runs `pkb mcp --http --host 0.0.0.0` on port 8026.
#
# The pkb binary is downloaded from nicsuzor/mem releases at build time.
# At runtime, mount the brain data directory and BGE-M3 model files.
#
# Build:
#   docker build -t pkb-mcp-server pkb-server/
#
# Run (see docker-compose.yml for the recommended approach):
#   docker run -d --name pkb-mcp-server \
#     -v /opt/nic/brain:/data \
#     -v /opt/debian/cache/aops/models/bge-m3:/models/bge-m3:ro \
#     -p 8026:8026 \
#     --restart unless-stopped \
#     pkb-mcp-server

FROM debian:bookworm-slim

# Install minimal runtime dependencies (curl for healthcheck, ca-certs for TLS)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -d /home/pkb -s /bin/bash pkb

# Download pkb binary from latest nicsuzor/mem release
RUN PLATFORM="x86_64-linux" \
    && MEM_TAG=$(curl -s https://api.github.com/repos/nicsuzor/mem/releases/latest \
         | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/') \
    && curl -fsSL "https://github.com/nicsuzor/mem/releases/download/${MEM_TAG}/mem-${MEM_TAG}-${PLATFORM}.tar.gz" \
         -o /tmp/mem.tar.gz \
    && tar xzf /tmp/mem.tar.gz -C /tmp \
    && cp /tmp/pkb /usr/local/bin/pkb \
    && chmod +x /usr/local/bin/pkb \
    && rm -rf /tmp/mem.tar.gz /tmp/pkb

# Create mount points
RUN mkdir -p /data /models/bge-m3 && chown pkb:pkb /data

USER pkb

ENV ACA_DATA=/data \
    PKB_MODEL_DIR=/models/bge-m3 \
    RUST_LOG=info

EXPOSE 8026

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -sf http://localhost:8026/health || exit 1

ENTRYPOINT ["pkb"]
CMD ["mcp", "--http", "--host", "0.0.0.0"]
