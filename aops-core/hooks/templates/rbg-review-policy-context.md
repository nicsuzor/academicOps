---
name: rbg-review-policy-context
title: RBG Review Policy Context Injection
category: template
description: |
  Full context injection when the rbg-review (end-of-session audit) gate
  blocks/warns on Stop. Split from rbg-policy-context.md (aops_47d0a754) —
  rbg-review has no ops-count threshold/countdown concept, so it must not
  inherit the "N remaining / threshold reached" framing added to the rbg
  (ops-count) gate's own templates.
  Variables: {ops_since_open}, {temp_path}
---

<academicOps rbg compliance check>
**ERROR:** Compliance check OVERDUE. You need to invoke the **rbg** agent before you can use tools.

**Periodic compliance check required ({ops_since_open} ops since last check).** Invoke the **rbg** agent with the file path argument:

- `Agent(subagent_type='aops-pkb:rbg', prompt='{temp_path}')`
  </academicOps rbg compliance check>
