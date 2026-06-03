# AcademicOps Makefile
# Unified build and installation entry point

.PHONY: help dev build-dev install-dev uninstall-dev install-remote install-claude install-gemini install-agy install-windows package-cowork package-cowork-windows install-cli install-crontab install-hooks nextver release clean clean-plugins build build-docker shell

# --- Configuration ---

AOPS_ROOT := $(shell pwd)
DIST_DIR := $(AOPS_ROOT)/dist
INSTALL_BIN := $(if $(USER_OPT),$(USER_OPT)/bin,$(HOME)/.local/bin)
CRON_SCRIPT := $(AOPS_ROOT)/scripts/repo-sync-cron.sh
DIST_REPO := nicsuzor/academicOps
DIST_REPO_URL := https://github.com/$(DIST_REPO)
GEMINI_REMOTE_URL := https://github.com/nicsuzor/academicOps.git
AGY_PLUGIN_DIR := $(HOME)/.gemini/antigravity-cli/plugins/aops-core

# Extension names
GEMINI_EXT_NAME := aops-core
CLAUDE_PLUGIN_NAME := aops-core@academicOps
GEMINI_TOOLS_EXT_NAME := aops-tools
CLAUDE_TOOLS_PLUGIN_NAME := aops-tools@academicOps
GEMINI_TOOLS_REMOTE_URL := https://github.com/nicsuzor/academicOps/releases/latest/download/aops-tools.tar.gz

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
	@echo "  make install-dev    - Install current dist/ into Claude and Gemini (includes aops-tools)"
	@echo "  make uninstall-dev  - Restore release marketplace after local testing"
	@echo "  make install-hooks  - Install pre-commit hooks"
	@echo ""
	@echo "User Installation (Install from remote releases):"
	@echo "  make install        - Install all components from GitHub releases (includes aops-tools)"
	@echo "  make install-claude - Install Claude plugins from dist repo"
	@echo "  make package-cowork - Build the Cowork upload zip (dist/aops-core-vX.Y.Z.zip)"
	@echo "  make install-gemini - Install Gemini extensions from main repo"
	@echo "  make install-agy   - Install plugin into Antigravity CLI (agy)"
	@echo "  make install-windows - (WSL only) Install into Windows-side Claude/Gemini if present"
	@echo "  make install-crontab - Setup background sync"
	@echo ""
	@echo "Release Management (Automation):"
	@echo "  make nextver        - Show next version number"
	@echo "  make release        - Manually tag/push (prefer release-please PRs)"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean          - Remove dist/ and prune stale plugin cache"
	@echo "  make clean-plugins  - Prune stale plugin cache versions + orphan manifests"
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
	-command gemini extensions uninstall $(GEMINI_EXT_NAME) 2>/dev/null; \
		rm -rf "$(HOME)/.gemini/extensions/$(GEMINI_EXT_NAME)"
	-command gemini extensions uninstall $(GEMINI_TOOLS_EXT_NAME) 2>/dev/null; \
		rm -rf "$(HOME)/.gemini/extensions/$(GEMINI_TOOLS_EXT_NAME)"
	-command claude plugin uninstall $(CLAUDE_PLUGIN_NAME)
	-command claude plugin uninstall $(CLAUDE_TOOLS_PLUGIN_NAME)
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
	@command claude plugin install $(CLAUDE_TOOLS_PLUGIN_NAME) || echo "  ⚠️ Claude aops-tools install failed"
	@echo "Installing local build into Gemini CLI..."
	@command gemini extensions install $(DIST_DIR)/aops-gemini --consent || echo "  ⚠️ Gemini install failed"
	@command gemini extensions install $(DIST_DIR)/aops-tools-gemini --consent || echo "  ⚠️ Gemini aops-tools install failed"
	@$(MAKE) install-agy
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
	@command claude plugin install $(CLAUDE_TOOLS_PLUGIN_NAME)
	@echo "✓ Release marketplace restored"

# Install pre-commit hooks
install-hooks:
	@echo "Installing pre-commit hooks..."
	@uv run pre-commit install
	@echo "✓ Pre-commit hooks installed"

# --- User Installation (Remote) ---

# Standard user install from official releases.
# Cowork is intentionally excluded from this chain: personal Anthropic accounts
# can't add custom marketplaces, so the `aops-cowork` plugin must be uploaded
# manually via the Claude desktop app (Customize → Add plugins → Upload a
# file). Run `make package-cowork` to produce the zip, then upload it through
# the UI. (Note: `aops-cowork` is a distinct plugin from `aops-core`, with
# Cowork-specific behaviour for the PKB ↔ native task-list mirror — see
# `aops-core/skills/cowork-sync/SKILL.md`.)
install: ensure-docker install-claude install-gemini install-agy install-windows install-crontab
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
	-command claude plugin uninstall $(CLAUDE_TOOLS_PLUGIN_NAME)
	@command claude plugin marketplace add $(DIST_REPO) && \
	command claude plugin marketplace update academicOps && \
	command claude plugin install $(CLAUDE_PLUGIN_NAME) && \
	echo "✓ Claude Code aops-core installed"
	@command claude plugin install $(CLAUDE_TOOLS_PLUGIN_NAME) \
		|| echo "  ⚠️ Claude aops-tools install failed — plugin source missing from $(DIST_REPO_URL) marketplace (next dist build should restore it)"

