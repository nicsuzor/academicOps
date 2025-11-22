"""Test YAML frontmatter parsing with special characters.

Tests validate that YAML parsing correctly handles titles and values
containing special characters like colons, which require proper quoting.
"""

from pathlib import Path

import pytest
import yaml


class TestYamlFrontmatterParsing:
    """Test YAML frontmatter parsing with special characters."""

    @pytest.mark.parametrize(
        "title,yaml_content,expected_valid",
        [
            # Properly quoted colon - should be valid
            (
                "Research: A Study",
                'title: "Research: A Study"\ntype: note',
                True,
            ),
            # Single quoted colon - should be valid
            (
                "Analysis: Results",
                "title: 'Analysis: Results'\ntype: note",
                True,
            ),
            # Unquoted colon in value - should be INVALID (parse error)
            (
                "Review: Methods",
                "title: Review: Methods\ntype: note",
                False,
            ),
            # Unquoted colon with URL-like pattern - should be INVALID
            (
                "Link: http://example.com",
                "title: Link: http://example.com\ntype: note",
                False,
            ),
            # Multiple colons unquoted - should be INVALID
            (
                "Time: 10:30:00",
                "title: Time: 10:30:00\ntype: note",
                False,
            ),
            # Properly quoted multiple colons - should be valid
            (
                "Time: 10:30:00",
                'title: "Time: 10:30:00"\ntype: note',
                True,
            ),
        ],
        ids=[
            "double_quoted_colon_valid",
            "single_quoted_colon_valid",
            "unquoted_colon_invalid",
            "unquoted_url_pattern_invalid",
            "unquoted_multiple_colons_invalid",
            "double_quoted_multiple_colons_valid",
        ],
    )
    def test_yaml_title_validity(
        self, title: str, yaml_content: str, expected_valid: bool
    ) -> None:
        """Test YAML parsing behavior with special characters in titles.

        Args:
            title: The title being tested (for documentation)
            yaml_content: YAML string to parse
            expected_valid: Whether parsing should succeed
        """
        if expected_valid:
            # Should parse without error
            result = yaml.safe_load(yaml_content)
            assert result is not None
            assert "title" in result
            assert result["title"] == title
        else:
            # Should raise a YAML parsing error
            with pytest.raises(yaml.YAMLError):
                yaml.safe_load(yaml_content)
