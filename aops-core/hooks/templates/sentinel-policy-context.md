---
name: sentinel-policy-context
title: Sentinel — Destructive Op Context
category: template
description: |
  Context injection when the sentinel gate blocks a destructive operation
  targeting a protected user environment path (extensions, plugins, config).
  Guides the agent toward evidence-based investigation.
---

BLOCKED: You attempted a destructive operation (rm, mv, rmdir, unlink) on a protected user environment path.

Protected paths include:

- ~/.gemini/extensions/ — Gemini extension installations (installed from GitHub releases via `gemini extensions install`)
- ~/.claude/plugins/ — Claude plugin installations
- ~/.claude/*.json — Claude configuration files
- ~/.gemini/settings.json — Gemini configuration
- ~/.config/gemini/ — Gemini config (alternate location)

Before performing destructive operations on these paths, you MUST:

1. Provide documented evidence that the target is actually broken (not just theorized to be broken)
2. Inspect the build/install pipeline first (GitHub Actions, build scripts, Makefile) — not the installation path
3. Get explicit user confirmation before proceeding

Do NOT guess about installation paths or reinstall from wrong sources. If the user says it works, it works.
