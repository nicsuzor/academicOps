# Repo-Local Scripts

This directory is for automation scripts specific to this repository.

## Purpose

Place project-specific automation here:
- Pre-commit hooks
- Build scripts
- Deployment automation
- Data processing pipelines
- Testing utilities

## Difference from Framework Scripts

**Framework scripts** (`bots/.academicOps/scripts/`):
- Validation hooks (validate_tool.py, validate_stop.py)
- Instruction loaders (load_instructions.py)
- Generic utilities
- **Never edit these** (they're symlinked from framework)

**Repo-local scripts** (this directory):
- Project-specific automation
- Custom build processes
- One-off utilities for this repo
- **Safe to edit and commit**

## Best Practices

1. **Make executable**: `chmod +x your-script.sh`
2. **Add shebang**: `#!/usr/bin/env bash` or `#!/usr/bin/env python3`
3. **Document usage**: Add help text or comments
4. **Handle errors**: Use `set -euo pipefail` in bash scripts
5. **Commit to repo**: These are project-specific, safe to commit

## Examples

```bash
# Build script
bots/scripts/build.sh

# Data processing
bots/scripts/process_data.py

# Custom pre-commit check
bots/scripts/check_quality.sh
```
