# AcademicOps Makefile
# Unified build and installation entry point

.PHONY: help dev build-dev install-dev uninstall-dev install install-remote clean-local install-claude install-agy install-windows package-cowork package-cowork-windows install-cowork uninstall-cowork install-cli install-crontab install-hooks nextver release prerelease clean clean-plugins build build-docker build-docker-dev verify-docker shell docker-push

# --- Configuration ---

AOPS_ROOT := $(shell pwd)
DIST_DIR := $(AOPS_ROOT)/dist
INSTALL_BIN := $(if $(USER_OPT),$(USER_OPT)/bin,$(HOME)/.local/bin)
CRON_SCRIPT := $(AOPS_ROOT)/scripts/repo-sync-cron.sh
# The published plugins live on the `dist` BRANCH of the repo. The Claude
# marketplace source takes a `owner/repo@ref` string (DIST_REPO), but the release
# download URLs (DIST_REPO_URL, used by AGY_*_RELEASE_URL) must be the plain repo
# URL with NO branch ref. Keep them separate. NOTE: do NOT write the ref as
# `owner/repo#dist` — `#` starts a comment in both Make and the shell, so the ref
# is silently dropped and the wrong (default) branch gets used.
DIST_REPO_SLUG := nicsuzor/academicOps
DIST_REPO := $(DIST_REPO_SLUG)@dist
DIST_REPO_URL := https://github.com/$(DIST_REPO_SLUG)

# Extension names. The live `make install` flow no longer installs the
# deprecated Gemini CLI extension (see install / install-windows). Exactly two
# plugins ship: aops (core) + aops-tools. `aops-core`/`aops-pkb`/`aops-extras`
# are gone from source (folded into aops/ or never existed here) and are no
# longer installed by anything in this file.
CLAUDE_TOOLS_PLUGIN_NAME := aops-tools@academicOps
CLAUDE_AOPS_PLUGIN_NAME := aops@academicOps
# The full set of Claude plugins a live `make install` must successfully install.
# install-claude/install-windows loop over this list and HALT on the first
# failure — no per-plugin soft-fail exceptions.
CLAUDE_PLUGINS := $(CLAUDE_AOPS_PLUGIN_NAME) $(CLAUDE_TOOLS_PLUGIN_NAME)
# aops-ts is intentionally NOT auto-installed by any target here: it's an
# opt-in Tailscale bring-up hook for remote/cloud sessions (specs/build-and-install.md),
# and joining the tailnet / shipping transcripts should stay an explicit
# per-machine choice. Install it by hand: `claude plugin install aops-ts@academicOps`.

# Only the `aops` plugin declares the `pkb_mcp_url` userConfig option (see
# aops/templates/aops.template.json) — aops-tools has no userConfig at all, so
# `--config` must never be passed for it (the CLI validates --config keys
# against the target plugin's schema and errors on an unknown key). Each
# install loop below therefore checks the loop variable `$$p` against these
# names and only then forwards a set $$PKB_MCP_URL as the aops plugin's
# userConfig default, so a fresh install doesn't require a manual
# `/plugin configure` pass afterward.

# LOCAL-dev marketplace + plugin names. `make dev`/`make install-dev` register the
# built dist/ as a marketplace named `aops` (generated at dist/.claude-plugin/
# marketplace.json — see build.py generate_local_marketplace), so a local build is
# visibly DISTINCT from the released `academicOps` marketplace in `claude plugin
# marketplace list`. `make install`'s clean-local removes these so a live install
# is never shadowed by a prior `make dev`.
CLAUDE_LOCAL_MARKETPLACE := aops
CLAUDE_LOCAL_AOPS_PLUGIN_NAME := aops@aops
CLAUDE_LOCAL_TOOLS_PLUGIN_NAME := aops-tools@aops
CLAUDE_LOCAL_PLUGINS := $(CLAUDE_LOCAL_AOPS_PLUGIN_NAME) $(CLAUDE_LOCAL_TOOLS_PLUGIN_NAME)

