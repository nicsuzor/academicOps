# Path Resolution System

## Overview

The academicOps system uses environment-based path resolution to support:

- Multi-machine deployment
- Different directory structures
- Separation of public bot code from private user data

## Configuration

### Environment Variables

Set these environment variables to customize paths:

- `ACADEMIC_OPS_ROOT`: Base directory containing user's private data (default: parent of bot directory)

### Automatic Detection

If environment variables are not set, the system automatically detects paths based on the bot repository location.

## Usage

### In Bash Scripts

```bash
# Source the path configuration
source "$(dirname "$0")/../config/paths.sh"

# Validate paths exist
if ! validate_paths; then
    echo "Path configuration error"
    exit 1
fi

# Use the exported variables
echo "Data directory: $ACADEMIC_OPS_DATA"
echo "Scripts directory: $ACADEMIC_OPS_SCRIPTS"
```

### In Python Scripts

```python
from config.paths import paths, DATA, SCRIPTS

# Validate paths
valid, missing = paths.validate()
if not valid:
    print(f"Missing directories: {missing}")
    exit(1)

# Use the path objects
task_file = paths.task_inbox / "new-task.md"
script = paths.scripts / "task_add.py"
```

## Directory Structure

### Standard Layout

```
$ACADEMIC_OPS_ROOT/           # User's parent repository
├── data/                      # Private user data
│   ├── goals/                 # Strategic goals
│   ├── projects/              # Project files
│   ├── tasks/                 # Task management
│   └── views/                 # Aggregated views
├── docs/                      # User-specific documentation
├── projects/                  # Academic project submodules
└── bot/                       # This repository (public)
    ├── config/                # Path configuration
    │   ├── paths.sh           # Bash path resolution
    │   └── paths.py           # Python path resolution
    ├── docs/                  # Generic documentation
    ├── scripts/               # Automation scripts
    └── models/                # Data models
```

## Multi-Machine Support

- The system works across machines with different user names.

### Configuration Methods

1. **Environment Variable** (Recommended for production):
   ```bash
   export ACADEMIC_OPS_ROOT="/path/to/your/workspace"
   ```

2. **Automatic Detection** (Default for development): The system detects paths relative to the bot repository location

3. **Configuration File** (Optional): Create a `.env` file in the bot directory:
   ```
   ACADEMIC_OPS_ROOT=/path/to/your/workspace
   ```

## Migration from Hardcoded Paths

### Old Style (Hardcoded)

```python
# DON'T DO THIS
task_file = "/home/nic/src/writing/data/tasks/inbox/task.md"
```

### New Style (Portable)

```python
# DO THIS INSTEAD
from config.paths import paths
task_file = paths.task_inbox / "task.md"
```

## Troubleshooting

### Path Not Found Errors

1. Run validation to identify missing directories:
   ```bash
   source config/paths.sh && validate_paths
   ```

2. Check environment variables:
   ```bash
   source config/paths.sh && print_config
   ```

3. Create missing directories:
   ```python
   from config.paths import paths
   paths.ensure_directories()
   ```

### Permission Errors

- Ensure the user has read/write access to all configured directories
- Check that scripts are executable: `chmod +x scripts/*.sh`

### Cross-Platform Issues

- Use forward slashes in path strings (Python's pathlib handles conversion)
- Avoid shell-specific constructs in scripts
- Test on target platform before deployment
