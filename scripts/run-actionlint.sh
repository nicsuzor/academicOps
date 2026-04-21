#!/bin/bash
# Helper script to run actionlint using a pre-built binary.
# This avoids the need for a Go toolchain and libc-dev in the environment.
# Used by .pre-commit-config.yaml

set -e

VERSION="1.7.11"
OS="linux"
ARCH="amd64"

# Detect architecture
case "$(uname -m)" in
    x86_64) ARCH="amd64" ;;
    aarch64|arm64) ARCH="arm64" ;;
    armv7l) ARCH="armv6" ;; # actionlint uses armv6 for 32-bit arm
esac

# Directory for the binary
BIN_DIR="$(git rev-parse --show-toplevel)/.bin"
BIN_PATH="$BIN_DIR/actionlint"

if [ ! -f "$BIN_PATH" ]; then
    # Use a lock directory for simple concurrency control
    LOCK_DIR="$BIN_DIR/install.lock"
    mkdir -p "$BIN_DIR"

    if mkdir "$LOCK_DIR" 2>/dev/null; then
        echo "Installing actionlint v$VERSION binary to $BIN_DIR..." >&2

        FILE="actionlint_${VERSION}_${OS}_${ARCH}.tar.gz"
        URL="https://github.com/rhysd/actionlint/releases/download/v${VERSION}/${FILE}"

        # Download to a temporary file first to be atomic
        TEMP_TAR="$BIN_DIR/actionlint.tar.gz"
        if ! curl -L -o "$TEMP_TAR" "$URL"; then
            rmdir "$LOCK_DIR"
            echo "Failed to download actionlint binary from $URL" >&2
            exit 1
        fi

        # Extract to a temporary binary name
        TEMP_BIN="$BIN_DIR/actionlint.tmp"
        tar -xzO actionlint < "$TEMP_TAR" > "$TEMP_BIN"
        chmod +x "$TEMP_BIN"

        # Atomic move
        mv "$TEMP_BIN" "$BIN_PATH"
        rm "$TEMP_TAR"
        rmdir "$LOCK_DIR"
    else
        # Wait for the other process to finish installation
        while [ ! -f "$BIN_PATH" ]; do
            sleep 1
        done
    fi
fi

exec "$BIN_PATH" "$@"
