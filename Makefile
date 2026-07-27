# academicOps — build & install. Design: specs/ARCHITECTURE.md.

.PHONY: help build install-dev uninstall-dev install clean test lint format \
        docker docker-build docker-shell docker-push

ROOT := $(shell pwd)
DIST := $(ROOT)/dist
LOCAL_MARKETPLACE := aops
DIST_REPO := nicsuzor/academicOps@dist
# The image this repository publishes. Override to build/push elsewhere.
IMAGE ?= ghcr.io/nicsuzor/aops-crew

# Plugin marketplace names declared in build/marketplace.toml — the single
# source of truth for what ships (specs/ARCHITECTURE.md's plugin table).
PLUGIN_NAMES = $(shell uv run python -c "import tomllib, pathlib; d = tomllib.loads(pathlib.Path('build/marketplace.toml').read_text()); print(' '.join(p['name'] for p in d['plugins']))" 2>/dev/null)

help:
	@echo "make build          - assemble dist/ for every plugin, both clients (build/build.py)"
	@echo "make install-dev    - build, then install dist/ as the local '$(LOCAL_MARKETPLACE)' marketplace"
	@echo "make uninstall-dev  - remove the local marketplace, restore the released one"
	@echo "make install        - install the released plugins from the dist branch"
	@echo "make test           - run the pytest suite"
	@echo "make lint           - ruff check + documented-reference check"
	@echo "make format         - ruff format + dprint fmt"
	@echo "make clean          - remove dist/"
	@echo "make docker         - build the crew worker image"
	@echo "make docker-shell   - interactive shell in the crew image"
	@echo "make docker-push    - push the crew image to ghcr.io"

# --- Build ---

build:
	@uv run python -m build.build

# --- Install ---

# The pkb plugin ships a pkb_mcp_url userConfig field for the PKB MCP server
# URL (specs/ARCHITECTURE.md "No defaults" — the URL is never baked in, only
# forwarded from the environment). --config is only valid against the plugin
# that declares the key, so it's scoped to aops-pkb specifically.
define claude_install
	config=""; \
	if [ "$(1)" = "aops-pkb" ] && [ -n "$$PKB_MCP_URL" ]; then config="--config pkb_mcp_url=$$PKB_MCP_URL"; fi; \
	command claude plugin install $(1)@$(2) $$config && echo "✓ $(1)@$(2) installed" \
		|| { echo "x $(1)@$(2) install failed" >&2; exit 1; }
endef

install-dev: build
	@command claude plugin marketplace remove $(LOCAL_MARKETPLACE) >/dev/null 2>&1 || true
	@command claude plugin marketplace add $(DIST)
	@for p in $(PLUGIN_NAMES); do \
		command claude plugin uninstall $$p@$(LOCAL_MARKETPLACE) >/dev/null 2>&1 || true; \
		$(call claude_install,$$p,$(LOCAL_MARKETPLACE)); \
	done
	@command -v agy >/dev/null 2>&1 && for p in $(PLUGIN_NAMES); do \
		[ -d "$(DIST)/$$p-agy" ] && (agy plugin uninstall $$p >/dev/null 2>&1 || true; agy plugin install "$(DIST)/$$p-agy" && echo "✓ agy $$p installed" || echo "x agy $$p install failed"); \
	done || true
	@uv run python -m build.install install --dist-root $(DIST)
	@uv run pre-commit install >/dev/null 2>&1 || true
	@echo "Local marketplace '$(LOCAL_MARKETPLACE)' -> $(DIST). Run 'make uninstall-dev' to restore the release channel."

uninstall-dev:
	@for p in $(PLUGIN_NAMES); do command claude plugin uninstall $$p@$(LOCAL_MARKETPLACE) >/dev/null 2>&1 || true; done
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

lint:
	@uv run ruff check .
	@uv run python scripts/check_refs.py

format:
	@uv run ruff format .
	@uv run dprint fmt

# --- Docker ---

docker: docker-build

docker-build: build
	@docker build --build-arg AOPS_DIST_SOURCE=local -t $(IMAGE) -t $(notdir $(IMAGE)):latest .
	@echo "✓ built $(IMAGE)"

# The environment contract is defined once, in plugins/aops/polecat/env_contract.py,
# and shared with polecat's own `docker run` (specs/ARCHITECTURE.md "Observability").
# `-e NAME` forwards the host's value and sets nothing: a variable unset on the
# host stays unset in the container.
docker-shell: docker-build
	@env_args="$$(uv run python -m aops.polecat.env_contract --docker-args)" \
		|| { echo "x could not read the container env contract" >&2; exit 1; }; \
	docker run -it --rm $$env_args -v $(ROOT):/app -w /app $(IMAGE)

docker-push:
	@docker push $(IMAGE)