# The local-dev cowork plugin lives in its OWN isolated marketplace + plugin
# namespace (`aops-coworklocal`) so a local install never clobbers the published
# `aops-cowork` plugin or the genuine `academicOps` marketplace. The published
# plugin is `aops-cowork` (dist/aops-cowork); the local copy is `aops-coworklocal`
# (dist/aops-coworklocal). See install-cowork / build_coworklocal_plugin.
CLAUDE_COWORK_MARKETPLACE := academicOps-cowork
CLAUDE_COWORK_PLUGIN_NAME := aops-coworklocal@academicOps-cowork
COWORK_DIST_DIR := $(DIST_DIR)/aops-coworklocal

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
	@echo "Two top-level install paths — dev (local source) and live (released dist)."
	@echo "Both cover Claude Code + Antigravity (agy) in one shot; install-agy/"
	@echo "install-claude are shared plumbing the two paths call, not separate paths."
	@echo ""
	@echo "Local Development (Install from source):"
	@echo "  make dev            - Full local dev setup (build, install-dev, install-hooks)"
	@echo "  make build-dev      - Build extension locally (dist/)"
	@echo "  make install-dev    - Install current dist/ into Claude Code + Antigravity (agy)"
	@echo "  make uninstall-dev  - Restore release marketplace after local testing"
	@echo "  make install-hooks  - Install pre-commit hooks"
	@echo ""
	@echo "Live Installation (Install from remote releases):"
	@echo "  make install        - Clean local installs, then install live plugins (Claude + agy) from the dist channel"
	@echo "  make clean-local    - Remove local/dev installs + marketplace override (run before a live install)"
	@echo "  make package-cowork - Build the Cowork upload zip (dist/aops-core-vX.Y.Z.zip)"
	@echo "  make install-cowork - Install aops-cowork locally from its isolated 'academicOps-cowork' marketplace"
	@echo "  make uninstall-cowork - Remove aops-cowork + its isolated marketplace"
	@echo "  make install-windows - (WSL only) Install into Windows-side Claude if present"
	@echo "  make install-crontab - Setup background sync"
	@echo ""
	@echo "Release Management:"
	@echo "  make nextver        - Show current build, next prerelease, stable source"
	@echo "  make release        - Cut a STABLE release via release-please (merge its PR)"
	@echo "  make prerelease     - Cut a beta tag (vX.Y.Z-beta.N; --prerelease Release + published to dist as a prerelease build)"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean          - Remove dist/ and prune stale plugin cache"
	@echo "  make clean-plugins  - Prune stale plugin cache versions + orphan manifests"
	@echo ""
	@echo "Docker:"
	@echo "  make build          - Build the aops crew worker image"
	@echo "  make verify-docker  - Build from clean (--no-cache) — required for verification; prevents false-green from cached layers"
	@echo "  make shell          - Interactive shell in the crew image"
	@echo "  make docker-push    - Push the docker image to ghcr.io"
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
	@echo "Validating Claude plugins..."
	@command -v claude >/dev/null 2>&1 && claude plugin validate $(DIST_DIR)/aops-claude || echo "  (claude not on PATH, skipping validation)"
	@command -v claude >/dev/null 2>&1 && claude plugin validate $(DIST_DIR)/aops-tools-claude || echo "  (claude not on PATH, skipping validation)"
	@echo "Verifying Antigravity plugins..."
	@command -v agy >/dev/null 2>&1 && agy plugin validate $(DIST_DIR)/aops-antigravity || echo "  (agy not on PATH, skipping verification)"
	@command -v agy >/dev/null 2>&1 && agy plugin validate $(DIST_DIR)/aops-tools-antigravity || echo "  (agy not on PATH, skipping verification)"
	@echo "✓ Build artifacts in $(DIST_DIR)"

