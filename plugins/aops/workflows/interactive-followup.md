---
title: Interactive Follow-up
type: template
category: process
description: Streamlined flow for bounded follow-up requests within an active session. Select when continuing recent in-context work where background is already established. Not for new goals or cross-session epics (use standard capture/decompose pipeline).
tags: [session, followup, interactive, lightweight, process]
---

# Process: Interactive Follow-up

Fast incremental modification workflow within an established session context.

## 1. Delta Scoping

- Identify the specific incremental modification, clarification, or check requested (`<request>`).
- Reuse active session context without re-running full intake or graph hydration.

## 2. Targeted Execution

- Apply minimal, precise edits or run requested commands directly on `<target-artifact>`.
- Maintain existing architecture and conventions established in current session.

## 3. Direct Verification

- Execute targeted verification checks (`<verification-command>`) to confirm the specific change works.
- Check for unintended side-effects on adjacent components.

## 4. Response

- Report outcome directly to user with concise diff summary or command output.
