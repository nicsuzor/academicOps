.PHONY: ver nextver release prerelease install install-claude install-gemini

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

# Install aops plugin for both Claude Code and Gemini CLI
install: install-claude install-gemini

# Install aops plugin for Claude Code
install-claude:
	@echo "Installing aops plugin for Claude Code..."
	@command claude plugin marketplace add nicsuzor/aops-dist && \
	command claude plugin marketplace update aops && \
	command claude plugin install aops-core@aops && \
	command claude plugin list && \
	echo "✓ Claude Code plugin installed"

# Install aops plugin for Gemini CLI
# WARNING: Uses --consent flag for auto-accept. Remove if you want manual confirmation.
install-gemini:
	@echo "Installing aops plugin for Gemini CLI..."
	@(command gemini extensions uninstall aops-core 2>/dev/null || echo "Gemini plugin not installed -- skipping removal") && \
	command gemini extensions install git@github.com:nicsuzor/aops-dist.git --consent --auto-update --pre-release && \
	echo "✓ Gemini CLI plugin installed"
