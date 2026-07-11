---
name: rbg-review-policy-message
title: RBG Review Policy Short Message
category: template
description: |
  Short user-facing message when the rbg-review (end-of-session audit) gate
  blocks/warns on Stop. Split from rbg-policy-message.md (aops_47d0a754) —
  rbg-review has no ops-count threshold/countdown concept (it fires on
  Stop-while-CLOSED, not on crossing a threshold), so it must not inherit the
  "N remaining / threshold reached" framing added to the rbg (ops-count) gate's
  own templates.
  Variables: {ops_since_open} - number of ops since last compliance check
---

✕ Compliance check required ({ops_since_open} ops since last check).
