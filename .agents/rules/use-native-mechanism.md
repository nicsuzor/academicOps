---
trigger: always_on
description: Prefer native platform, client, format, and build mechanisms.
---

## Native mechanisms

- Prefer standard client configs, env vars, native formats (e.g., Argdown), and `Dockerfile`/`Makefile` rules over custom wrappers, DSLs, or orchestration.
- Build custom machinery only when no native mechanism exists.