# Install local build artifacts directly into BOTH Claude Code and Antigravity
# (agy) — this is the complete local-dev counterpart to `make install` (the
# live path); there is no separate third "install Antigravity for dev"
# step to remember. (scripts/install.py, which used to do the Claude side plus
# Gemini symlinks, cron jobs, and automode rules, has been retired — it drifted
# out of sync with the current source layout (aops-core folded into aops/,
# aops-extras/aops-pkb never existed here) and was unusable.)
#
# `install-agy` itself is shared, surface-agnostic plumbing: it prefers a local
# dist/aops-antigravity build when present (true here — build-dev just made
# one) and falls back to the live `dist` branch URL otherwise (true for `make
# install`, after clean-local deletes any local build). Same target, two
# different inputs depending on which top-level path calls it.
#
# NOTE: This overrides the release marketplace with a local directory source.
# Run `make uninstall-dev` to restore the release marketplace when done testing.
install-dev: build-dev
	@echo "Installing from local build artifacts into Claude Code..."
	@echo "  Source: $(DIST_DIR) (local marketplace)"
	@echo "Uninstalling existing local/released plugins..."
	@# Uninstall BOTH the local (`@aops`) and any released (`@academicOps`) copies so
	@# a dev install never double-loads alongside a release install.
	@for p in $(CLAUDE_LOCAL_PLUGINS) $(CLAUDE_PLUGINS); do command claude plugin uninstall $$p >/dev/null 2>&1 || true; done
	@echo "Pruning old plugin cache versions..."
	-python3 -c "\
import json, shutil, pathlib; \
f = pathlib.Path.home() / '.claude/plugins/installed_plugins.json'; \
data = json.load(open(f))['plugins'] if f.exists() else {}; \
active = {p.split('@')[0] for p in ['$(CLAUDE_LOCAL_AOPS_PLUGIN_NAME)', '$(CLAUDE_LOCAL_TOOLS_PLUGIN_NAME)']}; \
cache_root = pathlib.Path.home() / '.claude/plugins/cache/$(CLAUDE_LOCAL_MARKETPLACE)'; \
[shutil.rmtree(d) or print(f'  removed stale cache dir {d.name}') for d in (cache_root.iterdir() if cache_root.exists() else []) if d.is_dir() and d.name not in active] \
"
	@echo "Configuring local Claude marketplace '$(CLAUDE_LOCAL_MARKETPLACE)' (distinct from released 'academicOps')..."
	@# Remove any prior marketplace first — `marketplace add` no-ops when the name
	@# already exists (it will NOT re-point the source). Drop both the released
	@# `academicOps` name (so the dev build isn't shadowed by a release source) and a
	@# stale `aops` name (so its source is re-pointed at the fresh build).
	-command claude plugin marketplace remove academicOps >/dev/null 2>&1 || true
	-command claude plugin marketplace remove $(CLAUDE_LOCAL_MARKETPLACE) >/dev/null 2>&1 || true
	@# Add dist/ as the marketplace: dist/.claude-plugin/marketplace.json names it
	@# `aops` and sources ./aops-* (see build.py generate_local_marketplace) —
	@# only plugins that were actually built are listed.
	@command claude plugin marketplace add $(DIST_DIR)
	@for p in $(CLAUDE_LOCAL_PLUGINS); do \
		pkb_config_args=""; \
		if [ "$$p" = "$(CLAUDE_LOCAL_AOPS_PLUGIN_NAME)" ] && [ -n "$$PKB_MCP_URL" ]; then \
			pkb_config_args="--config pkb_mcp_url=$$PKB_MCP_URL"; \
		fi; \
		command claude plugin install $$p $$pkb_config_args && echo "✓ $$p installed" \
			|| { echo "  x $$p install failed" >&2; exit 1; }; \
	done
	@$(MAKE) install-agy
	@echo "Merging aops axiom rules into ~/.claude/settings.json (best-effort)..."
	@uv run python scripts/install_automode.py || true
	@$(MAKE) report-versions
	@echo "✓ Local installation complete"
	@echo "  ⚠️  Local marketplace '$(CLAUDE_LOCAL_MARKETPLACE)' now points to $(DIST_DIR) (plugins: $(CLAUDE_LOCAL_PLUGINS))"
	@echo "  Run 'make uninstall-dev' to restore the release marketplace."

# Restore the release marketplace after local dev testing
uninstall-dev:
	@echo "Removing local '$(CLAUDE_LOCAL_MARKETPLACE)' marketplace + plugins..."
	@for p in $(CLAUDE_LOCAL_PLUGINS); do command claude plugin uninstall $$p >/dev/null 2>&1 || true; done
	@command claude plugin marketplace remove $(CLAUDE_LOCAL_MARKETPLACE) >/dev/null 2>&1 || true
	@echo "Restoring release marketplace ($(DIST_REPO))..."
	@command claude plugin marketplace add $(DIST_REPO)
	@command claude plugin marketplace update academicOps
	@for p in $(CLAUDE_PLUGINS); do \
		pkb_config_args=""; \
		if [ "$$p" = "$(CLAUDE_AOPS_PLUGIN_NAME)" ] && [ -n "$$PKB_MCP_URL" ]; then \
			pkb_config_args="--config pkb_mcp_url=$$PKB_MCP_URL"; \
		fi; \
		command claude plugin install $$p $$pkb_config_args; \
	done
	@echo "✓ Release marketplace restored"

# Install pre-commit hooks
install-hooks:
	@echo "Installing pre-commit hooks..."
	@uv run pre-commit install
	@echo "✓ Pre-commit hooks installed"

# --- User Installation (Remote) ---

