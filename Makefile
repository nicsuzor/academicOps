# AcademicOps Makefile
# Unified build and installation entry point

.PHONY: help dev build-dev install-dev uninstall-dev install-remote install-claude install-gemini package-cowork install-cli install-crontab install-hooks nextver release prerelease clean build build-docker shell

# --- Configuration ---

AOPS_ROOT := $(shell pwd)
DIST_DIR := $(AOPS_ROOT)/dist
INSTALL_BIN := $(if $(USER_OPT),$(USER_OPT)/bin,$(HOME)/.local/bin)
CRON_SCRIPT := $(AOPS_ROOT)/scripts/repo-sync-cron.sh
DIST_REPO := nicsuzor/aops
DIST_REPO_URL := https://github.com/$(DIST_REPO)
GEMINI_REMOTE_URL := https://github.com/nicsuzor/aops.git

# Extension names
GEMINI_EXT_NAME := aops-core
CLAUDE_PLUGIN_NAME := aops-core@academicOps

# Platform detection for binaries
UNAME_S := $(shell uname -s)
UNAME_M := $(shell uname -m)
ifeq ($(UNAME_S),Linux)
  ifeq ($(UNAME_M),x86_64)
    PLATFORM := linux-x86_64
  endif
endif
ifeq ($(UNAME_S),Darwin)
  ifeq ($(UNAME_M),arm64)
    PLATFORM := macos-aarch64
  endif
endif

# --- Help ---

help:
	@echo "AcademicOps Build & Install Utility"
	@echo ""
	@echo "Local Development (Install from source):"
	@echo "  make dev            - Full local dev setup (sync, build, install-dev)"
	@echo "  make build-dev      - Build extension locally (dist/)"
	@echo "  make install-dev    - Install current dist/ into Claude and Gemini"
	@echo "  make uninstall-dev  - Restore release marketplace after local testing"
	@echo "  make install-hooks  - Install pre-commit hooks"
	@echo ""
	@echo "User Installation (Install from remote releases):"
	@echo "  make install        - Install all components from GitHub releases"
	@echo "  make install-claude - Install Claude plugin from dist repo"
	@echo "  make package-cowork - Build the Cowork upload zip (dist/aops-core-vX.Y.Z.zip)"
	@echo "  make install-gemini - Install Gemini extension from main repo"
	@echo "  make install-crontab - Setup background sync"
	@echo ""
	@echo "Release Management (Automation):"
	@echo "  make prerelease     - Trigger testing build via GitHub Actions"
	@echo "  make nextver        - Show next version number"
	@echo "  make release        - Manually tag/push (prefer release-please PRs)"
	@echo ""
	@echo "Docker:"
	@echo "  make build          - Build the aops crew worker image"
	@echo "  make shell          - Interactive shell in the crew image"
	@echo ""
	@echo "Detected Platform: $(or $(PLATFORM),unknown)"

# --- Local Development ---

# Entry point for active development
dev:
	@echo "--- 🛠️  AcademicOps Local Dev Setup ---"
	@$(MAKE) build-dev
	@$(MAKE) install-dev
	@$(MAKE) install-hooks
	@echo "--- ✓ Dev setup complete ---"

# Build components from current source
build-dev:
	@echo "Building AcademicOps extension locally..."
	@ACA_DATA=$(AOPS_ROOT) uv run python scripts/build.py
	@echo "✓ Build artifacts in $(DIST_DIR)"

