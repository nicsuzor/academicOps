"""TDD tests for the template registry.

These tests define the expected behavior of the template registry module.
Written BEFORE implementation (TDD).
"""

from __future__ import annotations

from pathlib import Path

import pytest

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def registry():
    """Get a fresh registry instance for each test."""
    from lib.template_registry import TemplateRegistry

    TemplateRegistry.reset()
    return TemplateRegistry.instance()


@pytest.fixture
def templates_dir(tmp_path: Path) -> Path:
    """Create a temporary templates directory with test fixtures."""
    templates = tmp_path / "templates"
    templates.mkdir()

    # Create test template with frontmatter
    (templates / "test-template.md").write_text(
        """---
name: test-template
description: A test template
---
Hello {name}! Your session is {session_id}.
"""
    )

    # Create template with optional vars
    (templates / "optional-vars.md").write_text(
        """---
name: optional-vars
---
Required: {required_var}
Optional: {optional_var}
"""
    )

    # Create template without frontmatter
    (templates / "no-frontmatter.md").write_text("Plain content {var}")

    return templates


@pytest.fixture
def configured_registry(templates_dir: Path):
    """Get a registry configured with test templates directory."""
    from lib.template_registry import TemplateRegistry

    return TemplateRegistry.configure(templates_dir=templates_dir)


# =============================================================================
# SPEC LOOKUP TESTS
# =============================================================================


def test_get_spec_returns_correct_spec(registry):
    """Verify spec lookup works for known templates."""
    spec = registry.get_spec("hydration.block")
    assert spec.name == "hydration.block"
    assert spec.filename == "hydration-gate-block.md"
    assert "temp_path" in spec.required_vars


def test_get_spec_unknown_raises(registry):
    """KeyError raised for unknown template names."""
    with pytest.raises(KeyError) as exc_info:
        registry.get_spec("nonexistent.template")
    assert "nonexistent.template" in str(exc_info.value)


def test_get_spec_all_registered_templates(registry):
    """All expected templates are registered."""
    expected_names = [
        "hydration.block",
        "hydration.warn",
        "custodiet.context",
        "custodiet.instruction",
        "custodiet.fallback",
        "stop.handover_block",
        "tool.gate_message",
    ]

    for name in expected_names:
        spec = registry.get_spec(name)
        assert spec is not None, f"Template {name} not registered"
        assert spec.name == name


# =============================================================================
# RENDERING TESTS
# =============================================================================


def test_render_with_required_vars(configured_registry, templates_dir: Path):
    """Basic rendering with required variables works."""
    from lib.template_registry import TemplateCategory, TemplateSpec

    # Add a test spec to the registry
    configured_registry._specs["test.simple"] = TemplateSpec(
        name="test.simple",
        category=TemplateCategory.USER_MESSAGE,
        filename="test-template.md",
        required_vars=("name", "session_id"),
    )

    result = configured_registry.render("test.simple", {"name": "Alice", "session_id": "abc123"})
    assert "Hello Alice!" in result
    assert "Your session is abc123." in result


def test_render_missing_required_var_raises(configured_registry, templates_dir: Path):
    """ValueError raised when required variable is missing."""
    from lib.template_registry import TemplateCategory, TemplateSpec

    configured_registry._specs["test.required"] = TemplateSpec(
        name="test.required",
        category=TemplateCategory.USER_MESSAGE,
        filename="test-template.md",
        required_vars=("name", "session_id"),
    )

    with pytest.raises(ValueError) as exc_info:
        configured_registry.render("test.required", {"name": "Alice"})
    assert "session_id" in str(exc_info.value)


def test_render_with_optional_vars(configured_registry, templates_dir: Path):
    """Optional variables are interpolated when provided."""
    from lib.template_registry import TemplateCategory, TemplateSpec

    configured_registry._specs["test.optional"] = TemplateSpec(
        name="test.optional",
        category=TemplateCategory.USER_MESSAGE,
        filename="optional-vars.md",
        required_vars=("required_var",),
        optional_vars=("optional_var",),
    )

    result = configured_registry.render(
        "test.optional", {"required_var": "REQ", "optional_var": "OPT"}
    )
    assert "Required: REQ" in result
    assert "Optional: OPT" in result


def test_render_unused_optional_vars_default_empty(configured_registry, templates_dir: Path):
    """Missing optional vars get empty string default, not raise."""
    from lib.template_registry import TemplateCategory, TemplateSpec

    configured_registry._specs["test.optional"] = TemplateSpec(
        name="test.optional",
        category=TemplateCategory.USER_MESSAGE,
        filename="optional-vars.md",
        required_vars=("required_var",),
        optional_vars=("optional_var",),
    )

    # Should not raise - optional_var will be empty string
    result = configured_registry.render("test.optional", {"required_var": "REQ"})
    assert "Required: REQ" in result
    assert "Optional: " in result  # Empty string for optional