# Standard user install from official releases.
# Cowork is intentionally excluded from this chain: personal Anthropic accounts
# can't add custom marketplaces, so the `aops-coworklocal` plugin must be uploaded
# manually via the Claude desktop app (Customize → Add plugins → Upload a
# file). Run `make package-cowork` to produce the zip, then upload it through
# the UI. (Note: `aops-coworklocal` is a distinct plugin from `aops-core`, with
# Cowork-specific behaviour for the PKB ↔ native task-list mirror — see
# `aops-core/skills/cowork-sync/SKILL.md`.)
# Live install. Clears any local/dev installs FIRST (clean-local) so a prior
# `make install-dev` can't shadow the release build, then installs the live
# plugins. The two CORE surfaces — Claude + agy — run first and HALT the chain if
# their core plugin fails to install (that's the point of `make install`: prove
# it works). The trailing surfaces (docker image, Windows-side Claude, crontab)
# are optional and self-tolerant. The deprecated Gemini CLI is
# intentionally NOT in this chain.
install: clean-local install-claude install-agy ensure-docker install-windows install-crontab
	@$(MAKE) report-versions

# Remove every LOCAL/dev install so a subsequent live `make install` is from a
# clean slate and cannot be shadowed by a local build:
#  - Uninstalls the Claude + agy plugins.
#  - Removes the `academicOps` Claude marketplace. This is REQUIRED, not cosmetic:
#    `claude plugin marketplace add` no-ops when the name already exists (it will
#    NOT re-point the source), so a local-dir override left by `make install-dev`
#    would otherwise survive and `make install` would reinstall the LOCAL build.
#    install-claude re-adds the live $(DIST_REPO) source from scratch.
#  - Deletes the local Antigravity build dirs so install-agy falls through to the
#    live `dist` branch URL instead of preferring dist/aops-antigravity.
# Leaves the rest of dist/ (e.g. cowork zips) untouched — use `make clean` for that.
# Teardown is idempotent and quiet: uninstalling/removing something already absent
# is expected, so those are silenced (|| true) rather than surfaced as scary errors.
clean-local:
	@echo "--- 🧹 Clearing local/dev installs ---"
	@# Local dev build (`@aops` marketplace, from `make dev`) — remove its plugins and
	@# marketplace so this live install is never shadowed by a prior local build.
	@for p in $(CLAUDE_LOCAL_PLUGINS); do command claude plugin uninstall $$p >/dev/null 2>&1 || true; done
	@command claude plugin marketplace remove $(CLAUDE_LOCAL_MARKETPLACE) >/dev/null 2>&1 || true
	@# Released install + any legacy local-dir override that reused the `academicOps` name.
	@for p in $(CLAUDE_PLUGINS); do command claude plugin uninstall $$p >/dev/null 2>&1 || true; done
	@command claude plugin marketplace remove academicOps >/dev/null 2>&1 || true
	@command -v agy >/dev/null 2>&1 && for p in $(AGY_PLUGINS); do agy plugin uninstall $$p >/dev/null 2>&1 || true; done || true
	@rm -rf "$(DIST_DIR)/aops-antigravity" "$(DIST_DIR)/aops-tools-antigravity"
	@# `agy plugin uninstall` only knows about plugins IT installed (via its own
	@# copy-based `agy plugin install`); it has no record of any symlinks a prior
	@# dev workflow may have dropped at these same paths pointing at
	@# dist/aops-antigravity — now deleted above. Strip only symlinks (never a
	@# real agy-installed copy) so a stale/dangling dev link can never shadow or
	@# collide with the live install-agy run that follows.
	@for d in "$(HOME)/.gemini/config/plugins" "$(HOME)/.gemini/antigravity-cli/plugins"; do \
		for p in aops aops-tools; do \
			[ -L "$$d/$$p" ] && rm -f "$$d/$$p" && echo "  removed stale dev symlink $$d/$$p"; \
		done; \
	done; true
	@echo "✓ Local installs cleared"

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

