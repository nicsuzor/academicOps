# Claude Code CLI SessionStart Hook System: Complete Technical Reference

Claude Code CLI **can load SessionStart hooks from paths outside the current working directory**, but the mechanism differs from what many developers expect. Hooks are configured through a hierarchical settings system, not auto-discovered from directories, and commands within those hooks can reference scripts anywhere on the filesystem using absolute paths or the `$CLAUDE_PROJECT_DIR` environment variable.

This finding is critical for multi-project setups: you can maintain a centralized hooks repository and reference it from any project by configuring global settings at `~/.claude/settings.json` or by using absolute paths in project-specific configurations.

## How hook discovery actually works

Claude Code uses a **configuration-based discovery system**, not a file-scanning system. At startup, Claude Code loads `settings.json` files from multiple locations in strict hierarchical order, merges their configurations, and creates an immutable snapshot of all hook definitions for that session. External edits during a session require review via the `/hooks` menu before taking effect—a security feature preventing malicious modifications.

**The discovery hierarchy (highest to lowest priority):**

1. **Enterprise managed settings** — System administrators define org-wide policies that cannot be overridden
   - macOS: `/Library/Application Support/ClaudeCode/managed-settings.json`
   - Linux/WSL: `/etc/claude-code/managed-settings.json`
   - Windows: `C:\ProgramData\ClaudeCode\managed-settings.json`

2. **CLI arguments** — Runtime settings via `--settings` flag

3. **Project local settings** — Personal overrides not committed to version control
   - Location: `.claude/settings.local.json` in current working directory
   - Automatically git-ignored by Claude Code

4. **Project shared settings** — Team-wide configuration checked into source control
   - Location: `.claude/settings.json` in current working directory

5. **User global settings** — Personal defaults across all projects
   - Location: `~/.claude/settings.json`

6. **Legacy configuration** — Deprecated but still functional for backward compatibility
   - Location: `~/.claude.json` or `~/.claude/claude.json`

Settings at higher precedence levels override lower ones, with arrays being replaced entirely rather than merged. The `.claude/hooks/` directory commonly seen in examples is purely a **convention for organizing scripts**—it's not automatically scanned. Scripts placed there must be explicitly referenced in a `settings.json` file's hook configuration.

## Configuration file structure and schema

Claude Code exclusively uses **JSON format** for configuration files. YAML and TOML are not supported for primary configuration, though YAML appears as frontmatter in subagent and slash command Markdown files.

**Complete settings.json schema:**

```json
{
  "model": "claude-sonnet-4-20250514",
  "maxTokens": 4096,
  "autoUpdates": true,

  "permissions": {
    "allowedTools": [
      "Read",
      "Write(src/**)",
      "Bash(git *)",
      "Bash(npm *)"
    ],
    "deny": [
      "Read(./.env)",
      "Read(./.env.*)",
      "Read(./secrets/**)",
      "Write(./production.config.*)",
      "Bash(rm *)",
      "Bash(sudo *)"
    ]
  },

  "hooks": {
    "SessionStart": [{
      "matcher": "startup|resume|clear",
      "hooks": [{
        "type": "command",
        "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/session_start.sh",
        "timeout": 60
      }]
    }],
    "PostToolUse": [{
      "matcher": "Write(*.py)",
      "hooks": [{
        "type": "command",
        "command": "python -m black $file"
      }]
    }]
  },

  "env": {
    "ANTHROPIC_MODEL": "claude-sonnet-4-20250514",
    "BASH_DEFAULT_TIMEOUT_MS": "30000",
    "DISABLE_TELEMETRY": "1"
  },

  "enabledPlugins": {
    "formatter@company-tools": true
  },

  "apiKeyHelper": "/path/to/key-helper-script.sh",
  "parallelTasksCount": 3
}
```

**The .claude directory structure:**

