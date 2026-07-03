---
name: rbg-policy-message
title: RBG Policy Short Message
category: template
description: |
  Short user-facing message when rbg gate blocks a tool call.
  Variables: {ops_since_open} - number of ops since last compliance check
---

<academicOps rbg compliance check>
✕ Compliance check required ({ops_since_open} ops since last check).
</academicOps rbg compliance check>