# Install local build artifacts into clients
# NOTE: This overrides the release marketplace with a local directory source.
# Run `make uninstall-dev` to restore the release marketplace when done testing.
install-dev: build-dev
	@echo "Installing from local build artifacts..."
	@echo "  Claude source: $(DIST_DIR) (local marketplace)"
	@echo "  Gemini source: $(DIST_DIR)/aops-gemini (local build)"
	@echo "Uninstalling existing local plugins/extensions..."
	-command gemini extensions uninstall $(GEMINI_EXT_NAME)
	-command claude plugin uninstall $(CLAUDE_PLUGIN_NAME)
	@echo "Pruning old plugin cache versions..."
	-python3 -c "\
import json, shutil, pathlib; \
f = pathlib.Path.home() / '.claude/plugins/installed_plugins.json'; \
active = json.load(open(f))['plugins'].get('$(CLAUDE_PLUGIN_NAME)', [{}])[-1].get('installPath', '') if f.exists() else ''; \
cache = pathlib.Path.home() / '.claude/plugins/cache/academicOps/aops-core'; \
[shutil.rmtree(v) or print(f'  removed {v.name}') for v in cache.iterdir() if v.is_dir() and str(v) != active] if cache.exists() else None \
"
	@echo "Configuring local Claude marketplace (overrides release source)..."
	-command claude plugin marketplace add $(DIST_DIR)
	@echo "Installing local build into Claude Code..."
	@command claude plugin install $(CLAUDE_PLUGIN_NAME) || echo "  ⚠️ Claude install failed"
	@echo "Installing local build into Gemini CLI..."
	@command gemini extensions install $(DIST_DIR)/aops-gemini --consent || echo "  ⚠️ Gemini install failed"
	@$(MAKE) report-versions
	@echo "✓ Local installation complete"
	@echo "  ⚠️  Marketplace 'academicOps' now points to $(DIST_DIR)"
	@echo "  Run 'make uninstall-dev' to restore the release marketplace."

# Restore the release marketplace after local dev testing
uninstall-dev:
	@echo "Restoring release marketplace ($(DIST_REPO))..."
	@command claude plugin marketplace add $(DIST_REPO)
	@command claude plugin marketplace update academicOps
	@command claude plugin install $(CLAUDE_PLUGIN_NAME)
	@echo "✓ Release marketplace restored"

# Install pre-commit hooks
install-hooks:
	@echo "Installing pre-commit hooks..."
	@uv run pre-commit install
	@echo "✓ Pre-commit hooks installed"

# --- User Installation (Remote) ---

# Standard user install from official releases.
# Cowork is intentionally excluded from this chain: personal Anthropic accounts
# can't add custom marketplaces, so the Cowork plugin must be uploaded manually
# via the Claude desktop app (Customize → Add plugins → Upload a file). Run
# `make package-cowork` to produce the zip, then upload it through the UI.
install: ensure-docker install-claude install-gemini install-crontab
	@$(MAKE) report-versions

ensure-docker:
	@if ! command -v docker >/dev/null 2>&1; then \
		echo "⚠️  Docker not installed — skipping sandbox image build."; \
		echo "   Crew/sandbox features will be unavailable until Docker is installed."; \
	elif ! docker info >/dev/null 2>&1; then \
		echo "⚠️  Docker installed but daemon not running — skipping sandbox image build."; \
	elif docker image inspect $(SANDBOX_IMAGE) >/dev/null 2>&1; then \
		echo "✓ Docker image '$(SANDBOX_IMAGE)' already exists"; \
	else \
		echo "Docker image '$(SANDBOX_IMAGE)' not found — building..."; \
		$(MAKE) build-sandbox || echo "⚠️  Docker image build failed — continuing without sandbox image."; \
	fi

install-claude:
	@echo "Installing aops plugin for Claude Code..."
	@echo "  Source: $(DIST_REPO_URL)"
	-command claude plugin uninstall $(CLAUDE_PLUGIN_NAME)
	@command claude plugin marketplace add $(DIST_REPO) && \
	command claude plugin marketplace update academicOps && \
	command claude plugin install $(CLAUDE_PLUGIN_NAME) && \
	echo "✓ Claude Code plugin installed"

# Cowork on personal accounts has no marketplace mechanism. The same aops-core
# plugin shipped to Claude Code CLI is uploaded to Cowork as a zip via
# Customize → Add plugins → Upload a file. Cowork silently drops hooks and
# Python scripts it can't run; no separate cowork-flavoured build exists.
# The build emits the upload artifact at dist/aops-core-v{VERSION}.zip.
package-cowork: build-dev
	@echo "Cowork upload package built at:"
	@ls -1 $(DIST_DIR)/aops-core-v*.zip 2>/dev/null | tail -1 || \
		echo "  (missing — check build output above)"
	@echo ""
	@echo "Upload via Claude desktop app:"
	@echo "  Cowork tab → Customize → Add plugins → Upload a file → select the zip above."

