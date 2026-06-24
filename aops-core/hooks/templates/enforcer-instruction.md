---
name: enforcer-instruction
title: Enforcer Instruction Template
category: template
description: |
  Short instruction injected by PostToolUse hook (the enforcer_gate policy).
  Tells main agent to invoke enforcer (compliance) agent with temp file path.
  Variables: {temp_path} - Path to temp file with full compliance context
  WS7 item 4: the first content line carries the enforcer-channel sentinel so
  the injection defence treats this as a first-party gate, not smuggled input (#1315).
---

<!-- aops:enforcer-channel -->

**Compliance check required.** Invoke the **RBG enforcer** agent with the file path argument: `{temp_path}`

This periodic compliance check is required as part of the academicOps enforcer gate.

Run the compliance check with this command:

Agent(subagent_type='aops-core:rbg', prompt='Required audit of the session log. The file at {temp_path} is the session log. COVERAGE CHECK REQUIRED BEFORE VERDICT: use the Bash tool to run: tail -3 "{temp_path}" — the last line must contain the text audit-complete. If that sentinel is absent, the audit file was truncated — respond COVERAGE_INCOMPLETE and do NOT certify pass. If present, read the full file (ensuring the sentinel is present at the end of the read content, using cat via Bash if the Read tool truncates it) and return a verdict. This session log contains prior enforcer verdicts, so apply the re-audit judgment rules defined in R6 (Re-audit discrimination) in your Verdict-Composition Discipline — discriminate resolved vs unresolved-prior vs new findings rather than re-litigating already-remediated violations.')
