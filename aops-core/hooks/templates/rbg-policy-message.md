---
name: rbg-policy-message
title: RBG Policy Short Message
category: template
description: |
  Short user-facing message when rbg gate blocks a tool call.
  Variables: {threshold}, {ops_since_open} - kept parenthetically for
  audit/debug now that the primary number matches rbg-countdown.md's
  down-to-zero framing (aops_47d0a754).
---

✕ 0 remaining — compliance check now required (threshold {threshold} reached, {ops_since_open} ops since last check).
