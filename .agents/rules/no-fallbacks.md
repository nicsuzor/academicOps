---
trigger: always_on
description: Prohibit fallback paths, error swallowing, or downgrading failures in code and workflows; require loud, immediate halts on infrastructure and service errors.
---

## No fallbacks: halt loudly on infrastructure errors

Code, workflows, and tools must never swallow, hide, or downgrade errors. Any failure in infrastructure, services, tools, or underlying dependencies must halt loudly and surface immediately.

- **No fallback branches**: Do not introduce alternate execution paths or silent fallbacks to mask a broken tool, service, or dependency (such as CLI fallbacks when an MCP server is down, mock responses when an API fails, or fallback default values when data retrieval errors). Fix the failing component where it lives instead of bypassing it.
- **Do not swallow or downgrade exceptions**: Catch blocks, error handlers, and wrappers must never discard error details, convert errors into silent no-ops, or downgrade hard failures into benign warnings, empty collections, or synthetic success.
- **Surface verbatim failure details**: Raise exceptions with full stack traces, preserve raw stderr and exit codes, and propagate exact error messages up the stack so root causes are directly inspectable.
- **Fail fast at the point of failure**: Stop execution immediately upon encountering an unexpected error or infrastructure fault to prevent state corruption, masking defects, or proceeding on false premises.