```
~/.claude/                          # User-level configuration
├── settings.json                   # User settings applied to all projects
├── claude.json                     # Legacy config (deprecated)
├── CLAUDE.md                       # Global context/instructions
├── CLAUDE.local.md                # Personal global context (git-ignored)
├── agents/                        # User-level subagents (Markdown + YAML)
├── commands/                      # User-level slash commands
└── hooks/                         # Convention for organizing hook scripts

<project-root>/.claude/            # Project-level configuration
├── settings.json                  # Shared team settings (committed to git)
├── settings.local.json           # Personal project settings (git-ignored)
├── CLAUDE.md                      # Project instructions/memory
├── CLAUDE.local.md               # Personal project context
├── agents/                       # Project-specific subagents
├── commands/                     # Project-specific slash commands
└── hooks/                        # Project hook scripts
```

The `.mcp.json` file at the project root configures Model Context Protocol servers and can be version-controlled for team-wide tool availability. There is **no `.claude_config.json` file**—only `settings.json` variants are recognized.

**Environment variables** can override any configuration setting. Critical variables include `ANTHROPIC_API_KEY` for authentication, `CLAUDE_PROJECT_DIR` (available during hook execution), `BASH_DEFAULT_TIMEOUT_MS`, `CLAUDE_CODE_MAX_OUTPUT_TOKENS`, and privacy controls like `DISABLE_TELEMETRY`. All environment variables can be defined persistently in the `env` object within `settings.json`.

## Multi-project setup patterns and shared frameworks

Three documented patterns enable sharing SessionStart hooks across multiple projects, each with specific trade-offs for polyrepo architectures.

**Pattern 1: Global hooks in user settings**

Define hooks once in `~/.claude/settings.json` and they automatically apply to every project you work on. This is the simplest approach for personal consistency:

```json
{
  "hooks": {
    "SessionStart": [{
      "hooks": [{
        "type": "command",
        "command": "~/.claude/hooks/global_session_start.py"
      }]
    }]
  }
}
```

Store your hook scripts in `~/.claude/hooks/` and reference them with absolute paths or tilde expansion. Global hooks get merged with project-specific hooks, so teams can layer organization standards (global) with project requirements (local).

**Pattern 2: Symlinked CLAUDE.md files for shared context**

While you can't configure arbitrary `settings.json` paths via environment variables, symlinks work for sharing instruction files across projects:

```bash
# Create shared context repository
mkdir ~/.ai-context
touch ~/.ai-context/coding-standards.md

# Symlink as CLAUDE.md in multiple projects
cd ~/project-a && ln -s ~/.ai-context/coding-standards.md ./CLAUDE.md
cd ~/project-b && ln -s ~/.ai-context/coding-standards.md ./CLAUDE.md
```