# Cowork on personal accounts has no marketplace mechanism. The Cowork plugin
# is a SEPARATE build (`aops-cowork`) from the Claude Code CLI build (`aops-core`):
# same Claude-shaped layout, but with cowork-only skill blocks kept and the
# `cowork-sync` skill bundled. See `build_aops_core(platform="cowork", ...)` in
# scripts/build.py and `aops-core/skills/cowork-sync/SKILL.md` for the PKB
# ↔ native task-list mirror behaviour. The legacy `aops-core-v{VERSION}.zip`
# name is preserved as a symlink for backwards compatibility with any existing
# download URLs.
package-cowork: build-dev
	@echo "Cowork upload package built at:"
	@ls -1 $(DIST_DIR)/aops-cowork-v*.zip 2>/dev/null | tail -1 || \
		ls -1 $(DIST_DIR)/aops-core-v*.zip 2>/dev/null | tail -1 || \
		echo "  (missing — check build output above)"
	@echo ""
	@echo "Upload via Claude desktop app:"
	@echo "  Cowork tab → Customize → Add plugins → Upload a file → select the zip above."
	@if [ -d /mnt/c ] && grep -qi microsoft /proc/version 2>/dev/null; then \
		$(MAKE) --no-print-directory package-cowork-windows; \
	fi

# Copy the latest Cowork zip into the Windows user's Downloads folder so the
# desktop file-picker can see it on a native drive (UNC paths can be flaky).
# Only meaningful on WSL.
package-cowork-windows:
	@if [ ! -d /mnt/c ] || ! grep -qi microsoft /proc/version 2>/dev/null; then \
		echo "Not on WSL — nothing to copy."; exit 0; \
	fi; \
	ZIP=$$(ls -1t $(DIST_DIR)/aops-cowork-v*.zip 2>/dev/null | head -1); \
	if [ -z "$$ZIP" ]; then \
		ZIP=$$(ls -1t $(DIST_DIR)/aops-core-v*.zip 2>/dev/null | head -1); \
	fi; \
	if [ -z "$$ZIP" ]; then \
		echo "  ⚠️ No Cowork zip found in $(DIST_DIR) — run 'make package-cowork' first."; exit 1; \
	fi; \
	WIN_USER=$$(cmd.exe /c "echo %USERNAME%" 2>/dev/null | tr -d '\r' | tr -d '\n'); \
	DEST="/mnt/c/Users/$$WIN_USER/Downloads"; \
	if [ ! -d "$$DEST" ]; then \
		echo "  ⚠️ Windows Downloads not found at $$DEST — skipping."; exit 0; \
	fi; \
	cp "$$ZIP" "$$DEST/" && \
		echo "✓ Copied $$(basename $$ZIP) → $$DEST" && \
		echo "  In Claude desktop: Cowork → Customize → Add plugins → Upload a file → pick from Downloads."

install-gemini:
	@echo "Installing aops extension for Gemini CLI..."
	@echo "  Source: $(GEMINI_REMOTE_URL)"
	-command gemini extensions uninstall $(GEMINI_EXT_NAME)
	-command gemini extensions uninstall $(GEMINI_TOOLS_EXT_NAME)
	@command gemini extensions install $(GEMINI_REMOTE_URL) --consent --auto-update --pre-release && \
	echo "✓ Gemini CLI aops-core extension installed"
	@command gemini extensions install $(GEMINI_TOOLS_REMOTE_URL) --consent --auto-update --pre-release \
		|| echo "  ⚠️ Gemini aops-tools install failed — release asset missing from $(GEMINI_TOOLS_REMOTE_URL) (next dist build should restore it)"

# Install into Antigravity CLI (agy). Unlike gemini/claude which have their own
# plugin install commands, agy reads plugins from a flat directory.
# If dist/aops-antigravity exists (local dev build), use it directly.
# Otherwise, download the latest release tarball from GitHub.
AGY_RELEASE_URL := $(DIST_REPO_URL)/releases/latest/download/aops-antigravity-latest.tar.gz

