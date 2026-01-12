#!/usr/bin/env python3
"""
PreToolUse SQL validator hook for Claude Code.

Blocks dangerous SQL operations:
- DROP TABLE/DATABASE/etc.
- DELETE without WHERE clause
- TRUNCATE TABLE

Logs all blocked queries to a local log file for audit purposes.

Exit codes (per Claude Code docs):
    0: Allow - JSON output on stdout is processed
    2: Block - only stderr is read (message shown to Claude)
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# Log file for blocked queries
LOG_DIR = Path.home() / ".claude" / "sql_validator_logs"
LOG_FILE = LOG_DIR / "blocked_queries.log"


def ensure_log_dir():
    """Ensure log directory exists."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def log_blocked_query(query: str, tool_name: str = "unknown") -> None:
    """
    Log a blocked SQL query to the audit log.

    Args:
        query: The dangerous SQL query that was blocked
        tool_name: Name of the tool that attempted to run the query
    """
    ensure_log_dir()
    timestamp = datetime.now(timezone.utc).isoformat()
    log_entry = {
        "timestamp": timestamp,
        "tool": tool_name,
        "query": query,
    }

    try:
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        # Fail silently - logging shouldn't break the hook
        pass


def is_dangerous_sql(query: str) -> bool:
    """
    Check if a SQL query contains dangerous patterns.

    Dangerous patterns:
    - DROP (any form: DROP TABLE, DROP DATABASE, etc.)
    - DELETE without WHERE
    - TRUNCATE

    Args:
        query: SQL query string to check

    Returns:
        True if query is dangerous, False if safe
    """
    if not query or not query.strip():
        return False

    # Normalize for pattern matching: uppercase, strip whitespace
    normalized = query.strip().upper()

    # Pattern 1: DROP statements (any form)
    # Matches: DROP TABLE, DROP DATABASE, DROP INDEX, etc.
    if re.search(r"\bDROP\b", normalized):
        return True

    # Pattern 2: DELETE without WHERE
    # Matches: DELETE FROM table or DELETE FROM table ;
    # Must NOT have WHERE before the end/semicolon
    delete_match = re.search(r"\bDELETE\s+FROM\b", normalized)
    if delete_match:
        # Check if there's a WHERE clause after the DELETE FROM
        after_delete = normalized[delete_match.end() :]
        # If there's no WHERE clause before end of statement or semicolon, it's dangerous
        if not re.search(r"\bWHERE\b", after_delete):
            return True

    # Pattern 3: TRUNCATE statements
    if re.search(r"\bTRUNCATE\b", normalized):
        return True

    return False


def extract_sql_from_command(command: str) -> str | None:
    """
    Extract SQL query from a bash command.

    Handles common patterns:
    - sqlite3 db.db 'SELECT ...'
    - mysql -u user -p < 'SELECT ...'
    - psql -c 'SELECT ...'

    Args:
        command: Bash command string

    Returns:
        Extracted SQL query or None if no SQL found
    """
    if not command:
        return None

    # Pattern: -c 'SQL' or -c "SQL"
    c_match = re.search(r"-c\s+['\"]([^'\"]+)['\"]", command)
    if c_match:
        return c_match.group(1)

    # Pattern: 'SQL' at end after database name (sqlite3, etc.)
    quote_match = re.search(r"['\"]([^'\"]+)['\"]", command)
    if quote_match:
        return quote_match.group(1)

    return None


def validate_sql_query(tool_name: str, args: dict[str, Any]) -> dict[str, Any] | None:
    """
    Validate SQL in tool arguments.

    Only checks specific tools that can execute SQL:
    - Bash: Searches for SQL in command arguments

    Args:
        tool_name: Name of the tool being called
        args: Tool arguments

    Returns:
        Hook output dict if blocked, None if allowed
    """
    # Only validate Bash commands (most likely to contain raw SQL)
    if tool_name != "Bash":
        return None

    command = args.get("command", "")
    if not command:
        return None

    # Try to extract SQL from the command
    sql_query = extract_sql_from_command(command)

    if sql_query and is_dangerous_sql(sql_query):
        log_blocked_query(sql_query, tool_name)
        return get_hook_output("Blocked dangerous SQL operation", sql_query)

    return None


def get_hook_output(
    reason: str | None, query: str | None = None
) -> dict[str, Any] | None:
    """
    Format hook output for Claude Code.

    Args:
        reason: Reason for blocking (None if not blocking)
        query: The blocked SQL query (for logging)

    Returns:
        Hook output dict or None if not blocking
    """
    if reason is None:
        return None

    return {
        "continue": False,
        "systemMessage": (
            f"{reason}\n\n"
            f"Blocked query: `{query}`\n\n"
            f"To run this query safely:\n"
            f"1. For DELETE: Add a WHERE clause to limit affected rows\n"
            f"2. For DROP/TRUNCATE: Create a specific issue for schema changes\n\n"
            f"Blocked queries are logged at {LOG_FILE}"
        ),
    }


def main():
    """
    Main hook entry point.

    Reads hook input from stdin (JSON), validates SQL operations,
    and outputs hook result as JSON to stdout or error message to stderr.
    """
    try:
        # Read hook input from stdin
        input_data = json.load(sys.stdin)

        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        # Validate SQL
        block_result = validate_sql_query(tool_name, tool_input)

        if block_result:
            # Block - output to stderr (exit 2)
            print(json.dumps(block_result), file=sys.stderr)
            sys.exit(2)
        else:
            # Allow - no output needed (exit 0)
            sys.exit(0)

    except Exception as e:
        # On error, log and allow (don't block due to hook failure)
        error_msg = {
            "continue": True,
            "systemMessage": f"SQL validator hook error: {e}",
        }
        print(json.dumps(error_msg), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
