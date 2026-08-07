# academicOps — build & install. Design: specs/ARCHITECTURE.md.

.PHONY: help build build-test install-dev uninstall-dev install clean test lint format \
        docker docker-build docker-shell docker-push docker-test-otel docker-smoke-test \
        verify-docker

ROOT := $(shell pwd)
DIST := $(ROOT)/dist
LOCAL_MARKETPLACE := aops
DIST_REPO := nicsuzor/academicOps@dist
# The image this repository publishes. Override to build/push elsewhere.
IMAGE ?= ghcr.io/nicsuzor/aops-crew

# Plugin marketplace names declared in build/marketplace.toml — the single
# source of truth for what ships (specs/ARCHITECTURE.md's plugin table).
PLUGIN_NAMES = $(shell uv run python -c "import tomllib, pathlib; d = tomllib.loads(pathlib.Path('build/marketplace.toml').read_text()); print(' '.join(p['name'] for p in d['plugins']))" 2>/dev/null)
STALE_PLUGIN_NAMES = aops aops-cope aops-core aops-extras aops-ida aops-jr aops-pkb aops-tools aops-ts

help:
	@echo "make build          - assemble dist/ for every plugin, both clients (build/build.py)"
	@echo "make build-test     - build, then validate every dist/ plugin dir with"
	@echo "                      'claude plugin validate' and 'agy plugin validate'"
	@echo "make install-dev    - build, then install dist/ as the local '$(LOCAL_MARKETPLACE)' marketplace"
	@echo "make uninstall-dev  - remove the local marketplace, restore the released one"
	@echo "make install        - install the released plugins from the dist branch"
	@echo "make test           - run the pytest suite"
	@echo "make lint           - ruff check + documented-reference check + basedpyright"
	@echo "make format         - ruff format + dprint fmt"
	@echo "make clean          - remove dist/"
	@echo "make docker         - build the crew worker image"
	@echo "make docker-shell   - interactive shell in the crew image"
	@echo "make docker-push    - push the crew image to ghcr.io"
	@echo "make docker-test-otel - build the image, then prove native OTel export"
	@echo "                        actually reaches a throwaway collector"
	@echo "make docker-smoke-test - build the image, then run its structural"
	@echo "                        smoke test (plugin list, agy plugins, ACA_DATA)"
	@echo "make verify-docker  - clean (--no-cache) image build; required before"
	@echo "                        certifying a change, so no cached layer can"
	@echo "                        produce a false-green result"

# --- Build ---

build:
	@uv run python -m build.build

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
		if command -v agy >/dev/null 2>&1; then \
			agy plugin validate "$(DIST)/$$p-agy" \
				&& echo "✓ agy $$p validated" \
				|| { echo "x agy $$p validate failed" >&2; exit 1; }; \
		fi; \
	done
	@echo "✓ dist/ validated for every plugin, both clients"

# --- Install ---

# Claude Code plugins can define `userConfig` fields for things like MCP server
# URLs (e.g. `pkb_mcp_url`). If the environment has a matching upper-case
# variable (e.g. `PKB_MCP_URL`), we forward it automatically.
define claude_install
	config=""; \
	if [ -f "$(DIST)/$(1)-claude/.claude-plugin/plugin.json" ]; then \
		keys=$$(uv run python -c "import json, pathlib; d=json.loads(pathlib.Path('$(DIST)/$(1)-claude/.claude-plugin/plugin.json').read_text()); print(' '.join(d.get('userConfig', {}).keys()))" 2>/dev/null); \
		for k in $$keys; do \
			env_k=$$(echo $$k | tr '[:lower:]' '[:upper:]'); \
			val=$$(eval echo \$$$$env_k); \
			if [ -n "$$val" ]; then config="$$config --config $$k=$$val"; fi; \
		done; \
	fi; \
	command claude plugin install $(1)@$(2) $$config && echo "✓ $(1)@$(2) installed" \
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
		command -v agy >/dev/null 2>&1 && (agy plugin uninstall $$p >/dev/null 2>&1 || true; agy plugin uninstall "$(DIST)/$$p-agy" && echo "✓ agy $$p installed" || echo "x agy $$p install failed"); \
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

format:
	@uv run ruff format .
	@uv run dprint fmt

# --- Docker ---

docker: docker-build

docker-build: build
	@docker build --build-arg AOPS_DIST_SOURCE=local -t $(IMAGE) -t $(notdir $(IMAGE)):latest .
	@echo "✓ built $(IMAGE)"

# The environment contract is defined once, in lib/polecat/env_contract.py,
# and shared with polecat's own `docker run` (specs/ARCHITECTURE.md "Observability").
# `-e NAME` forwards the host's value and sets nothing: a variable unset on the
# host stays unset in the container.
docker-shell: docker-build
	@env_args="$$(uv run python -m lib.polecat.env_contract --docker-args)" \
		|| { echo "x could not read the container env contract" >&2; exit 1; }; \
	docker run -it --rm $$env_args -v $(ROOT):/app -w /app $(IMAGE)

# The build to certify a dev change against. `docker-build` reuses the layer
# cache, so a layer whose inputs Docker judges unchanged is carried forward —
# and an image that looks rebuilt while still holding the previous plugin set
# reads as a pass that proves nothing. `--no-cache` rebuilds every layer from
# source, which is the only form of this build whose green result is evidence.
# Slow by construction; use `docker-build` for the edit loop and this before
# certifying.
verify-docker: build
	@docker build --no-cache --build-arg AOPS_DIST_SOURCE=local -t $(IMAGE) -t $(notdir $(IMAGE)):latest .
	@echo "✓ clean build: $(IMAGE) — every layer rebuilt from source"

docker-push:
	@docker push $(IMAGE)

# Not part of `make docker` or `make test` — opt-in, on the image-build path.
# Proves Claude Code's native OpenTelemetry export actually reaches a
# collector once the image is built, rather than only asserting the env
# contract's flags were constructed correctly (tests/test_telemetry_otel_e2e.py).
docker-test-otel: docker-build
	@uv run pytest -m otel_e2e tests/test_telemetry_otel_e2e.py -v

# Not part of `make docker` or `make test` — opt-in, on the image-build path.
# Boots the real image and re-runs the structural checks a human previously
# ran by hand (plugin list under claude, agy's plugins/, ACA_DATA, the agy
# session mount target); see tests/polecat/test_container_smoke.py and
# specs/polecat/tmux-interactive-driving.md, "Plugin structural check". Not
# proof any plugin's hooks or MCP servers are actually live — structural only.
docker-smoke-test: docker-build
	@POLECAT_E2E=1 POLECAT_IMAGE=$(notdir $(IMAGE)):latest uv run pytest tests/polecat/test_container_smoke.py -v
