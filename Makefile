.PHONY: ver nextver release prerelease \
	install install-claude install-gemini install-cli install-crontab \
	install-dev install-claude-dev install-cli-dev install-hooks

DIST_REPO := nicsuzor/aops-dist
MEM_REPO_PATH := $(or $(wildcard $(HOME)/src/mem),$(wildcard /opt/nic/mem))
INSTALL_BIN := $(if $(USER_OPT),$(USER_OPT)/bin,$(HOME)/.local/bin)
CRON_SCRIPT := $(HOME)/dotfiles/scripts/repo-sync-cron.sh

# Detect platform for binary downloads
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

# --- Version & Release ---

# Show current version
ver:
	@uv run python scripts/build.py --version

# Show current and next version
nextver:
	@current=$$(uv run python scripts/build.py --version); \
	next=$$(echo $$current | awk -F. '{print $$1 "." $$2 "." $$3+1}'); \
	echo "Current: v$$current → Next: v$$next"

# Tag and push a new release
release:
	@current=$$(uv run python scripts/build.py --version); \
	next=$$(echo $$current | awk -F. '{print $$1 "." $$2 "." $$3+1}'); \
	branch=$$(git rev-parse --abbrev-ref HEAD); \
	echo "Releasing v$$next on $$branch..."; \
	git tag "v$$next" && \
	git fetch origin "$$branch" && \
	git push origin "$$branch" "v$$next" && \
	echo "✓ Released v$$next"

# Trigger a prerelease build via GitHub Actions workflow_dispatch
prerelease:
	@echo "Triggering prerelease build..."
	@gh workflow run build-extension.yml --field prerelease=true && \
	echo "✓ Prerelease workflow triggered. Check: gh run list --workflow=build-extension.yml"

# --- Release Install (default) ---

# Install from GitHub releases (no local build)
install: install-claude install-cli install-crontab

# Install aops plugin for Claude Code from marketplace
install-claude:
	@echo "Installing aops plugin for Claude Code..."
	@command claude plugin marketplace add nicsuzor/aops-dist && \
	command claude plugin marketplace update aops && \
	command claude plugin install aops-core@aops && \
	command claude plugin list && \
	echo "✓ Claude Code plugin installed"

# Install aops plugin for Gemini CLI from main repo
# WARNING: Uses --consent flag for auto-accept. Remove if you want manual confirmation.
install-gemini:
	@echo "Installing aops plugin for Gemini CLI..."
	@(command gemini extensions uninstall aops-core 2>/dev/null || echo "Gemini plugin not installed -- skipping removal") && \
	command gemini extensions install git@github.com:nicsuzor/academicOps.git --consent --auto-update --pre-release && \
	command gemini extensions list && \
	echo "✓ Gemini CLI plugin installed"

# Download aops + pkb from GitHub release and install to bin dir
install-cli:
ifndef PLATFORM
	$(error Cannot detect platform. Set PLATFORM manually: make install-cli PLATFORM=linux-x86_64)
endif
	@echo "Installing aops + pkb from $(DIST_REPO) release..."
	@mkdir -p "$(INSTALL_BIN)"
	@TMPDIR=$$(mktemp -d) && \
	ARCHIVE="aops-claude-$(PLATFORM).tar.gz" && \
	echo "  Downloading $$ARCHIVE..." && \
	gh release download --repo $(DIST_REPO) --pattern "$$ARCHIVE" --dir "$$TMPDIR" --clobber && \
	echo "  Extracting binaries..." && \
	tar xzf "$$TMPDIR/$$ARCHIVE" -C "$$TMPDIR" && \
	if [ -f "$$TMPDIR/bin/aops" ]; then \
		cp "$$TMPDIR/bin/aops" "$(INSTALL_BIN)/aops" && chmod +x "$(INSTALL_BIN)/aops"; \
	elif [ -f "$$TMPDIR/aops-claude/bin/aops" ]; then \
		cp "$$TMPDIR/aops-claude/bin/aops" "$(INSTALL_BIN)/aops" && chmod +x "$(INSTALL_BIN)/aops"; \
	fi && \
	if [ -f "$$TMPDIR/bin/pkb" ]; then \
		cp "$$TMPDIR/bin/pkb" "$(INSTALL_BIN)/pkb" && chmod +x "$(INSTALL_BIN)/pkb"; \
	elif [ -f "$$TMPDIR/aops-claude/bin/pkb" ]; then \
		cp "$$TMPDIR/aops-claude/bin/pkb" "$(INSTALL_BIN)/pkb" && chmod +x "$(INSTALL_BIN)/pkb"; \
	fi && \
	rm -rf "$$TMPDIR" && \
	echo "  Installed to $(INSTALL_BIN)" && \
	echo "  aops: $$($(INSTALL_BIN)/aops --version 2>/dev/null || echo 'installed')" && \
	echo "  pkb:  $$($(INSTALL_BIN)/pkb --version 2>/dev/null || echo 'installed')" && \
	echo "✓ CLI tools installed" && \
	case ":$$PATH:" in *":$(INSTALL_BIN):"*) ;; *) echo "⚠ $(INSTALL_BIN) is not on PATH. Add it to your shell config." ;; esac

# Install crontab entry for repo-sync
install-crontab:
	@if crontab -l 2>/dev/null | grep -q "repo-sync-cron"; then \
		echo "✓ repo-sync-cron already in crontab"; \
	elif [ -x "$(CRON_SCRIPT)" ]; then \
		echo "Installing crontab entry..."; \
		(crontab -l 2>/dev/null || true; echo "*/30 * * * * $(CRON_SCRIPT) >> /tmp/repo-sync-cron.log 2>&1") | crontab -; \
		echo "✓ Crontab entry installed"; \
	else \
		echo "✗ Cron script not found at $(CRON_SCRIPT)"; \
		exit 1; \
	fi

# --- Development Install (local build) ---

# Install from local source (requires mem repo + cargo)
install-dev: install-claude-dev install-cli-dev install-hooks

# Install pre-commit hooks into local git repo
install-hooks:
	@echo "Installing pre-commit hooks..."
	@uv run pre-commit install && \
	echo "✓ Pre-commit hooks installed"

# Build plugin locally and install for Claude Code
install-claude-dev:
	@echo "Building and installing aops plugin locally..."
	@uv run python scripts/build.py && \
	claude plugin install ./dist/aops-claude && \
	echo "✓ Claude Code plugin installed from local build"

# Build aops + pkb from local mem repo via cargo
install-cli-dev:
ifeq ($(MEM_REPO_PATH),)
	$(error mem repo not found. Clone it to ~/src/mem or /opt/nic/mem)
endif
	@echo "Building aops + pkb from $(MEM_REPO_PATH)..."
	@cargo install --path "$(MEM_REPO_PATH)" && \
	echo "✓ CLI tools built and installed via cargo"
