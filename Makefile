# AcademicOps Makefile
# Unified build and installation entry point

.PHONY: help dev build-dev install-dev install-remote install-claude install-gemini install-cli install-crontab install-hooks nextver release prerelease clean

# --- Configuration ---

AOPS_ROOT := $(shell pwd)
DIST_DIR := $(AOPS_ROOT)/dist
MEM_REPO_PATH := $(or $(wildcard $(HOME)/src/mem),$(wildcard /opt/nic/mem))
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
	@echo "  make install-hooks  - Install pre-commit hooks"
	@echo ""
	@echo "User Installation (Install from remote releases):"
	@echo "  make install        - Install all components from GitHub releases"
	@echo "  make install-claude - Install Claude plugin from dist repo"
	@echo "  make install-gemini - Install Gemini extension from main repo"
	@echo "  make install-cli    - Install pkb/aops CLI binaries"
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

# Install local build artifacts into clients
install-dev:
	@echo "Installing local build into Claude Code..."
	@command claude plugin install $(DIST_DIR)/aops-claude --force || echo "  ⚠️ Claude install failed"
	@echo "Installing local build into Gemini CLI..."
	@command gemini extensions install $(DIST_DIR)/aops-gemini --consent || echo "  ⚠️ Gemini install failed"
	@if [ -n "$(MEM_REPO_PATH)" ]; then \
		echo "Building CLI tools from $(MEM_REPO_PATH)..."; \
		cargo install --path "$(MEM_REPO_PATH)" || echo "  ⚠️ CLI build failed"; \
	fi
	@echo "✓ Local installation complete"

# Install pre-commit hooks
install-hooks:
	@echo "Installing pre-commit hooks..."
	@uv run pre-commit install
	@echo "✓ Pre-commit hooks installed"

# --- User Installation (Remote) ---

# Standard user install from official releases
install: install-claude install-gemini install-cli install-crontab

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

install-cli:
ifndef PLATFORM
	$(error Cannot detect platform. Set PLATFORM manually: make install-cli PLATFORM=linux-x86_64)
endif
	@echo "Installing aops + pkb from $(DIST_REPO) release..."
	@mkdir -p "$(INSTALL_BIN)"
	@TMPDIR=$$(mktemp -d) && \
	ARCHIVE="aops-claude-$(PLATFORM).tar.gz" && \
	gh release download --repo $(DIST_REPO) --pattern "$$ARCHIVE" --dir "$$TMPDIR" --clobber && \
	tar xzf "$$TMPDIR/$$ARCHIVE" -C "$$TMPDIR" && \
	if [ -f "$$TMPDIR/bin/aops" ]; then cp "$$TMPDIR/bin/aops" "$(INSTALL_BIN)/aops" && chmod +x "$(INSTALL_BIN)/aops"; \
	elif [ -f "$$TMPDIR/aops-claude/bin/aops" ]; then cp "$$TMPDIR/aops-claude/bin/aops" "$(INSTALL_BIN)/aops" && chmod +x "$(INSTALL_BIN)/aops"; fi && \
	if [ -f "$$TMPDIR/bin/pkb" ]; then cp "$$TMPDIR/bin/pkb" "$(INSTALL_BIN)/pkb" && chmod +x "$(INSTALL_BIN)/pkb"; \
	elif [ -f "$$TMPDIR/aops-claude/bin/pkb" ]; then cp "$$TMPDIR/aops-claude/bin/pkb" "$(INSTALL_BIN)/pkb" && chmod +x "$(INSTALL_BIN)/pkb"; fi && \
	rm -rf "$$TMPDIR" && \
	echo "✓ CLI tools installed to $(INSTALL_BIN)"

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
	else \
		echo "✗ Cron script not found at $(CRON_SCRIPT)"; \
		exit 1; \
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

# --- Utils ---

clean:
	@echo "Cleaning artifacts..."
	@rm -rf $(DIST_DIR)
	@echo "✓ Cleaned"
