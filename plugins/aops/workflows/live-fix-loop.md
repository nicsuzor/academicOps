---
title: Live Fix Loop
type: template
category: process
description: Reproduction, isolation, and fix cycle for defects that only manifest in deployed or live runtimes (e.g. Docker containers, browser interfaces, remote hosts). Select when a bug cannot be reproduced in isolated unit tests. Not for unit-testable defects (use `feature-dev`).
tags: [debugging, live-runtime, containers, deployed, fix-loop, process]
---

# Process: Live Fix Loop

Rapid diagnosis and verification cycle for defects observable only within a running container, remote host, or deployed service.

## 1. Live Symptom Capture

- Drive the deployed artifact in `<target-runtime>` to trigger the defect.
- Capture verbatim failure evidence: runtime logs, network traces, console errors, or screenshots.
- Establish the baseline failure state before making workspace modifications.

## 2. Environment and Isolation Analysis

- Identify differences between local test environment and live runtime: environment variables, filesystem paths, permissions, service dependencies, or timing.
- Trace the defect to specific configuration or code discrepancies in the live runtime.

## 3. Targeted Patch Implementation

- Apply the minimal code or configuration change in the workspace to address the identified runtime failure.
- Ensure the fix preserves local test suite compatibility.

## 4. Live Rebuild and Re-Verification

- Rebuild and redeploy the target container or service using `<rebuild-command>`.
- Re-run the exact live reproduction procedure from step 1 against the fresh deployment.
- Confirm the defect is resolved and no secondary failures appear in runtime logs.

## 5. Handover

- Run local regression test suite to ensure no side effects.
- Compose `wf-handover` with evidence from both live runtime verification and local test passes.
