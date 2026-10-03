# academicOps — build & install. Design: specs/ARCHITECTURE.md.

.PHONY: help build build-test install-dev uninstall-dev install clean clean-plugins test lint format

# Plugin marketplace names declared in build/marketplace.toml — the single
# source of truth for what ships (specs/ARCHITECTURE.md's plugin table).
PLUGIN_NAMES = $(shell uv run python -c "import tomllib, pathlib; d = tomllib.loads(pathlib.Path('build/marketplace.toml').read_text()); print(' '.join(p['name'] for p in d['plugins']))" 2>/dev/null)
STALE_PLUGIN_NAMES = aops aops-cope aops-extras aops-ida aops-jr aops-pkb aops-tools aops-ts pkb

help:
	@echo "make build          - assemble dist/ for every plugin, clients (Claude, agy, openclaw)"
	@echo "make build-test     - build, then validate every dist/ plugin dir with"
	@echo "                      'claude plugin validate' and 'agy plugin validate'"
	@echo "make install-dev    - build, then install dist/ as the local '$(LOCAL_MARKETPLACE)' marketplace"
	@echo "make uninstall-dev  - remove the local marketplace, restore the released one"
	@echo "make install        - install the released plugins from the dist branch"
	@echo "make test           - run the pytest suite"
	@echo "make lint           - ruff check + documented-reference check + basedpyright"
	@echo "make format         - ruff format + dprint fmt"
	@echo "make clean          - remove dist/"
	@echo "make clean-plugins  - prune stale plugin caches and cowork packages"


# --- Build ---

build:
	@uv run python -m build.build

build-claude:
	@uv run python -m build.build --clients claude

build-agy:
	@uv run python -m build.build --clients agy

build-openclaw:
	@uv run python -m build.build --clients openclaw

# Cowork installs from dist/cowork (directory marketplace or zip upload) and
# launches a plugin's MCP servers with a bare environment — $PKB_MCP_URL does
# not expand there and nothing can supply it after install. build.marketplace
# bakes the URL into dist/cowork's .mcp.json as the stdio launcher's env when
# it is set at build time, and warns when it is not. Deliberately
# NOT a build failure: the published channel ships without a URL, so Cowork's
# services MCP is unusable until there is a real way to configure it
# post-install. Only a local build with PKB_MCP_URL exported produces a
# working Cowork channel.
build-cowork:
	@uv run python -m build.build --clients claude

# Each client ships its own manifest schema (.claude-plugin/plugin.json vs
# plugin.json, agent.md's frontmatter shape, hooks.json's shape) and only
# that client's own CLI can validate against it — build.py has no
# independent checker for either. Not part of `make build`: this runs each
# dist plugin dir through the client that will actually load it, so a
# manifest error surfaces here instead of at install or first use.
build-test: build
	@for p in $(PLUGIN_NAMES); do \
		command claude plugin validate "$(DIST)/$$p-claude" \
			&& echo "✓ claude $$p validated" \
			|| { echo "x claude $$p validate failed" >&2; exit 1; }; \
		if [ -d "$(DIST)/cowork/$$p" ]; then \
			command claude plugin validate "$(DIST)/cowork/$$p" \
				&& echo "✓ cowork $$p validated" \
				|| { echo "x cowork $$p validate failed" >&2; exit 1; }; \
		fi; \
		if command -v agy >/dev/null 2>&1; then \
			agy plugin validate "$(DIST)/$$p-agy" \
				&& echo "✓ agy $$p validated" \
				|| { echo "x agy $$p validate failed" >&2; exit 1; }; \
		fi; \
		if command -v claude >/dev/null 2>&1; then \
			claude plugin validate "$(DIST)/$$p-openclaw" \
				&& echo "✓ openclaw $$p validated" \
				|| { echo "x openclaw $$p validate failed" >&2; exit 1; }; \
		fi; \
	done
	@echo "✓ dist/ validated for every plugin and client target"

# --- Install ---

define claude_install
	command claude plugin install $(1)@$(2) && echo "✓ $(1)@$(2) installed" \
		|| { echo "x $(1)@$(2) install failed" >&2; exit 1; }
endef

