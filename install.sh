#!/bin/bash
# One-line installer for academicOps framework
# Usage: curl -sSL https://raw.githubusercontent.com/nicsuzor/academicOps/main/install.sh | bash

set -e

INSTALL_DIR="${AOPS_INSTALL_DIR:-$HOME/.academicOps}"

echo "Installing aOps framework to $INSTALL_DIR..."

if [ -d "$INSTALL_DIR" ]; then
    echo "Updating existing installation..."
    cd "$INSTALL_DIR" && git pull
else
    git clone https://github.com/nicsuzor/academicOps.git "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"
./setup.sh

echo ""
echo "aOps framework installed successfully!"
echo "Run 'source ~/.bashrc' or restart your shell to use aOps commands."