# Every plugin in $(CLAUDE_PLUGINS) is a hard dependency — HALT on the first
# failure (Nic ruling 2026-07-12: no more soft-fail/warn-and-continue for any
# plugin). A missing plugin asset means the dist build is broken; that must
# stop the install, not degrade silently into a partial one.
install-claude:
	@echo "Installing aops plugins for Claude Code..."
	@echo "  Source: $(DIST_REPO_URL)"
	@echo "  Plugins: $(CLAUDE_PLUGINS)"
	@# Idempotent, quiet teardown (uninstalling something absent is expected).
	@for p in $(CLAUDE_PLUGINS); do command claude plugin uninstall $$p >/dev/null 2>&1 || true; done
	@# Force the academicOps marketplace to the LIVE dist repo. `marketplace add`
	@# no-ops when the name already exists (it will NOT re-point an existing
	@# source), so remove any prior source first — e.g. a local-dir override left
	@# by `make install-dev` — then re-add the release source from scratch.
	@command claude plugin marketplace remove academicOps >/dev/null 2>&1 || true
	@command claude plugin marketplace add $(DIST_REPO)
	@command claude plugin marketplace update academicOps
	@for p in $(CLAUDE_PLUGINS); do \
		pkb_config_args=""; \
		if [ "$$p" = "$(CLAUDE_AOPS_PLUGIN_NAME)" ] && [ -n "$$PKB_MCP_URL" ]; then \
			pkb_config_args="--config pkb_mcp_url=$$PKB_MCP_URL"; \
		fi; \
		command claude plugin install $$p $$pkb_config_args && echo "✓ Claude Code $$p installed" \
			|| { echo "  x Claude $$p install failed — could not install from $(DIST_REPO_URL) marketplace" >&2; exit 1; }; \
	done


# Cowork on personal accounts has no marketplace mechanism. The Cowork plugin
# is a SEPARATE build (`aops-coworklocal`) from the Claude Code CLI build (`aops-core`):
# same Claude-shaped layout, but with cowork-only skill blocks kept and the
# `cowork-sync` skill bundled. See `build_aops_core(platform="cowork", ...)` in
# scripts/build.py and `aops-core/skills/cowork-sync/SKILL.md` for the PKB
# ↔ native task-list mirror behaviour. The legacy `aops-core-v{VERSION}.zip`
# name is preserved as a symlink for backwards compatibility with any existing
# download URLs.
package-cowork: build-dev
	@echo "Cowork upload package built at:"
	@ls -1 $(DIST_DIR)/aops-coworklocal-v*.zip 2>/dev/null | tail -1 || \
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
	ZIP=$$(ls -1t $(DIST_DIR)/aops-coworklocal-v*.zip 2>/dev/null | head -1); \
	if [ -z "$$ZIP" ]; then \
		ZIP=$$(ls -1t $(DIST_DIR)/aops-cowork-v*.zip 2>/dev/null | head -1); \
	fi; \
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

# Local install of the Cowork plugin from its OWN isolated marketplace.
# Unlike `install-dev` (which legitimately overrides the genuine `academicOps`
# marketplace with a newer build of the SAME aops-core plugin), the cowork build
# is a DISTINCT plugin. This target registers a SEPARATE marketplace named
# `academicOps-cowork` (containing only `aops-cowork`) and installs from it, so
# it never adds/updates/replaces `academicOps` and never installs
# aops-core/aops-tools. Running it leaves any genuine `academicOps` marketplace
# fully intact. The marketplace source is a local DIRECTORY (dist/aops-cowork),
# which survives Cowork restarts — github-source marketplaces get nuked on every
# restart (RemotePluginManager.syncPlugins; cf. claude-code issues #38429/#40600).
install-cowork: build-dev
	@echo "Installing aops-cowork from isolated marketplace '$(CLAUDE_COWORK_MARKETPLACE)'..."
	@echo "  Marketplace source: $(COWORK_DIST_DIR) (local directory)"
	-command claude plugin uninstall $(CLAUDE_COWORK_PLUGIN_NAME)
	@command claude plugin marketplace add $(COWORK_DIST_DIR)
	@command claude plugin install $(CLAUDE_COWORK_PLUGIN_NAME) \
		&& echo "✓ aops-cowork installed from '$(CLAUDE_COWORK_MARKETPLACE)'" \
		|| { echo "  ⚠️ aops-cowork install failed" >&2; exit 1; }

# Remove the cowork plugin and its isolated marketplace. Touches ONLY the
# academicOps-cowork namespace — leaves `academicOps`/aops-core/aops-tools alone.
uninstall-cowork:
	@echo "Removing aops-cowork and its isolated marketplace '$(CLAUDE_COWORK_MARKETPLACE)'..."
	-command claude plugin uninstall $(CLAUDE_COWORK_PLUGIN_NAME)
	-command claude plugin marketplace remove $(CLAUDE_COWORK_MARKETPLACE)
	@echo "✓ aops-cowork + '$(CLAUDE_COWORK_MARKETPLACE)' removed"

