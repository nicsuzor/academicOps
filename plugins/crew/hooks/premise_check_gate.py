#!/usr/bin/env python3
"""Hook arm/disarm lifecycle for premise checking (backward-compatibility wrapper for hearsay_gate)."""

from __future__ import annotations

import hearsay_gate as _hg

# Re-export all symbols (public and internal) from hearsay_gate for backward compatibility
globals().update({_name: getattr(_hg, _name) for _name in dir(_hg)})

premise_check_arm = _hg.hearsay_arm
premise_check_handler = _hg.hearsay_handler
