# AcademicOps Makefile
# Unified build and installation entry point

.PHONY: help dev build-dev install-dev uninstall-dev install-remote install-claude install-gemini install-cli install-crontab install-hooks nextver release prerelease clean build-sandbox shell

# --- Configuration ---

AOPS_ROOT := $(shell pwd)
DIST_DIR := $(AOPS_ROOT)/dist
INSTALL_BIN := $(if $(USER_OPT),$(USER_OPT)/bin,$(HOME)/.local/bin)
CRON_SCRIPT := $(AOPS_ROOT)/scripts/repo-sync-cron.sh
DIST_REPO := nicsuzor/aops-dist

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
	@echo "  make install-gemini - Install Gemini extension from main repo"
	@echo "  make install-crontab - Setup background sync"
	@echo ""
	@echo "Release Management (Automation):"
	@echo "  make prerelease     - Trigger testing build via GitHub Actions"
	@echo "  make nextver        - Show next version number"
	@echo "  make release        - Manually tag/push (prefer release-please PRs)"
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

# Verify the Docker environment for both Claude and Gemini
test-docker:
	@echo "Verifying Docker environment (multi-client support)..."
	@./scripts/verify-docker-env.sh

# Install local build artifacts into clients
# NOTE: This overrides the release marketplace with a local directory source.
# Run `make uninstall-dev` to restore the release marketplace when done testing.
install-dev:
	@echo "Uninstalling existing local plugins/extensions..."
	-command gemini extensions uninstall aops-core
	-command claude plugin uninstall aops-core
	@echo "Pruning old plugin cache versions..."
	-python3 -c "\
import json, shutil, pathlib; \
f = pathlib.Path.home() / '.claude/plugins/installed_plugins.json'; \
active = json.load(open(f))['plugins'].get('aops-core@aops', [{}])[-1].get('installPath', '') if f.exists() else ''; \
cache = pathlib.Path.home() / '.claude/plugins/cache/aops/aops-core'; \
[shutil.rmtree(v) or print(f'  removed {v.name}') for v in cache.iterdir() if v.is_dir() and str(v) != active] if cache.exists() else None \
"
	@echo "Configuring local Claude marketplace (overrides release source)..."
	-command claude plugin marketplace add $(AOPS_ROOT)
	@echo "Installing local build into Claude Code..."
	@command claude plugin install aops-core@aops || echo "  ⚠️ Claude install failed"
	@echo "Installing local build into Gemini CLI..."
	@command gemini extensions install $(DIST_DIR)/aops-gemini --consent || echo "  ⚠️ Gemini install failed"
	@echo "✓ Local installation complete"
	@echo "  ⚠️  Marketplace 'aops' now points to $(AOPS_ROOT)"
	@echo "  Run 'make uninstall-dev' to restore the release marketplace."

# Restore the release marketplace after local dev testing
uninstall-dev:
	@echo "Restoring release marketplace ($(DIST_REPO))..."
	@command claude plugin marketplace add $(DIST_REPO)
	@command claude plugin marketplace update aops
	@command claude plugin install aops-core@aops
	@echo "✓ Release marketplace restored"

# Install pre-commit hooks
install-hooks:
	@echo "Installing pre-commit hooks..."
	@uv run pre-commit install
	@echo "✓ Pre-commit hooks installed"

# --- User Installation (Remote) ---

# Standard user install from official releases
install: install-claude install-gemini install-crontab

install-claude:
	@echo "Installing aops plugin for Claude Code from $(DIST_REPO)..."
	@command claude plugin marketplace add $(DIST_REPO) && \
	command claude plugin marketplace update aops && \
	command claude plugin install aops-core@aops && \
	echo "✓ Claude Code plugin installed"

install-gemini:
	@echo "Installing aops extension for Gemini CLI from GitHub..."
	@command gemini extensions install git@github.com:nicsuzor/academicOps.git --consent --auto-update --pre-release && \
	echo "✓ Gemini CLI extension installed"

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
	@current=$$(uv run python scripts/build.py --version); \
	next=$$(echo $$current | awk -F. '{print $$1 "." $$2 "." $$3+1}'); \
	echo "Current: v$$current → Suggested Next: v$$next"

# Manual tag and push (Release-please is preferred)
release:
	@current=$$(uv run python scripts/build.py --version); \
	next=$$(echo $$current | awk -F. '{print $$1 "." $$2 "." $$3+1}'); \
	branch=$$(git rev-parse --abbrev-ref HEAD); \
	echo "Manual Release v$$next on $$branch..."; \
	git tag "v$$next" && \
	git push origin "$$branch" "v$$next" && \
	echo "✓ Released v$$next (Note: Release-please PR might be out of sync)"

# --- Docker ---

SANDBOX_IMAGE := aops-sandbox

# Build the Gemini crew sandbox image from .gemini/sandbox.Dockerfile
build-sandbox:
	@echo "Building aops Gemini sandbox image..."
	@docker build -f .gemini/sandbox.Dockerfile -t $(SANDBOX_IMAGE) .
	@echo "✓ Sandbox image built: $(SANDBOX_IMAGE)"
	@echo "  Use with: GEMINI_SANDBOX_IMAGE=$(SANDBOX_IMAGE) gemini --sandbox"

# Drop into an interactive shell in the sandbox image (for local testing)
shell: build-sandbox
	@docker run -it --rm -v $(AOPS_ROOT):/app -w /app $(SANDBOX_IMAGE)

# --- Utils ---

clean:
	@echo "Cleaning artifacts..."
	@rm -rf $(DIST_DIR)
	@echo "✓ Cleaned"