# Install into Antigravity CLI (agy) via agy's OFFICIAL `agy plugin install`
# command — no hand-copying of plugin source. agy has no user-addable marketplace
# (its marketplaces are built into the binary), so third-party plugins install
# from either:
#   - a local directory:  agy plugin install <dir>
#   - a GitHub URL:        agy plugin install https://github.com/<o>/<r>/tree/<branch>/<subpath>
# In the URL form, agy clones the repo, checks out <branch>, locates the plugin in
# <subpath>, and converts/installs it. We point at the `dist` BRANCH — the SAME
# live channel the Claude marketplace uses, always current. (The release
# `/releases/latest/download/` assets are NOT usable: GitHub's "latest" excludes
# prereleases, and the antigravity assets only attach to prerelease builds.)
# For LOCAL dev (dist/aops-antigravity present) install straight from that dir.
# NOTE: plugin dirs live at the dist BRANCH ROOT (dist:aops-antigravity), not
# under a nested dist/ subpath — see build-extension.yml's "Publish
# distribution to dist" step.
AGY_CORE_URL  := https://github.com/$(DIST_REPO_SLUG)/tree/dist/aops-antigravity
AGY_TOOLS_URL := https://github.com/$(DIST_REPO_SLUG)/tree/dist/aops-tools-antigravity
# Exactly two plugins ship for agy too — aops + aops-tools, both hard
# dependencies (no soft-fail exception for either).
AGY_PLUGINS := aops aops-tools

install-agy:
	@if ! command -v agy >/dev/null 2>&1; then \
		echo "  (agy not found on PATH — skipping Antigravity install)"; \
		exit 0; \
	fi
	@echo "Installing aops plugins into Antigravity CLI (agy): $(AGY_PLUGINS)"
	@for p in $(AGY_PLUGINS); do agy plugin uninstall $$p >/dev/null 2>&1 || true; done
	@for p in $(AGY_PLUGINS); do \
		case $$p in \
			aops) local_dir="$(DIST_DIR)/aops-antigravity"; url="$(AGY_CORE_URL)" ;; \
			aops-tools) local_dir="$(DIST_DIR)/aops-tools-antigravity"; url="$(AGY_TOOLS_URL)" ;; \
		esac; \
		if [ -d "$$local_dir" ]; then \
			echo "  Source ($$p): $$local_dir (local build)"; \
			agy plugin install "$$local_dir" && echo "✓ agy $$p installed" \
				|| { echo "  x agy $$p install failed" >&2; exit 1; }; \
		else \
			agy plugin install "$$url" && echo "✓ agy $$p installed" \
				|| { echo "  x agy $$p install failed" >&2; exit 1; }; \
		fi; \
	done

# Optional: install into Windows-side Claude when invoked from WSL.
# Silently no-ops outside WSL or when no Windows Claude is found.
# Set AOPS_SKIP_WINDOWS=1 to opt out even when WSL + Windows Claude is present.
install-windows:
	@if [ -n "$$AOPS_SKIP_WINDOWS" ]; then \
		echo "Skipping Windows-side install (AOPS_SKIP_WINDOWS set)"; \
		exit 0; \
	fi; \
	if [ ! -d /mnt/c ] || ! grep -qi microsoft /proc/version 2>/dev/null; then \
		exit 0; \
	fi; \
	echo "--- 🪟  WSL detected — checking for Windows-side Claude ---"; \
	if (cd /mnt/c && cmd.exe /c "where claude" >/dev/null 2>&1); then \
		echo "Installing aops plugins into Windows Claude: $(CLAUDE_PLUGINS)"; \
		(cd /mnt/c && cmd.exe /c "claude plugin marketplace add $(DIST_REPO)" 2>&1 | grep -v -E '^(UNC paths|Defaulting to)' || true); \
		(cd /mnt/c && cmd.exe /c "claude plugin marketplace update academicOps" 2>&1 | grep -v -E '^(UNC paths|Defaulting to)' || true); \
		for p in $(CLAUDE_PLUGINS); do \
			(cd /mnt/c && cmd.exe /c "claude plugin install $$p" 2>&1 | grep -v -E '^(UNC paths|Defaulting to)') \
				&& echo "✓ Windows Claude $$p installed" \
				|| { echo "  x Windows Claude $$p install failed" >&2; exit 1; }; \
		done; \
	else \
		echo "  (no Windows-side claude found — skipping)"; \
	fi

