# Documentation Reorganization Migration Guide
**Date**: January 2025  
**Issue**: [#26](https://github.com/nicsuzor/academicOps/issues/26)

## Overview
This migration reorganizes documentation between the public bot repository and private parent repository, implements environment-based path resolution, and removes personal references from public code.

## Changes Made

### 1. Personal Reference Sanitization
**Changed Files:**
- `bot/docs/AGENT-INSTRUCTIONS.md`
  - Replaced personal repository references with "User's parent repository"
  - Removed all hardcoded `/home/nic/` paths

### 2. Path Resolution System
**New Files Created:**
- `bot/config/paths.sh` - Bash path resolution
- `bot/config/paths.py` - Python path resolution  
- `bot/docs/PATH-RESOLUTION.md` - Documentation

**Key Features:**
- Environment variable support (`ACADEMIC_OPS_ROOT`)
- Automatic path detection based on bot location
- Multi-machine compatibility
- No hardcoded user-specific paths

### 3. Documentation Reorganization

#### Moved to Bot Repository (Generic)
These files were moved from `docs/` to `bot/docs/`:
- `error-handling.md` - Generic error handling strategy
- `error-quick-reference.md` - Error quick reference
- `modes.md` - Agent interaction modes
- `DEVELOPMENT.md` - Development guidelines

#### Created in Bot Repository
New generic versions created in `bot/docs/`:
- `architecture.md` - Generic system architecture
- `INDEX.md` - Documentation index without personal paths
- `INSTRUCTIONS.md` - Generic agent instructions

#### Kept in Parent Repository (Personal)
These files remain in parent `docs/`:
- `accommodations.md` - Personal ADHD accommodations
- `STRATEGY.md` - Personal strategic planning
- `workflows/*.md` - Personal workflow definitions
- Original `INDEX.md` - Contains personal context
- Original `INSTRUCTIONS.md` - Contains personal context

### 4. Path Updates in Documentation
All documentation updated to use:
- `$ACADEMIC_OPS_ROOT` instead of `/home/nic/src/writing/`
- `$ACADEMIC_OPS_DATA` instead of `/home/nic/src/writing/data/`
- `$ACADEMIC_OPS_SCRIPTS` instead of `/home/nic/src/writing/bot/scripts/`
- Path resolution imports instead of hardcoded paths

## Migration Steps for Users

### 1. Update Your Environment
```bash
# Option 1: Set environment variable
export ACADEMIC_OPS_ROOT="/path/to/your/workspace"

# Option 2: Let system auto-detect (default)
# No action needed - paths detected from bot location
```

### 2. Update Scripts
Old style:
```python
task_file = "/home/nic/src/writing/data/tasks/inbox/task.md"
```

New style:
```python
from config.paths import paths
task_file = paths.task_inbox / "task.md"
```

### 3. Update Agent Commands
Agents should now:
1. Source path configuration before operations
2. Use environment variables instead of hardcoded paths
3. Refer to PATH-RESOLUTION.md for guidance

### 4. Verify Installation
```bash
# Test path configuration
cd bot
source config/paths.sh
print_config
validate_paths
```

## Benefits

### For Public Users
- No personal information in public repository
- Clear separation of generic vs personal content
- Better documentation organization
- Multi-machine support out of the box

### For Development
- Portable codebase works on any machine
- Environment-based configuration
- Clear extension points
- Better security boundaries

### For Maintenance
- Cleaner repository structure
- Easier to update documentation
- Clear ownership of files
- Simplified contribution process

## Compatibility

### Backwards Compatibility
- Existing hardcoded paths will continue to work on original machine
- Gradual migration possible - update scripts as needed

### Forward Compatibility
- New path system designed for extensibility
- Environment variables allow custom configurations
- Documentation structured for future additions

## Known Issues

### Gemini CLI Path Handling
- Gemini-cli may not properly handle absolute paths
- Workaround: Use relative paths when invoking from bot directory
- Long-term: Update Gemini configuration to use path resolution

### Cross-Platform Paths
- Windows paths need special handling
- Solution: Python's pathlib handles conversion automatically
- Scripts should use path resolution libraries

## Testing Checklist

- [ ] Path resolution works on Linux
- [ ] Path resolution works on Mac
- [ ] Path resolution works on Windows
- [ ] Scripts find correct directories
- [ ] Agents can access required files
- [ ] No personal data in bot repository
- [ ] Documentation is properly organized

## Support

For issues or questions:
1. Check [PATH-RESOLUTION.md](PATH-RESOLUTION.md)
2. Review [GitHub Issue #26](https://github.com/nicsuzor/academicOps/issues/26)
3. Create new issue if needed