def test_render_strips_frontmatter(configured_registry, templates_dir: Path):
    """YAML frontmatter is stripped from rendered output."""
    from lib.template_registry import TemplateCategory, TemplateSpec

    configured_registry._specs["test.frontmatter"] = TemplateSpec(
        name="test.frontmatter",
        category=TemplateCategory.USER_MESSAGE,
        filename="test-template.md",
        required_vars=("name", "session_id"),
    )

    result = configured_registry.render("test.frontmatter", {"name": "Test", "session_id": "123"})
    assert "---" not in result
    assert "description:" not in result
    assert "Hello Test!" in result


def test_render_template_not_found_raises(configured_registry):
    """FileNotFoundError when template file doesn't exist."""
    from lib.template_registry import TemplateCategory, TemplateSpec

    configured_registry._specs["test.missing"] = TemplateSpec(
        name="test.missing",
        category=TemplateCategory.USER_MESSAGE,
        filename="nonexistent.md",
        required_vars=(),
    )

    with pytest.raises(FileNotFoundError):
        configured_registry.render("test.missing", {})


# =============================================================================
# LIST/FILTER TESTS
# =============================================================================


def test_list_templates_all(registry):
    """Lists all registered template names."""
    names = registry.list_templates()
    assert len(names) >= 10  # At least 10 templates defined
    assert "hydration.block" in names
    assert "custodiet.context" in names


def test_list_templates_by_category(registry):
    """Category filtering works correctly."""
    from lib.template_registry import TemplateCategory

    user_messages = registry.list_templates(category=TemplateCategory.USER_MESSAGE)
    assert "hydration.block" in user_messages
    assert "hydration.warn" in user_messages

    subagent = registry.list_templates(category=TemplateCategory.SUBAGENT_INSTRUCTION)
    assert "custodiet.context" in subagent

    # User messages should not include subagent instructions
    assert "custodiet.context" not in user_messages


# =============================================================================
# ENV OVERRIDE TESTS
# =============================================================================


def test_env_override_changes_path(configured_registry, templates_dir: Path, monkeypatch):
    """Environment variable overrides template path."""
    from lib.template_registry import TemplateCategory, TemplateSpec

    # Create override template
    override_template = templates_dir / "override.md"
    override_template.write_text("OVERRIDE: {name}")

    configured_registry._specs["test.override"] = TemplateSpec(
        name="test.override",
        category=TemplateCategory.USER_MESSAGE,
        filename="test-template.md",  # Default file
        required_vars=("name",),
        optional_vars=("session_id",),
        env_override="TEST_TEMPLATE_OVERRIDE",
    )

    # Without env var - uses default
    result1 = configured_registry.render("test.override", {"name": "Default", "session_id": "x"})
    assert "Hello Default!" in result1

    # With env var - uses override
    monkeypatch.setenv("TEST_TEMPLATE_OVERRIDE", str(override_template))
    result2 = configured_registry.render("test.override", {"name": "Custom", "session_id": "x"})
    assert "OVERRIDE: Custom" in result2


def test_env_override_missing_file_raises(configured_registry, monkeypatch):
    """FileNotFoundError when env override points to missing file."""
    from lib.template_registry import TemplateCategory, TemplateSpec

    configured_registry._specs["test.override"] = TemplateSpec(
        name="test.override",
        category=TemplateCategory.USER_MESSAGE,
        filename="test-template.md",
        required_vars=(),
        env_override="TEST_TEMPLATE_OVERRIDE",
    )

    monkeypatch.setenv("TEST_TEMPLATE_OVERRIDE", "/nonexistent/path.md")
    with pytest.raises(FileNotFoundError) as exc_info:
        configured_registry.render("test.override", {})
    assert "TEST_TEMPLATE_OVERRIDE" in str(exc_info.value)


def test_env_override_relative_path_resolution(
    configured_registry, templates_dir: Path, monkeypatch
):
    """Relative paths in env override are resolved relative to templates_dir."""
    from lib.template_registry import TemplateCategory, TemplateSpec

    # Create a subdirectory with template
    subdir = templates_dir / "overrides"
    subdir.mkdir()
    (subdir / "custom.md").write_text("CUSTOM: {name}")

    configured_registry._specs["test.relative"] = TemplateSpec(
        name="test.relative",
        category=TemplateCategory.USER_MESSAGE,
        filename="test-template.md",
        required_vars=("name",),
        optional_vars=("session_id",),
        env_override="TEST_RELATIVE_OVERRIDE",
    )

    # Relative path should resolve against templates_dir
    monkeypatch.setenv("TEST_RELATIVE_OVERRIDE", "overrides/custom.md")
    result = configured_registry.render("test.relative", {"name": "Rel", "session_id": "x"})
    assert "CUSTOM: Rel" in result


