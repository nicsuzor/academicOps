"""Tests for code review rules.

These tests define the behavior of our code review system that enforces coding standards.
"""

from pathlib import Path


class TestEnvironmentVariableRule:
    """Test rule that enforces config/fixture usage instead of direct env var access."""

    def test_detects_os_getenv_in_test_files(self):
        """Rule should catch os.getenv() in test files."""
        from bot.scripts.code_review import EnvironmentVariableRule

        code = """
def test_something():
    api_key = os.getenv("ZOTERO_API_KEY")
    assert api_key
"""

        rule = EnvironmentVariableRule()
        violations = rule.check(Path("tests/test_foo.py"), code)

        assert len(violations) == 1
        assert violations[0].rule == "no-direct-env-vars"
        assert "fixture" in violations[0].fix.lower()
        assert violations[0].line == 3  # Line with os.getenv

    def test_detects_os_environ_dict_access_in_tests(self):
        """Rule should catch os.environ['KEY'] in test files."""
        from bot.scripts.code_review import EnvironmentVariableRule

        code = """
def test_something():
    api_key = os.environ["API_KEY"]
"""

        rule = EnvironmentVariableRule()
        violations = rule.check(Path("tests/test_bar.py"), code)

        assert len(violations) == 1
        assert violations[0].rule == "no-direct-env-vars"

    def test_detects_os_environ_get_in_tests(self):
        """Rule should catch os.environ.get() in test files."""
        from bot.scripts.code_review import EnvironmentVariableRule

        code = 'api_key = os.environ.get("KEY", "default")'

        rule = EnvironmentVariableRule()
        violations = rule.check(Path("tests/integration/test_api.py"), code)

        assert len(violations) == 1

    def test_allows_env_vars_in_non_test_files(self):
        """Rule should NOT flag os.getenv() in non-test code (config, etc)."""
        from bot.scripts.code_review import EnvironmentVariableRule

        code = """
# Configuration module
api_key = os.getenv("API_KEY")
"""

        rule = EnvironmentVariableRule()
        violations = rule.check(Path("src/config.py"), code)

        assert len(violations) == 0, "Should allow env vars in non-test files"

    def test_allows_env_vars_in_fixtures_conftest(self):
        """Rule should allow env vars in conftest.py fixtures (that's where config lives)."""
        from bot.scripts.code_review import EnvironmentVariableRule

        code = """
@pytest.fixture
def testing_config():
    return Config(api_key=os.getenv("TEST_API_KEY"))
"""

        rule = EnvironmentVariableRule()
        violations = rule.check(Path("tests/conftest.py"), code)

        assert len(violations) == 0, "conftest.py fixtures can use env vars"


class TestMockUsageRule:
    """Test rule that enforces live fixtures for own code."""

    def test_detects_mock_for_buttermilk_classes(self):
        """Rule should catch Mock() used for ZoteroSource (buttermilk code)."""
        from bot.scripts.code_review import MockUsageRule

        code = """
def test_foo():
    mock_api = Mock()
    mock_api.items.return_value = [...]

    with patch.object(ZoteroSource, "zot", new_callable=lambda: property(lambda self: mock_api)):
        source = ZoteroSource(library_id="123")
"""

        rule = MockUsageRule()
        violations = rule.check(
            Path("projects/buttermilk/tests/test_zotero_v2.py"), code
        )

        assert len(violations) == 1
        assert violations[0].rule == "no-mocks-for-own-code"
        assert "live fixtures" in violations[0].message.lower()
        assert "ZoteroSource" in violations[0].message

    def test_allows_mocks_for_external_libraries(self):
        """Rule should allow Mock() for external APIs (pyzotero, requests, etc)."""
        from bot.scripts.code_review import MockUsageRule

        code = """
def test_api_call():
    # Mocking external library is fine
    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = {"data": "test"}
        result = fetch_data()
"""

        rule = MockUsageRule()
        violations = rule.check(Path("projects/buttermilk/tests/test_api.py"), code)

        assert len(violations) == 0, "Should allow mocks for external libs"

    def test_only_checks_buttermilk_tests(self):
        """Rule should only apply to buttermilk tests, not general test infrastructure."""
        from bot.scripts.code_review import MockUsageRule

        code = """
def test_hook():
    mock = Mock()
    result = validate_tool("Write", {}, mock)
"""

        rule = MockUsageRule()
        violations = rule.check(Path("bot/tests/test_validate_tool.py"), code)

        assert len(violations) == 0, "Should not check non-buttermilk tests"


