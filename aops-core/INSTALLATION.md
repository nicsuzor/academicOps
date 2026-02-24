# AcademicOps Core Installation & Architecture

## Unified Hook Router System

The `aops-core` hooks system uses a **Universal Router** (`hooks/router.py`) to standardize behavior across different AI coding assistants (Claude Code and Gemini CLI).

### Architecture

1. **Single Entry Point**: All hook events are directed to `hooks/router.py`.
2. **Event Normalization**:
   - **Gemini Events** (e.g., `SessionStart`) are mapped to their Claude equivalents or handled internally.
   - **Gemini Context**: The router extracts `transcript_path` from Gemini's `SessionStart` payload to derive the temporary configuration root (`AOPS_GEMINI_TEMP_ROOT`), ensuring consistent path resolution for session files.
3. **Gate Registry**:
   - `hooks/gate_registry.py` defines the mapping between events and "Gates" (compliance checks).
   - Example: `PreToolUse` -> `HydrationGate`, `CustodietGate`.
4. **Legacy Support**: The router maintains backward compatibility by ensuring environment variables like `PYTHONPATH` are correctly injected for downstream scripts.

### Key Components

- `hooks/router.py`: The main dispatcher.
- `hooks/gates.py`: The universal gate runner.
- `hooks/gate_registry.py`: Configuration of which gates run for which events.
- `lib/hook_utils.py`: Shared utilities for path resolution (handling both `aops` and `Gemini` modes).

---

## Installation & Setup

### 1. Requirements

- **Plugin Independence**: The system is designed to be location-independent. It does **not** rely on a global `$AOPS` environment variable.
- **Path Resolution**:
  - **Local**: Uses `PYTHONPATH` derived from the script location.
  - **Gemini**: Uses `AOPS_GEMINI_TEMP_ROOT` (injected by router) or falls back to `cwd` hashing.

### 2. Gemini CLI Installation

To install `aops-core` as a Gemini extension:

1. **Extension Configuration**:
   Ensure your `gemini-extension.json` points to `hooks/router.py` for all relevant hooks.

   ```json
   {
     "hooks": {
       "SessionStart": "python3 aops-core/hooks/router.py",
       "PreToolUse": "python3 aops-core/hooks/router.py",
       "UserPromptSubmit": "python3 aops-core/hooks/router.py"
     }
   }
   ```

   _Note: The Gemini CLI wrapper handles `PYTHONPATH` injection automatically, or `router.py` will self-configure._

2. **Session Persistence**:
   The router automatically detects Gemini sessions and persists configuration (like `temp_root`) to `~/.gemini/tmp/<project-hash>/chats/session-<pid>.json`, ensuring that subsequent hooks (like `UserPromptSubmit`) can resolve the correct context.

### 3. Claude Code Installation

For standard Claude Code Usage:

1. **Environment Setup**:
   The `hooks/session_env_setup.sh` script handles initialization.
   - It calculates `AOPS_CORE` root relative to itself.
   - It exports `PYTHONPATH` to `.claude/env` (or equivalent).
   - It **does not** enforce a global `$AOPS` variable, keeping the environment clean.

2. **Hook Configuration**:
   Configure Claude to use `hooks/router.py` (or specific entry points if preferred, though `router.py` is recommended for consistency).

### 4. Antigravity / Development Install

1. **Setup Script**:
   Run `make install-dev` in the repository root.
   - This builds the plugin and installs dependencies.
   - Installs cron jobs for dev machines.

2. **Verification**:
   Run the test suite to verify installation integrity:

   ```bash
   pytest tests/hooks/
   ```

---

## Troubleshooting

- **"ModuleNotFoundError"**: Ensure `PYTHONPATH` includes `aops-core`. The router handles this, but custom scripts might need explicit setup.
- **Gemini Temp Files Missing**: Check `~/.gemini/tmp/`. The router logs session startup details which can be useful for debugging.
- **Gate Blocking**: Check `aops-core/hooks/gate_registry.py` to see active gates. Logs are written to stderr.
