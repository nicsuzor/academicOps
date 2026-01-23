---
id: base-verification
category: base
---

# Base: Verification

**Composable base pattern.** Most workflows include this.

## Pattern

1. CHECKPOINT step before completion
2. Evidence gathered (tests pass, behavior observed, output verified)
3. No completion without verification

## Escalation

If verification reveals issues:
- Simple fix → fix and re-verify
- Complex issue → switch to [[debugging]]