install-agy:
	@if ! command -v agy >/dev/null 2>&1; then \
		echo "  (agy not found on PATH — skipping Antigravity install)"; \
		exit 0; \
	fi
	@echo "Installing aops plugin into Antigravity CLI (agy)..."
	@if [ -d "$(DIST_DIR)/aops-antigravity" ]; then \
		echo "  Source: $(DIST_DIR)/aops-antigravity (local build)"; \
		mkdir -p "$(AGY_PLUGIN_DIR)"; \
		cp -r "$(DIST_DIR)/aops-antigravity/"* "$(AGY_PLUGIN_DIR)/"; \
		agy plugin install "$(AGY_PLUGIN_DIR)"; \
	else \
		echo "  Source: $(AGY_RELEASE_URL)"; \
		TMP_DIR=$$(mktemp -d); \
		curl -fsSL "$(AGY_RELEASE_URL)" | tar -xz -C "$$TMP_DIR"; \
		mkdir -p "$(AGY_PLUGIN_DIR)"; \
		cp -r "$$TMP_DIR/"* "$(AGY_PLUGIN_DIR)/"; \
		agy plugin install "$(AGY_PLUGIN_DIR)"; \
		rm -rf "$$TMP_DIR"; \
	fi
	@echo "  Target: $(AGY_PLUGIN_DIR)"
	@echo "✓ Antigravity CLI plugin installed"
	@if [ -f "$(HOME)/.gemini/config/mcp_config.json" ] && [ ! -s "$(HOME)/.gemini/config/mcp_config.json" ]; then \
		echo '{}' > "$(HOME)/.gemini/config/mcp_config.json"; \
		echo "  ✓ Fixed empty mcp_config.json"; \
	fi

# Optional: install into Windows-side Claude/Gemini when invoked from WSL.
# Silently no-ops outside WSL or when no Windows binaries are found.
# Set AOPS_SKIP_WINDOWS=1 to opt out even when WSL + Windows binaries are present.
install-windows:
	@if [ -n "$$AOPS_SKIP_WINDOWS" ]; then \
		echo "Skipping Windows-side install (AOPS_SKIP_WINDOWS set)"; \
		exit 0; \
	fi; \
	if [ ! -d /mnt/c ] || ! grep -qi microsoft /proc/version 2>/dev/null; then \
		exit 0; \
	fi; \
	echo "--- 🪟  WSL detected — checking for Windows-side Claude/Gemini ---"; \
	if (cd /mnt/c && cmd.exe /c "where claude" >/dev/null 2>&1); then \
		echo "Installing aops-core plugin into Windows Claude..."; \
		(cd /mnt/c && cmd.exe /c "claude plugin marketplace add $(DIST_REPO)" 2>&1 | grep -v -E '^(UNC paths|Defaulting to)' || true); \
		(cd /mnt/c && cmd.exe /c "claude plugin marketplace update academicOps" 2>&1 | grep -v -E '^(UNC paths|Defaulting to)' || true); \
		(cd /mnt/c && cmd.exe /c "claude plugin install $(CLAUDE_PLUGIN_NAME)" 2>&1 | grep -v -E '^(UNC paths|Defaulting to)') \
			&& echo "✓ Windows Claude aops-core installed" \
			|| echo "  ⚠️ Windows Claude aops-core install failed"; \
		(cd /mnt/c && cmd.exe /c "claude plugin install $(CLAUDE_TOOLS_PLUGIN_NAME)" 2>&1 | grep -v -E '^(UNC paths|Defaulting to)') \
			&& echo "✓ Windows Claude aops-tools installed" \
			|| echo "  ⚠️ Windows Claude aops-tools install failed"; \
	else \
		echo "  (no Windows-side claude found — skipping)"; \
	fi; \
	if (cd /mnt/c && cmd.exe /c "where gemini" >/dev/null 2>&1); then \
		echo "Installing aops extensions into Windows Gemini CLI..."; \
		(cd /mnt/c && cmd.exe /c "gemini extensions install $(GEMINI_REMOTE_URL) --consent --auto-update --pre-release" 2>&1 | grep -v -E '^(UNC paths|Defaulting to)') \
			&& echo "✓ Windows Gemini aops-core installed" \
			|| echo "  ⚠️ Windows Gemini aops-core install failed"; \
		(cd /mnt/c && cmd.exe /c "gemini extensions install $(GEMINI_TOOLS_REMOTE_URL) --consent --auto-update --pre-release" 2>&1 | grep -v -E '^(UNC paths|Defaulting to)') \
			&& echo "✓ Windows Gemini aops-tools installed" \
			|| echo "  ⚠️ Windows Gemini aops-tools install failed"; \
	else \
		echo "  (no Windows-side gemini found — skipping)"; \
	fi

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

clean: clean-plugins
	@echo "Cleaning artifacts..."
	@rm -rf $(DIST_DIR)
	@echo "✓ Cleaned"

# Prune stale Claude plugin caches in both surfaces:
#  1. CLI / `~/.claude/plugins/cache/` — keeps only versions referenced by
#     installed_plugins.json; removes install manifests whose marketplace dir
#     is gone.
#  2. Desktop GUI app / `~/Library/Application Support/Claude/
#     local-agent-mode-sessions/<account>/<surface>/rpm/` — force-removes
#     aops-* entries from the rpm manifest and deletes their unpacked dirs.
#     Use this when the GUI's "Uninstall plugin" button fails.
clean-plugins:
	@echo "Pruning stale Claude plugin cache versions..."
	@python3 scripts/clean_plugins.py
