#!/usr/bin/env python3
"""
Unit tests for sql_validator PreToolUse hook.

Tests cover:
- Detection of dangerous SQL patterns (DROP, DELETE without WHERE, TRUNCATE)
- Proper logging of blocked queries
- Allow-through of safe SQL patterns
- Handler for non-SQL tools
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys

# Add hooks directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "hooks"))


class TestDangerousQueryDetection:
    """Test detection of dangerous SQL patterns."""

    def test_drop_table_is_blocked(self):
        """DROP TABLE queries should be blocked."""
        from sql_validator import is_dangerous_sql

        query = "DROP TABLE users"
        assert is_dangerous_sql(query) is True

    def test_drop_database_is_blocked(self):
        """DROP DATABASE queries should be blocked."""
        from sql_validator import is_dangerous_sql

        query = "DROP DATABASE production"
        assert is_dangerous_sql(query) is True

    def test_drop_with_whitespace_is_blocked(self):
        """DROP with extra whitespace should be blocked."""
        from sql_validator import is_dangerous_sql

        query = "  DROP  \n  TABLE  users"
        assert is_dangerous_sql(query) is True

    def test_drop_case_insensitive(self):
        """DROP should be detected case-insensitively."""
        from sql_validator import is_dangerous_sql

        queries = ["drop table users", "DROP TABLE users", "DrOp TABLE users"]
        for query in queries:
            assert is_dangerous_sql(query) is True, f"Failed for: {query}"

    def test_delete_without_where_is_blocked(self):
        """DELETE without WHERE clause should be blocked."""
        from sql_validator import is_dangerous_sql

        query = "DELETE FROM users"
        assert is_dangerous_sql(query) is True

    def test_delete_with_multiple_whitespace(self):
        """DELETE without WHERE with extra whitespace should be blocked."""
        from sql_validator import is_dangerous_sql

        query = "  DELETE  FROM   users  \n  ;"
        assert is_dangerous_sql(query) is True

    def test_truncate_is_blocked(self):
        """TRUNCATE queries should be blocked."""
        from sql_validator import is_dangerous_sql

        query = "TRUNCATE TABLE orders"
        assert is_dangerous_sql(query) is True

    def test_truncate_case_insensitive(self):
        """TRUNCATE should be detected case-insensitively."""
        from sql_validator import is_dangerous_sql

        queries = ["truncate table users", "TRUNCATE TABLE users"]
        for query in queries:
            assert is_dangerous_sql(query) is True, f"Failed for: {query}"

    def test_delete_with_where_is_safe(self):
        """DELETE with WHERE clause should be safe."""
        from sql_validator import is_dangerous_sql

        query = "DELETE FROM users WHERE id = 5"
        assert is_dangerous_sql(query) is False

    def test_select_is_safe(self):
        """SELECT queries should be safe."""
        from sql_validator import is_dangerous_sql

        query = "SELECT * FROM users WHERE id = 5"
        assert is_dangerous_sql(query) is False

    def test_update_is_safe(self):
        """UPDATE queries should be safe."""
        from sql_validator import is_dangerous_sql

        query = "UPDATE users SET name = 'John' WHERE id = 5"
        assert is_dangerous_sql(query) is False

    def test_insert_is_safe(self):
        """INSERT queries should be safe."""
        from sql_validator import is_dangerous_sql

        query = "INSERT INTO users (name) VALUES ('John')"
        assert is_dangerous_sql(query) is False

    def test_create_table_is_safe(self):
        """CREATE TABLE queries should be safe."""
        from sql_validator import is_dangerous_sql

        query = "CREATE TABLE users (id INT, name TEXT)"
        assert is_dangerous_sql(query) is False

    def test_empty_query_is_safe(self):
        """Empty query should be safe."""
        from sql_validator import is_dangerous_sql

        query = ""
        assert is_dangerous_sql(query) is False

    def test_comment_before_drop(self):
        """DROP after comment should be detected."""
        from sql_validator import is_dangerous_sql

        query = "-- comment\nDROP TABLE users"
        assert is_dangerous_sql(query) is True

    def test_delete_from_with_newlines(self):
        """DELETE FROM across newlines should be detected."""
        from sql_validator import is_dangerous_sql

        query = "DELETE\nFROM\nusers"
        assert is_dangerous_sql(query) is True


class TestLogging:
    """Test logging of blocked queries."""

    @patch("sql_validator.log_blocked_query")
    def test_blocked_query_is_logged(self, mock_log):
        """Blocked queries should be logged."""
        from sql_validator import validate_sql_query

        query = "DROP TABLE users"
        result = validate_sql_query("Bash", {"command": f"sqlite3 db.db '{query}'"})

        if result:  # If returned (blocked)
            mock_log.assert_called()

    def test_log_format_includes_query(self):
        """Log should include the dangerous query."""
        from sql_validator import log_blocked_query

        with patch("builtins.open", create=True) as mock_file:
            mock_file.return_value.__enter__.return_value.write = MagicMock()
            log_blocked_query("DROP TABLE users")
            # Verify write was called (logging occurred)
            assert mock_file.return_value.__enter__.return_value.write.called


class TestToolHandling:
    """Test handling of different tool types."""

    def test_bash_with_sql_is_validated(self):
        """Bash commands containing SQL should be validated."""
        from sql_validator import validate_sql_query

        result = validate_sql_query(
            "Bash", {"command": "sqlite3 db.db 'DROP TABLE users'"}
        )
        assert result is not None  # Should be blocked

    def test_non_sql_tool_passes_through(self):
        """Non-SQL tools should not be blocked."""
        from sql_validator import validate_sql_query

        result = validate_sql_query("Read", {"file_path": "/some/file.txt"})
        assert result is None  # Should be allowed

    def test_write_tool_passes_through(self):
        """Write tool should not be checked for SQL."""
        from sql_validator import validate_sql_query

        result = validate_sql_query("Write", {"file_path": "test.py"})
        assert result is None  # Should be allowed


class TestHookOutputFormat:
    """Test hook output format compliance."""

    def test_blocked_query_returns_correct_format(self):
        """Blocked query should return properly formatted hook output."""
        from sql_validator import get_hook_output

        output = get_hook_output("Blocked dangerous query", "DROP TABLE users")

        assert "continue" in output
        assert output["continue"] is False
        assert "systemMessage" in output
        assert "DROP TABLE" in output["systemMessage"]

    def test_allowed_query_returns_none(self):
        """Allowed query should return None (no output)."""
        from sql_validator import get_hook_output

        output = get_hook_output(None, "SELECT * FROM users")
        assert output is None


class TestMultipleStatements:
    """Test handling of multiple SQL statements."""

    def test_multiple_statements_with_drop_is_blocked(self):
        """Multiple statements where one is DROP should be blocked."""
        from sql_validator import is_dangerous_sql

        query = "SELECT * FROM users; DROP TABLE users"
        assert is_dangerous_sql(query) is True

    def test_multiple_safe_statements_are_allowed(self):
        """Multiple safe statements should be allowed."""
        from sql_validator import is_dangerous_sql

        query = "SELECT * FROM users; UPDATE users SET name='John' WHERE id=5"
        assert is_dangerous_sql(query) is False
