Degraded capability failure detected in tool response. Under `halt-on-failure` and `fail-fast`:

- Do not silently swallow this degradation or treat the action as fully successful.
- Required: Report the capability failure verbatim to the user and invoke /learn to diagnose the root cause (do not create tasks).