# =============================================================================
# SINGLETON & LIFECYCLE TESTS
# =============================================================================


def test_singleton_returns_same_instance():
    """instance() returns same object."""
    from lib.template_registry import TemplateRegistry

    TemplateRegistry.reset()
    reg1 = TemplateRegistry.instance()
    reg2 = TemplateRegistry.instance()
    assert reg1 is reg2


def test_reset_clears_instance():
    """reset() allows new instance creation."""
    from lib.template_registry import TemplateRegistry

    reg1 = TemplateRegistry.instance()
    TemplateRegistry.reset()
    reg2 = TemplateRegistry.instance()
    assert reg1 is not reg2


def test_configure_creates_fresh_instance(tmp_path: Path):
    """configure() resets and returns new instance with custom config."""
    from lib.template_registry import TemplateRegistry

    reg1 = TemplateRegistry.instance()
    reg2 = TemplateRegistry.configure(templates_dir=tmp_path)
    assert reg1 is not reg2
    assert reg2._templates_dir == tmp_path


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


def test_all_specs_have_valid_files(registry):
    """All registered specs point to existing template files."""
    templates_dir = Path(__file__).parent.parent.parent / "aops-core" / "hooks" / "templates"

    for name in registry.list_templates():
        spec = registry.get_spec(name)
        template_path = templates_dir / spec.filename
        assert template_path.exists(), f"Template file missing for {name}: {template_path}"


def test_all_templates_render_without_error(registry):
    """All templates can be rendered (with mock variables)."""
    templates_dir = Path(__file__).parent.parent.parent / "aops-core" / "hooks" / "templates"
    from lib.template_registry import TemplateRegistry

    # Configure with real templates dir
    reg = TemplateRegistry.configure(templates_dir=templates_dir)

    for name in reg.list_templates():
        spec = reg.get_spec(name)
        # Build mock variables
        variables = {}
        for var in spec.required_vars:
            variables[var] = f"<{var}>"
        for var in spec.optional_vars:
            variables[var] = f"<{var}>"

        # Should not raise
        result = reg.render(name, variables)
        assert isinstance(result, str)
        assert len(result) > 0


# =============================================================================
# TEMPLATE CATEGORY TESTS
# =============================================================================


def test_template_category_enum_values():
    """TemplateCategory has expected values."""
    from lib.template_registry import TemplateCategory

    assert TemplateCategory.USER_MESSAGE.value == "user_message"
    assert TemplateCategory.CONTEXT_INJECTION.value == "context_injection"
    assert TemplateCategory.SUBAGENT_INSTRUCTION.value == "subagent_instruction"


def test_spec_category_assignment(registry):
    """Templates have correct category assignments."""
    from lib.template_registry import TemplateCategory

    # User messages
    assert registry.get_spec("hydration.block").category == TemplateCategory.USER_MESSAGE
    assert registry.get_spec("hydration.warn").category == TemplateCategory.USER_MESSAGE

    # Context injection
    assert registry.get_spec("custodiet.instruction").category == TemplateCategory.CONTEXT_INJECTION
    assert registry.get_spec("stop.handover_block").category == TemplateCategory.CONTEXT_INJECTION

    # Subagent instruction
    assert registry.get_spec("custodiet.context").category == TemplateCategory.SUBAGENT_INSTRUCTION


# =============================================================================
# RENDER WITH METADATA TESTS
# =============================================================================


def test_render_with_metadata_returns_full_info(configured_registry, templates_dir: Path):
    """render_with_metadata returns content, spec, and variables used."""
    from lib.template_registry import TemplateCategory, TemplateSpec

    configured_registry._specs["test.meta"] = TemplateSpec(
        name="test.meta",
        category=TemplateCategory.USER_MESSAGE,
        filename="test-template.md",
        required_vars=("name", "session_id"),
    )

    result = configured_registry.render_with_metadata(
        "test.meta", {"name": "Alice", "session_id": "123"}
    )

    assert result.content == configured_registry.render(
        "test.meta", {"name": "Alice", "session_id": "123"}
    )
    assert result.spec.name == "test.meta"
    assert result.variables_used == {"name": "Alice", "session_id": "123"}