report-versions:
	@echo "--- 📋 Installed Versions ---"
	@echo "Claude plugins:"
	@-claude plugin list 2>&1 || true
	@echo "Antigravity (agy) plugins:"
	@-command -v agy >/dev/null 2>&1 && agy plugin list 2>&1 || echo "  (agy not on PATH)"

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
#
# Stable versions are owned by release-please. As Conventional-Commit changes land
# on `dev`, release-please maintains a release PR; merging it tags vX.Y.Z, which
# build-extension.yml builds and publishes to `main` (the stable install channel).
# `make release` merges that PR. Prereleases are separate: `make prerelease` cuts a
# vX.Y.Z-beta.N tag that ships ONLY as a `--prerelease` GitHub Release (main left
# untouched) — see build-extension.yml's tag-shape classification.

# Show the version picture: current build, next prerelease tag, where stable comes from.
nextver:
	@cur=$$(uv run python scripts/version.py --get); \
	pre=$$(uv run python scripts/version.py --prerelease beta); \
	echo "Current build:    $$cur"; \
	echo "Next prerelease:  v$$pre   ->  make prerelease"; \
	echo "Next stable:      via release-please  ->  make release"

# Cut a STABLE release by merging release-please's open dev release PR. release-
# please then tags vX.Y.Z (with AOPS_DIST_PAT) and build-extension.yml builds +
# publishes the distribution to main. Only a dev-targeted release-please PR is
# valid here; a stray `release-please--branches--main` PR is ignored (main is the
# published dist branch, never a PR base).
release:
	@command -v gh >/dev/null 2>&1 || { echo "x gh CLI not found — needed to drive release-please."; exit 1; }; \
	pr=$$(gh pr list --state open --base dev --json number,headRefName \
	      --jq '[.[] | select(.headRefName | startswith("release-please"))][0].number // empty'); \
	if [ -z "$$pr" ]; then \
	  echo "No open dev-targeted release-please PR to merge."; \
	  echo; \
	  echo "  release-please opens the release PR automatically as commits land on dev."; \
	  echo "  If none is open, either nothing release-worthy has landed, or release-"; \
	  echo "  please state is out of sync (manifest behind the shipped tags)."; \
	  echo; \
	  echo "  Force a version (runs release-please on dev, NOT main):"; \
	  echo "    gh workflow run release-please.yml --ref dev -f release_as=X.Y.Z"; \
	  exit 1; \
	fi; \
	title=$$(gh pr view $$pr --json title --jq .title); \
	echo "Merging release-please PR #$$pr — $$title"; \
	gh pr merge $$pr --merge \
	  && echo "Merged #$$pr. release-please will tag the release; build-extension.yml then builds + publishes to main." \
	  || { echo "x Merge blocked (branch protection / checks). Retry: gh pr merge $$pr --merge --admin"; exit 1; }

# Cut a beta/testing release for testers. Pushes a vX.Y.Z-<label>.N tag on the
# CURRENT commit; build-extension.yml classifies the '-' suffix as a prerelease,
# builds installable assets into a `--prerelease` GitHub Release, and leaves main
# (the stable channel) untouched. release-please is intentionally NOT involved.
#   make prerelease                 # next patch above latest stable in series, beta.N
#   make prerelease LABEL=rc        # use rc.N instead of beta.N
#   make prerelease VERSION=0.4.0   # force the base version (still auto-increments .N)
LABEL ?= beta
prerelease:
	@branch=$$(git rev-parse --abbrev-ref HEAD); \
	head=$$(git rev-parse --short HEAD); \
	if [ -n "$(VERSION)" ]; then \
	  tag="v$$(uv run python scripts/version.py --prerelease $(LABEL) --base $(VERSION))"; \
	else \
	  tag="v$$(uv run python scripts/version.py --prerelease $(LABEL))"; \
	fi; \
	if git rev-parse -q --verify "refs/tags/$$tag" >/dev/null; then \
	  echo "x Tag $$tag already exists locally."; exit 1; \
	fi; \
	echo "Prerelease $$tag  (commit $$head on $$branch)"; \
	if git rev-parse -q --verify "origin/$$branch" >/dev/null 2>&1 \
	   && ! git merge-base --is-ancestor HEAD "origin/$$branch"; then \
	  echo "!  HEAD is ahead of origin/$$branch — push your branch first if you want this commit on $$branch (the tag still carries it)."; \
	fi; \
	git tag "$$tag" && git push origin "$$tag" \
	  && echo "Pushed $$tag → build-extension.yml cuts a --prerelease Release + publishes to dist (semver prerelease; clients opt in to dev builds)."

