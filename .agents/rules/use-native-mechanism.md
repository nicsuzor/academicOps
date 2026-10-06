---
trigger: always_on
description: Use native platform, client, format, and build mechanisms before creating bespoke machinery.
---

## Use the native mechanism

Before creating custom logic or bespoke abstractions, identify and adopt the standard mechanism provided by the platform, client, format, or runtime:

- Prefer standard client configuration fields, environment variables (e.g., skill directory variables), and tool permissions over custom wrappers or mixins.
- Use native format syntax (such as standard Argdown syntax) rather than bespoke pseudo-code or DSL layers.
- Prefer direct build-system or container configuration changes (e.g., Dockerfile or Makefile updates) over complex programmatic orchestration.
- Build custom machinery only when no native mechanism exists.