**Known issue**: Symlinks to `~/.claude` directory itself have reported problems (GitHub issue #764). The workaround is to symlink individual files or use direct absolute paths in hook commands rather than symlinking the hook scripts themselves. Issue #5433 documents hooks failing silently when executed through symlinked directories.

**Pattern 3: Multi-directory access with --add-dir**

Work across multiple repositories in a single session by adding directories at startup or mid-session:

```bash
# At startup: Reference backend while working on frontend
claude --add-dir ../backend-api --add-dir ~/shared/libraries

# During session
/add-dir ../backend-api
```

This enables polyrepo workflows where you need cross-repository context. However, CLAUDE.md files in directories added via `--add-dir` are **not automatically loaded** (GitHub issue #3146), limiting context sharing through this mechanism.

**Pattern 4: Plugin-based distribution**

The plugin system (in public beta) packages hooks, commands, and configurations for distribution. Teams can create private plugin marketplaces:

```bash
# Add company plugin marketplace
/plugin marketplace add company/claude-plugins

# Install shared hooks/commands
/plugin install company-standards
```

**Real-world implementations** demonstrate these patterns in production. The GitButler integration uses SessionStart hooks to initialize shadow git worktrees for change tracking. The disler/claude-code-hooks-mastery repository provides reference implementations of all 8 hook lifecycle events. Teams at companies like Neon Engineering publish standardized hooks for notifications, code formatting, type checking, and test running.

For polyrepo setups specifically, the recommended hybrid approach combines global user settings for personal standards, project-specific `.claude/settings.json` for team requirements, plugins for organizational standards, and `--add-dir` for cross-repository sessions when needed.

## Path resolution rules and edge cases

Path resolution in Claude Code has specific behaviors that affect reliability, particularly for hooks referencing scripts outside the project directory.

**Relative paths resolve from the current working directory** where Claude Code was launched, **not** from the hook file location or configuration file location. This creates portability issues. If you define a hook command as `.claude/hooks/script.sh` and run `claude` from different directories, the relative path resolves differently each time. GitHub issue #4754 documents inconsistent behavior when relative paths in CLAUDE.md reference files, attempting to load from CWD instead of relative to the CLAUDE.md location.

**Absolute paths are officially recommended** and eliminate ambiguity. From the official documentation and community repositories: "If your hook scripts aren't executing properly, it might be due to relative paths in your settings.json. Claude Code documentation recommends using absolute paths for command scripts."

**Environment variables are fully supported** with `$CLAUDE_PROJECT_DIR` being the most critical. This special variable contains the absolute path to the project root (where Claude Code started) and is available during all hook executions:

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Write|Edit",
      "hooks": [{
        "type": "command",
        "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/check-style.sh"
      }]
    }]
  }
}
```

Note the escaped quotes around the variable—necessary for paths containing spaces, particularly on Windows. Standard shell variables like `$HOME`, `$PATH`, and `$PYTHONPATH` also work. Plugin hooks get access to `${CLAUDE_PLUGIN_ROOT}` for plugin-relative paths.

**Tilde expansion** (`~`) works correctly for home directory references. You can use `~/external-scripts/hook.sh` in hook commands, though this creates a **security consideration** documented in GitHub issue #3275: Claude Code can access and modify files anywhere on the filesystem using absolute paths or tilde expansion, even outside the working directory. The permission system provides protection:

```json
{
  "permissions": {
    "deny": [
      "Read(/etc/**)",
      "Write(/var/**)",
      "Bash(sudo *)"
    ]
  }
}
```

**Symlinks have multiple known issues**. When `~/.claude` is itself a symlink (common for dotfiles management), Claude Code may fail to detect files in that directory. Hook scripts accessed through symlinked directories can hang indefinitely with no error messages (issue #5433). The workaround is using direct absolute paths to the actual file locations rather than symlink paths. A July 2025 fix addressed symlink resolution for settings files specifically, but symlink handling remains fragile in general.

**Windows presents additional challenges**. Issue #9542 reports SessionStart hooks cause infinite hangs on Windows (though they work on macOS and Linux). Issues #3594, #4079, and #4507 document Windows path resolution errors with spaces in paths like `C:\Program Files\Git`. Proper quoting is essential on Windows.

**Accessing files outside the project directory is possible** through absolute paths, tilde expansion, or the `--add-dir` flag. This is intentional for multi-project workflows but requires careful permission management to prevent unintended file access.

## Concrete answer to the critical question

**Can you configure Claude Code to load a SessionStart hook from a path outside the current working directory?**

**Yes, through two mechanisms:**

1. **Hook commands can reference external scripts** using absolute paths or tilde expansion:

```json
{
  "hooks": {
    "SessionStart": [{
      "hooks": [{
        "type": "command",
        "command": "/Users/username/shared-hooks/session_start.sh"
      }]
    }]
  }
}
```

Place this configuration in **any** settings.json location—project-level (`.claude/settings.json`) or user-level (`~/.claude/settings.json`)—and the command will execute the script from the external location.

2. **Global settings automatically apply to all projects**:

```json
// In ~/.claude/settings.json
{
  "hooks": {
    "SessionStart": [{
      "hooks": [{
        "type": "command",
        "command": "~/personal-context-repo/hooks/load-context.py"
      }]
    }]
  }
}
```

This configuration in your user-level settings will run for every project without needing project-specific configuration.

**What you cannot do** is specify an arbitrary `settings.json` file location via environment variables. The settings files must be in the standard hierarchy locations. However, since hook commands themselves accept any path, you can maintain a centralized hooks repository and reference it from the standard settings locations.

**Recommended implementation for flat architecture:**

```bash
# Your structure
~/personal-context/
  ├── hooks/
  │   └── session_start.sh
  └── instructions/
      └── coding-standards.md