install-gemini:
	@echo "Installing aops extension for Gemini CLI..."
	@echo "  Source: $(GEMINI_REMOTE_URL)"
	-command gemini extensions uninstall $(GEMINI_EXT_NAME)
	@command gemini extensions install $(GEMINI_REMOTE_URL) --consent --auto-update --pre-release && \
	echo "✓ Gemini CLI extension installed"

report-versions:
	@echo "--- 📋 Installed Versions ---"
	@echo "Gemini extensions:"
	@-gemini extensions list 2>&1 || true
	@echo "Claude plugins:"
	@-claude plugin list 2>&1 || true

install-crontab:
	@if crontab -l 2>/dev/null | grep -q "repo-sync-cron"; then \
		echo "✓ Crontab already configured"; \
	elif [ -x "$(CRON_SCRIPT)" ]; then \
		echo "Installing crontab entries..."; \
		(crontab -l 2>/dev/null || true; \
		 echo "# aOps quick sync"; \
		 echo "*/5 * * * * $(CRON_SCRIPT) --quick >> /tmp/repo-sync-quick.log 2>&1"; \
		 echo "# aOps full maintenance"; \
		 echo "0 * * * * $(CRON_SCRIPT) >> /tmp/repo-sync-cron.log 2>&1") | crontab -; \
		echo "✓ Crontab entries installed"; \
	fi

# --- Release Management ---

# Trigger a prerelease build via GitHub Actions workflow_dispatch
prerelease:
	@echo "Triggering prerelease build via GitHub Actions..."
	@gh workflow run build-extension.yml --field prerelease=true
	@echo "✓ Prerelease workflow triggered. Follow progress with: gh run list --workflow=build-extension.yml"

# Show current and next version
nextver:
	@current=$$(uv run python scripts/version.py --get); \
	next=$$(uv run python scripts/version.py --next patch); \
	echo "Current: v$$current → Suggested Next: v$$next"

# Manual tag and push (Release-please is preferred)
release:
	@next=$$(uv run python scripts/version.py --next patch); \
	branch=$$(git rev-parse --abbrev-ref HEAD); \
	echo "Manual Release v$$next on $$branch..."; \
	git tag -a "v$$next" -m "release v$$next" && \
	git push origin "$$branch" "v$$next" && \
	echo "✓ Released v$$next (Note: Release-please PR might be out of sync)"

# --- Docker ---

DOCKER_IMAGE := ghcr.io/nicsuzor/aops-crew
SANDBOX_IMAGE := $(DOCKER_IMAGE)

# Build the Docker image used for crew/worker agent environments and Gemini sandboxing
# CLAUDE_CODE_VERSION busts the layer cache so the installer always runs fresh,
# picking up the latest release. Pass an explicit version to pin.
build-docker:
	@echo "Building aops crew image..."
	@docker build --build-arg CLAUDE_CODE_VERSION=$$(date +%s) --build-arg RUST_CACHEBUST=$$(date +%s) -t $(DOCKER_IMAGE) -t $(notdir $(DOCKER_IMAGE)):latest .
	@echo "✓ Image built: $(DOCKER_IMAGE) (also tagged $(notdir $(DOCKER_IMAGE)):latest)"
	@echo "  Use with: GEMINI_SANDBOX_IMAGE=$(DOCKER_IMAGE) gemini --sandbox"

# Aliases
build: build-docker
build-sandbox: build-docker

# Drop into an interactive shell in the crew image (for local testing)
shell: build-docker
	@docker run -it --rm -v $(AOPS_ROOT):/app -w /app $(DOCKER_IMAGE)

# --- Utils ---

clean:
	@echo "Cleaning artifacts..."
	@rm -rf $(DIST_DIR)
	@echo "✓ Cleaned"
