---
title: fail-fast
type: note
permalink: concepts/core/fail-fast
tags:
- core-axiom
- error-handling
- reliability
---

**Core idea**: Abort immediately when assumptions are invalid, rather than continuing with uncertain state.

## Overview

The fail-fast principle requires code to stop execution as soon as an error condition is detected, rather than attempting to recover or continue with potentially corrupted state. This makes bugs easier to diagnose and prevents cascading failures.

## Principles

- No default values that mask missing configuration
- No fallback paths that hide errors
- Explicit error messages that identify the problem
- Fail loudly with clear diagnostics, not silently

## Examples

**Good Example**:

```python
if not config_path.exists():
    raise FileNotFoundError(f"Config not found: {config_path}")
config = load_yaml(config_path)
```

**Bad Example**:

```python
config = load_config() or {}  # Silent failure!
value = config.get("key", "default")  # Masks missing data
```

## When to Apply

- Configuration loading (no defaults)
- File path validation (must exist)
- API responses (fail on unexpected format)
- User input validation (explicit requirements)
- Test setup (fail if preconditions not met)

## Related Concepts

- [[no-assumptions]] - Why we fail fast
- [[standard-tools]] - Tools must exist or fail
- [[explicit-errors]] - How to fail fast effectively

## Learning Log

**2025-11-06**: Initial concept extracted during BM integration (Issue #193)
