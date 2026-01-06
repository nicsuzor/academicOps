---
name: compliance-auditor-instruction
title: Compliance Auditor Instruction
category: template
description: Short instruction injected by PostToolUse hook (periodic) for compliance check.
---

# Compliance Auditor Instruction Template

Short instruction injected every ~7 tool calls.
Tells main agent to spawn compliance-auditor subagent.

Variables:
- `{temp_path}` - Path to temp file with session context

---
**Periodic Compliance Check**: Spawn compliance-auditor to verify you're following framework principles:

```
Task(subagent_type="compliance-auditor", model="haiku",
     description="Compliance check",
     prompt="Read {temp_path} and check for principle violations.")
```

If auditor reports issues, address them before continuing. This check helps catch drift early.