# --- Docker ---

DOCKER_IMAGE := ghcr.io/nicsuzor/aops-crew
SANDBOX_IMAGE := $(DOCKER_IMAGE)

# Build the Docker image used for crew/worker agent environments and Gemini sandboxing.
#
# AOPS_DIST_SOURCE=local: builds from THIS checkout's dist/ output (rebuilt
# fresh via build-dev first) rather than cloning the published `dist` branch,
# so local builds always reflect current source instead of whatever last
# shipped (which can lag — see #2208). CI (build-extension.yml) doesn't pass
# AOPS_DIST_SOURCE, so it keeps the `remote` default and clones the branch it
# just published.
#
# CLAUDE_CODE_VERSION/RUST_CACHEBUST bust their layer cache once per calendar
# day (not once per build) so Claude Code and Rust — and, via the framework
# install's hard dependency on a fresh `claude` binary, the aops plugin
# install — don't reinstall on every local build. Pass an explicit version to
# pin, or `make docker-refresh-tools` to force an immediate refresh.
build-docker: build-dev
	@echo "Building aops crew image..."
	@docker build --build-arg AOPS_DIST_SOURCE=local --build-arg CLAUDE_CODE_VERSION=$$(date +%Y%m%d) --build-arg RUST_CACHEBUST=$$(date +%Y%m%d) -t $(DOCKER_IMAGE) -t $(notdir $(DOCKER_IMAGE)):latest .
	@echo "✓ Image built: $(DOCKER_IMAGE) (also tagged $(notdir $(DOCKER_IMAGE)):latest)"
	@echo "  Use with: GEMINI_SANDBOX_IMAGE=$(DOCKER_IMAGE) gemini --sandbox"

# Build a DEV-ONLY image tagged `:dev`, never `:latest`/bare $(DOCKER_IMAGE) —
# real polecats pull the bare/`:latest` tag (see build-docker above), so this
# target must never touch it. Used by scripts/dev-crew.sh for the live-editing
# dev loop (tests/harness/README.md § "Dev-loop"). Same AOPS_DIST_SOURCE=local
# build as build-docker; only the `-t` flags differ.
build-docker-dev: build-dev
	@echo "Building aops crew DEV image (tag :dev only — does not touch :latest)..."
	@docker build --build-arg AOPS_DIST_SOURCE=local --build-arg CLAUDE_CODE_VERSION=$$(date +%Y%m%d) --build-arg RUST_CACHEBUST=$$(date +%Y%m%d) -t $(DOCKER_IMAGE):dev .
	@echo "✓ Image built: $(DOCKER_IMAGE):dev ($(DOCKER_IMAGE):latest untouched)"

# Force an immediate Claude Code / Rust refresh without a full --no-cache rebuild.
docker-refresh-tools: build-dev
	@echo "Refreshing Claude Code + Rust in aops crew image..."
	@docker build --build-arg AOPS_DIST_SOURCE=local --build-arg CLAUDE_CODE_VERSION=$$(date +%s) --build-arg RUST_CACHEBUST=$$(date +%s) -t $(DOCKER_IMAGE) -t $(notdir $(DOCKER_IMAGE)):latest .
	@echo "✓ Image refreshed: $(DOCKER_IMAGE)"

# Build from a clean checkout — required when verifying Dockerfile changes.
# --no-cache forces every layer to rebuild from source: a stale cached layer
# cannot produce a false-green result (issue #1452).
verify-docker:
	@echo "Building aops crew image (clean build — no layer cache)..."
	@docker build --no-cache --build-arg CLAUDE_CODE_VERSION=$$(date +%s) --build-arg RUST_CACHEBUST=$$(date +%s) -t $(DOCKER_IMAGE) -t $(notdir $(DOCKER_IMAGE)):latest .
	@echo "✓ Clean build complete: $(DOCKER_IMAGE)"
	@echo "  Every Dockerfile layer rebuilt from source — no cached layer can produce a false-green result."
	@echo "  Use with: GEMINI_SANDBOX_IMAGE=$(DOCKER_IMAGE) gemini --sandbox"

# Aliases
build: build-docker
build-sandbox: build-docker

docker-push:
	@echo "Pushing aops crew image..."
	@docker push $(DOCKER_IMAGE)
	@echo "✓ Image pushed: $(DOCKER_IMAGE)"

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