class TestCodeReviewer:
    """Test the main code review orchestrator."""

    def test_checks_all_rules_on_file(self):
        """CodeReviewer should run all registered rules."""
        from bot.scripts.code_review import CodeReviewer

        code = """
def test_bad():
    api_key = os.getenv("KEY")
    mock_zotero = Mock()
    source = ZoteroSource(library_id="123")
"""

        reviewer = CodeReviewer()
        violations = reviewer.check_file(
            Path("projects/buttermilk/tests/test_bad.py"), code
        )

        # Should catch both: env var + mock usage (ZoteroSource mentioned)
        assert len(violations) >= 2
        rules_triggered = {v.rule for v in violations}
        assert "no-direct-env-vars" in rules_triggered
        assert "no-mocks-for-own-code" in rules_triggered

    def test_formats_violations_for_display(self):
        """CodeReviewer should format violations with file, line, and fix."""
        from bot.scripts.code_review import CodeReviewer, Violation

        violations = [
            Violation(
                file=Path("tests/test_foo.py"),
                line=10,
                rule="no-direct-env-vars",
                message="Use config instead of os.getenv()",
                fix="Create pytest fixture that uses testing.yaml",
            )
        ]

        reviewer = CodeReviewer()
        formatted = reviewer.format_violations(violations)

        assert "tests/test_foo.py:10" in formatted
        assert "no-direct-env-vars" in formatted
        assert "Use config instead" in formatted
        assert "pytest fixture" in formatted


class TestFileLocationRule:
    """Test rule that enforces proper test file locations (academicOps axiom #5)."""

    def test_blocks_tmp_test_files(self):
        """Test files in /tmp should be blocked (violates axiom #5: build for replication)."""
        from bot.scripts.code_review import TestFileLocationRule

        rule = TestFileLocationRule()
        violations = rule.check(Path("/tmp/test_foo.py"), "")

        assert len(violations) == 1
        assert violations[0].rule == "no-tmp-tests"
        assert "axiom #5" in violations[0].message
        assert "projects/" in violations[0].fix

    def test_allows_proper_project_tests(self):
        """Test files in projects/*/tests/ should be allowed."""
        from bot.scripts.code_review import TestFileLocationRule

        rule = TestFileLocationRule()
        violations = rule.check(Path("projects/buttermilk/tests/test_foo.py"), "")

        assert len(violations) == 0

    def test_blocks_tests_outside_tests_directory(self):
        """Test files outside tests/ directories should be blocked."""
        from bot.scripts.code_review import TestFileLocationRule

        rule = TestFileLocationRule()
        violations = rule.check(Path("projects/buttermilk/test_foo.py"), "")

        assert len(violations) == 1
        assert violations[0].rule == "tests-in-tests-dir"
        assert "tests/ directory" in violations[0].message

    def test_allows_bot_framework_tests(self):
        """Framework tests in bot/tests/ should be allowed."""
        from bot.scripts.code_review import TestFileLocationRule

        rule = TestFileLocationRule()
        violations = rule.check(Path("bot/tests/test_validation.py"), "")

        assert len(violations) == 0

    def test_ignores_non_test_files(self):
        """Non-test files should not be checked."""
        from bot.scripts.code_review import TestFileLocationRule

        rule = TestFileLocationRule()

        # /tmp Python file without "test" in name - allowed (not a test)
        violations = rule.check(Path("/tmp/script.py"), "")
        assert len(violations) == 0

        # Regular source file - allowed (not a test)
        violations = rule.check(Path("projects/buttermilk/src/config.py"), "")
        assert len(violations) == 0


class TestGitIntegration:
    """Test git commit hook integration."""

    def test_get_staged_files(self):
        """Should get list of staged files from git."""
        from bot.scripts.code_review import get_staged_files

        # This test would need to be run in a git repo with staged files
        # For now, just test it returns a list
        files = get_staged_files()
        assert isinstance(files, list)

    def test_skips_non_python_files(self):
        """Should only check Python files."""
        from bot.scripts.code_review import CodeReviewer

        reviewer = CodeReviewer()

        # Should not try to parse JavaScript
        violations = reviewer.check_file(Path("src/app.js"), "const x = 1;")
        assert len(violations) == 0