install-dev: build
	@command claude plugin marketplace remove $(LOCAL_MARKETPLACE) >/dev/null 2>&1 || true
	@command claude plugin marketplace add $(DIST)
	@for p in $(STALE_PLUGIN_NAMES); do \
		command claude plugin uninstall $$p@$(LOCAL_MARKETPLACE) >/dev/null 2>&1 || true; \
		command claude plugin uninstall $$p@academicOps >/dev/null 2>&1 || true; \
		command -v agy >/dev/null 2>&1 && agy plugin uninstall $$p >/dev/null 2>&1 || true; \
		rm -rf ~/.gemini/config/plugins/$$p; \
	done
	@for p in $(PLUGIN_NAMES); do \
		command claude plugin uninstall $$p@$(LOCAL_MARKETPLACE) >/dev/null 2>&1 || true; \
		command claude plugin uninstall $$p@academicOps >/dev/null 2>&1 || true; \
		command claude plugin uninstall aops-$$p@$(LOCAL_MARKETPLACE) >/dev/null 2>&1 || true; \
		command claude plugin uninstall aops-$$p@academicOps >/dev/null 2>&1 || true; \
		$(call claude_install,$$p,$(LOCAL_MARKETPLACE)); \
	done
	@mkdir -p ~/.gemini/config/plugins
	@for p in $(PLUGIN_NAMES); do \
		command -v agy >/dev/null 2>&1 && (agy plugin uninstall $$p >/dev/null 2>&1 || true; agy plugin uninstall "$$p" && echo "✓ agy $$p uninstalled" || echo "x agy $$p uninstall failed"); \
		rm -rf ~/.gemini/config/plugins/$$p ~/.gemini/config/plugins/aops-$$p; \
		if [ -d "$(DIST)/$$p-agy" ]; then \
			cp -R "$(DIST)/$$p-agy" ~/.gemini/config/plugins/$$p && echo "✓ ~/.gemini/config/plugins/$$p installed"; \
			command -v agy >/dev/null 2>&1 && (agy plugin install "$(DIST)/$$p-agy" >/dev/null 2>&1 && echo "✓ agy $$p installed" || true); \
		fi; \
	done || true
	@uv run python -m build.install install --dist-root $(DIST)
	@uv run pre-commit install >/dev/null 2>&1 || true
	@echo "Local marketplace '$(LOCAL_MARKETPLACE)' -> $(DIST). Run 'make uninstall-dev' to restore the release channel."

uninstall-dev:
	@for p in $(STALE_PLUGIN_NAMES) $(PLUGIN_NAMES); do \
		command claude plugin uninstall $$p@$(LOCAL_MARKETPLACE) >/dev/null 2>&1 || true; \
		command claude plugin uninstall aops-$$p@$(LOCAL_MARKETPLACE) >/dev/null 2>&1 || true; \
		command -v agy >/dev/null 2>&1 && (agy plugin uninstall $$p >/dev/null 2>&1 || true; agy plugin uninstall aops-$$p >/dev/null 2>&1 || true); \
		rm -rf ~/.gemini/config/plugins/$$p ~/.gemini/config/plugins/aops-$$p; \
	done
	@command claude plugin marketplace remove $(LOCAL_MARKETPLACE) >/dev/null 2>&1 || true
	@uv run python -m build.install uninstall
	@command claude plugin marketplace add $(DIST_REPO)
	@command claude plugin marketplace update academicOps
	@echo "✓ release marketplace restored"

install:
	@command claude plugin marketplace remove academicOps >/dev/null 2>&1 || true
	@command claude plugin marketplace add $(DIST_REPO)
	@command claude plugin marketplace update academicOps
	@for p in $(PLUGIN_NAMES); do $(call claude_install,$$p,academicOps); done

# --- Maintenance ---

clean-plugins:
	@uv run python scripts/clean_plugins.py

clean:
	@rm -rf $(DIST)
	@echo "✓ cleaned"

test:
	@uv run pytest tests/

# Mirrors the Lint and Type Check workflows. basedpyright is invoked exactly as
# .github/workflows/typecheck.yml invokes it, and is the only local entry point
# for it — without this line type errors only surface in CI.
lint:
	@uv run ruff check .
	@uv run python scripts/check_refs.py
	@uv run basedpyright
	@uv run pre-commit run gitleaks --all-files

format:
	@uv run ruff format .
	@uv run dprint fmt