~/projects/
  ├── project-a/.claude/settings.json
  └── project-b/.claude/settings.json
```

**In ~/.claude/settings.json (global approach):**

```json
{
  "hooks": {
    "SessionStart": [{
      "hooks": [{
        "type": "command",
        "command": "~/personal-context/hooks/session_start.sh"
      }]
    }]
  }
}
```

**Or in each project's .claude/settings.json:**

```json
{
  "hooks": {
    "SessionStart": [{
      "hooks": [{
        "type": "command",
        "command": "/absolute/path/to/personal-context/hooks/session_start.sh"
      }]
    }]
  }
}
```

The SessionStart hook script can then load external instruction files into context programmatically.

## Gemini CLI compatibility and differences

Gemini CLI **does not currently have a SessionStart hook system**. This is a fundamental architectural difference and the most significant compatibility gap. GitHub issues #2779 and #9070 track feature requests for hooks in Gemini CLI, with #9070 proposing a comprehensive design that would mirror Claude Code's JSON-over-stdin contract and exit code semantics, including migration tooling to convert Claude Code hooks. As of October 2025, this remains unimplemented.

**Configuration comparison:**

| Aspect                   | Claude Code CLI                                      | Gemini CLI                            |
| ------------------------ | ---------------------------------------------------- | ------------------------------------- |
| **Hooks system**         | 8 lifecycle events implemented                       | Not implemented (requested)           |
| **SessionStart**         | Fully functional                                     | Not available                         |
| **Configuration file**   | `~/.claude/settings.json`                            | `~/.gemini/settings.json`             |
| **Context/memory**       | `CLAUDE.md`                                          | `GEMINI.md`                           |
| **MCP servers**          | Separate `.mcp.json` (git-friendly)                  | In main settings.json                 |
| **Discovery precedence** | Enterprise → Project local → Project → User → Legacy | System → User → Project → Environment |
| **Philosophy**           | Hybrid deterministic + probabilistic                 | Purely probabilistic context-driven   |

Gemini CLI relies entirely on **probabilistic AI following instructions** in GEMINI.md files rather than guaranteed deterministic hook execution. This makes it suitable for exploratory work and individual development but less reliable for production automation requiring guaranteed actions like formatting, linting, or quality gates.

**Both CLIs can coexist** on the same system without conflicts—they use different configuration directories (`~/.claude/` vs `~/.gemini/`), different context files, and different command namespaces. MCP servers are fully compatible since both implement the Model Context Protocol standard; the same server works with both CLIs despite different configuration formats.

**Migration path**: Currently manual. When Gemini implements hooks, the proposed design includes a `gemini hooks migrate --from-claude` command for automatic conversion of hook configurations and environment variable mappings.

**When to use each**: Choose Claude Code for production environments requiring deterministic automation, team collaboration with shared configurations, CI/CD integration, and quality gate enforcement. Choose Gemini CLI for exploratory development, personal projects, situations where the generous free tier matters, or when you prefer open-source tools (Gemini CLI is Apache 2.0 licensed). The fundamental trade-off is deterministic control vs. probabilistic instruction-following.

## Known limitations and issues

**Windows-specific problems** include SessionStart hooks causing infinite hangs (issue #9542) and path resolution failures with spaces in paths (issues #3594, #4079, #4507). Windows users should test hooks thoroughly and consider workarounds like WSL for reliability.

**Symlink fragility** affects multiple scenarios: symlinked `~/.claude` directories fail to detect files properly, hooks executed through symlinked paths hang silently, and relative paths in symlinked CLAUDE.md files attempt loading from wrong locations. Direct absolute paths avoid these issues.

**Configuration file discovery** never checks for `.claude_config.json` despite this being a common assumption. Only `settings.json` (in various locations) and the legacy `claude.json` are recognized.

**XDG Base Directory non-compliance** on Linux (issue #1455) means Claude Code always uses `~/.claude` regardless of `$XDG_CONFIG_HOME` or other XDG environment variables.

**CLAUDE.md files in added directories** aren't automatically loaded when using `--add-dir` (issue #3146), limiting context sharing in multi-directory sessions.

**No official JSON schema** exists for settings.json despite community requests (issue #2783), making validation and IDE autocomplete unavailable.

**Hook debugging** requires the `--debug` flag for visibility into execution. Silent failures can occur with symlinks or misconfigured paths.

## Best practices and recommendations

**For hook configuration:**

- Always use absolute paths in hook commands: `/absolute/path/script.sh` or `~/relative-to-home.sh`
- Leverage `$CLAUDE_PROJECT_DIR` for project-relative scripts: `"$CLAUDE_PROJECT_DIR/.claude/hooks/script.sh"`
- Quote paths that might contain spaces: `"\"$CLAUDE_PROJECT_DIR\"/script.sh"`
- Avoid symlinks for hook scripts themselves; symlink CLAUDE.md files if needed for context sharing
- Test hooks with `claude --debug` to see execution details
- Set appropriate timeouts: `"timeout": 30` in hook configuration

**For multi-project setups:**

- Store personal standards in `~/.claude/settings.json` as global hooks
- Commit `.claude/settings.json` to version control for team-shared configurations
- Use `.claude/settings.local.json` (git-ignored) for personal project overrides
- Organize hook scripts in `.claude/hooks/` by convention, even though not auto-discovered
- Consider plugins for distributing organizational standards across teams
- Use `--add-dir` for cross-repository context when needed

**For security:**

- Define `permissions.deny` patterns for sensitive paths like `.env` files and `/etc/**`
- Review hook commands before adding (they execute with your credentials)
- Use the `/hooks` interactive menu to review externally modified hooks before activation
- Be aware hooks can access files outside project directory via absolute paths

**For Windows users:**

- Test SessionStart hooks thoroughly; they have known reliability issues
- Use WSL if encountering persistent path resolution problems
- Double-quote all paths containing spaces
- Avoid `Program Files` paths in hook commands when possible

**For polyrepo workflows:**

- Maintain a centralized hooks repository in `~/shared-hooks/` or similar
- Reference it from global settings for personal use: `~/shared-hooks/session_start.sh`
- Or reference from project settings for team use: `/team/shared/hooks/session_start.sh`
- Use git worktrees for parallel Claude instances on the same repository
- Consider GitButler hooks for automatic session isolation into branches

The flat architecture pattern—maintaining a personal context repository outside project directories and referencing it via hooks with absolute paths—is fully supported and represents a documented best practice for sophisticated multi-project setups.

## Hook Input/Output Schemas (academicOps Implementation)

Based on analysis of actual hook execution logs and our Pydantic models in `bots/hooks/hook_models.py`:

### Common Input Structure (All Hooks)

All hooks receive JSON on stdin with these common fields:

```json
{
  "session_id": "uuid-string",
  "transcript_path": "/path/to/.claude/projects/[project]/[session-id].jsonl",
  "cwd": "/current/working/directory",
  "permission_mode": "bypassPermissions" | "requirePermissions",
  "hook_event_name": "PreToolUse" | "PostToolUse" | "UserPromptSubmit" | "SessionStart" | "Stop" | "SubagentStop"
}
```

### PreToolUse Hook

**Input** (in addition to common fields):

```json
{
  "tool_name": "Bash" | "Read" | "Write" | "Edit" | "Grep" | "Glob" | ...,
  "tool_input": {
    // Tool-specific parameters
    // Examples:
    // Bash: {"command": "ls -la", "description": "..."}
    // Read: {"file_path": "/path/to/file"}
    // Write: {"file_path": "/path", "content": "..."}
    // Edit: {"file_path": "/path", "old_string": "...", "new_string": "..."}
  }
}
```

**Output** (required structure):

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow" | "deny" | "ask",
    "permissionDecisionReason": "Optional explanation"
  },
  "continue": true | false,
  "systemMessage": "Optional warning shown to user",
  "stopReason": "Optional message when continue=false"
}
```

**Exit codes**:

- `0` - Allow execution (hook succeeded)
- `1` - Warn but allow (show systemMessage)
- `2` - Block execution (show permissionDecisionReason)

### PostToolUse Hook

**Input** (in addition to common fields):

```json
{
  "tool_name": "Bash" | "Read" | "Write" | ...,
  "tool_input": {
    // Same as PreToolUse
  },
  "tool_response": {
    "type": "text" | "error" | ...,
    // Tool-specific response data
    // Examples:
    // Read: {"file": {"filePath": "...", "content": "...", "numLines": 56, ...}}
    // Bash: {"output": "command output", "exitCode": 0}
  }
}
```

**Output**:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "Optional context injected into conversation"
  },
  "continue": true | false,
  "systemMessage": "Optional message",
  "suppressOutput": true | false
}
```

**Exit code**: Always `0` (PostToolUse hooks don't block)

### UserPromptSubmit Hook

**Input** (in addition to common fields):

```json
{
  "prompt": "The user's input text"
}
```

**Output**:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "Optional context to inject"
  },
  "continue": true | false,
  "systemMessage": "Optional message"
}
```

**Exit code**: Always `0`

### SessionStart Hook

**Input** (in addition to common fields):

```json
{
  // No additional fields beyond common structure
}
```

**Output**:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "Context injected at session start (instructions, environment info, etc.)"
  },
  "systemMessage": "Optional startup message",
  "suppressOutput": true | false
}
```

**Exit code**: `0` for success

### Stop and SubagentStop Hooks

**Input** (in addition to common fields):

```json
{
  // No additional fields beyond common structure
}
```

**Output**:

```json
{
  "decision": "block" | null,
  "reason": "Required when decision='block'",
  "continue": true | false
}
```

**Exit codes**:

- `0` - Allow stop
- `1` - Warn but allow
- `2` - Block stop

### Environment Variables Available in Hooks

- `$CLAUDE_PROJECT_DIR` - Absolute path to project root (where Claude Code started)
- `$CLAUDE_PLUGIN_ROOT` - For plugin hooks, path to plugin directory
- **Custom variables** - Shell environment variables work in hook commands (e.g., `$AOPS` for centralized framework path)
- Standard shell variables: `$HOME`, `$PATH`, `$PYTHONPATH`, etc.
- Any variables defined in `settings.json` `env` object

### Best Practices for Hook Implementation

1. **Always output valid JSON** - Even on error, output `{}` and exit 0
2. **Validate input defensively** - Check for missing fields before accessing
3. **Use Pydantic models** - Validate output structure (see `bots/hooks/hook_models.py`)
4. **Handle errors gracefully** - Wrap logic in try/except, never crash
5. **Log for debugging** - Use separate log files (e.g., `/tmp/claude_*.json`)
6. **Set timeouts** - Configure reasonable timeout in settings (default 2-5s)
7. **Absolute paths** - Use `$CLAUDE_PROJECT_DIR` or absolute paths, not relative
8. **Exit codes matter** - PreToolUse: 0=allow, 1=warn, 2=block; Others: always 0

### Example: Minimal Hook Implementation

```python
#!/usr/bin/env python3
import json
import sys


def main():
    # Read input
    try:
        input_data = json.load(sys.stdin)
    except:
        input_data = {}

    # Process (hook-specific logic)
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",  # or SessionStart, etc.
            "permissionDecision": "allow",  # PreToolUse only
        }
    }

    # Output and exit
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
```

### Debugging Hook Execution

Enable debug logging to see actual hook I/O:

```python
from hook_debug import safe_log_to_debug_file

# Logs to /tmp/claude_{hook_event}_{timestamp}.json
safe_log_to_debug_file("PreToolUse", input_data, output_data)
```

Run Claude Code with debug flag to see hook execution:

```bash
claude --debug
```

Check logs in `/tmp/`:

```bash
ls -lt /tmp/claude_* | head
cat /tmp/claude_pretooluse_TIMESTAMP.json
```
