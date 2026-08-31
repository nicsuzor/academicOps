---
title: Session Hook Forensics
type: template
category: process
description: Forensic diagnosis and verification of session hook execution, context injection, and handler lifecycle. Select when debugging hook failures or transcript injection bugs.
tags: [hooks, forensics, debugging, session-start, lifecycle, process]
---

# Process: Session Hook Forensics

Diagnostic workflow for investigating session hook execution, event firing, and payload injection.

## 1. Trace and Transcript Ingestion

- Collect session start logs, event records, and raw JSON transcripts for `<session-id>`.
- Extract timestamps, registered hook handlers, and environment variables.

## 2. Event Dispatch Verification

- Trace the hook lifecycle from event trigger to handler invocation.
- Verify whether the event payload was delivered intact to the handler.
- Inspect handler return object (`inject_text`, `user_text`, `kind`).

## 3. Injection and Transcript Audit

- Confirm whether injected text was rendered in the active session context.
- Check for encoding errors, truncation, or regex filtering issues.

## 4. Root Cause and Remediation

- Isolate the failure mechanism (handler crash, timeout, permission denial, stale baked image).
- Formulate targeted fix and verify using isolated hook test suite.
