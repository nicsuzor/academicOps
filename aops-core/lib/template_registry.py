"""Template Registry: Centralized management of gate message templates.

Provides a unified system for:
- Template specification with required/optional variables
- Rendering with placeholder validation
- Category-based filtering (user messages, context injection, subagent instructions)
- Environment variable overrides for template paths

Usage:
    from lib.template_registry import TemplateRegistry

    registry = TemplateRegistry.instance()
    content = registry.render("hydration.block", {"temp_path": "/tmp/ctx.md"})

Exit behavior: Functions raise exceptions (fail-fast P#8). Callers handle graceful degradation.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar

from lib.template_loader import load_template


class TemplateCategory(Enum):
    """Distinguishes template purpose."""

    USER_MESSAGE = "user_message"  # Short, actionable, shown to user
    CONTEXT_INJECTION = "context_injection"  # Injected into agent context
    SUBAGENT_INSTRUCTION = "subagent_instruction"  # Rich context for subagents


@dataclass(frozen=True)
class TemplateSpec:
    """Specification for a gate template.

    Attributes:
        name: Unique identifier, e.g., "hydration.block"
        category: What kind of template (user message, context, subagent)
        filename: Template file name, e.g., "hydration-gate-block.md"
        required_vars: Variables that MUST be provided to render
        optional_vars: Variables that MAY be provided (default to empty string)
        description: Human-readable purpose
        env_override: Env var name to override template path
    """

    name: str
    category: TemplateCategory
    filename: str
    required_vars: tuple[str, ...] = ()
    optional_vars: tuple[str, ...] = ()
    description: str = ""
    env_override: str | None = None


@dataclass
class RenderedTemplate:
    """Result of rendering a template with metadata."""

    content: str
    spec: TemplateSpec
    variables_used: dict[str, Any]


# =============================================================================
# TEMPLATE SPECIFICATIONS
# =============================================================================
# All gate templates defined here. This is the single source of truth.

TEMPLATE_SPECS: dict[str, TemplateSpec] = {
    # --- Hydration gate ---
    "hydration.block": TemplateSpec(
        name="hydration.block",
        category=TemplateCategory.USER_MESSAGE,
        filename="hydration-gate-block.md",
        required_vars=("temp_path",),
        optional_vars=("session_id", "client_type"),
        description="Block message when hydration gate denies tool",
        env_override="HYDRATION_BLOCK_TEMPLATE",
    ),
    "hydration.warn": TemplateSpec(
        name="hydration.warn",
        category=TemplateCategory.USER_MESSAGE,
        filename="hydration-gate-warn.md",
        required_vars=("temp_path",),
        optional_vars=("session_id", "client_type"),
        description="Warning when hydration gate is in warn mode",
        env_override="HYDRATION_WARN_TEMPLATE",
    ),
    # --- Prompt hydrator ---
    "hydration.context": TemplateSpec(
        name="hydration.context",
        category=TemplateCategory.SUBAGENT_INSTRUCTION,
        filename="prompt-hydrator-context.md",
        required_vars=(
            "session_context",
            "axioms_content",
            "heuristics_content",
            "skills_content",
        ),
        optional_vars=(
            "prompt",
            "framework_paths",
            "mcp_tools",
            "env_vars",
            "project_paths",
            "project_context_index",
            "project_rules",
            "relevant_files",
            "workflows_index",
            "skills_index",
            "axioms",
            "heuristics",
            "task_state",
            "scripts_index",
            "session_id",
            "gate_name",
            "tool_name",
            "custodiet_mode",
        ),
        description="Unified context for hydration gate",
    ),
    "hydrator.instruction": TemplateSpec(
        name="hydrator.instruction",
        category=TemplateCategory.CONTEXT_INJECTION,
        filename="prompt-hydration-instruction.md",
        required_vars=("temp_path",),
        optional_vars=("client_type",),
        description="Instruction to invoke prompt hydrator",
    ),
    # --- Custodiet gate ---
    "custodiet.context": TemplateSpec(
        name="custodiet.context",
        category=TemplateCategory.SUBAGENT_INSTRUCTION,
        filename="custodiet-context.md",
        required_vars=(
            "session_context",
            "tool_name",
            "axioms_content",
            "heuristics_content",
            "skills_content",
            "custodiet_mode",
        ),
        optional_vars=("session_id", "gate_name"),
        description="Full context for custodiet compliance check",
        env_override="CUSTODIET_CONTEXT_TEMPLATE",
    ),
    "critic.context": TemplateSpec(
        name="critic.context",
        category=TemplateCategory.SUBAGENT_INSTRUCTION,
        filename="critic-context.md",
        required_vars=(
            "session_context",
            "tool_name",
            "axioms_content",
            "heuristics_content",
        ),
        optional_vars=("session_id", "gate_name", "custodiet_mode", "skills_content"),
        description="Deep session context for critic review (full narrative)",
    ),
    "custodiet.instruction": TemplateSpec(
        name="custodiet.instruction",
        category=TemplateCategory.CONTEXT_INJECTION,
        filename="custodiet-instruction.md",
        required_vars=("temp_path",),
        description="Instruction to invoke custodiet skill",
        env_override="CUSTODIET_INSTRUCTION_TEMPLATE",
    ),
    "custodiet.fallback": TemplateSpec(
        name="custodiet.fallback",
        category=TemplateCategory.USER_MESSAGE,
        filename="overdue-enforcement-block.md",
        required_vars=(),
        description="Fallback block when compliance check overdue",
    ),
    "custodiet.audit": TemplateSpec(
        name="custodiet.audit",
        category=TemplateCategory.SUBAGENT_INSTRUCTION,
        filename="custodiet-audit.md",
        required_vars=("session_id", "gate_name", "tool_name"),
        description="Audit context for custodiet gate",
    ),
    # --- Task gate ---
    "task.block": TemplateSpec(
        name="task.block",
        category=TemplateCategory.USER_MESSAGE,
        filename="task-gate-block.md",
        required_vars=(
            "task_bound_status",
            "hydrator_invoked_status",
            "critic_invoked_status",
            "missing_gates",
        ),
        description="Block message when task gate denies tool",
        env_override="TASK_GATE_BLOCK_TEMPLATE",
    ),
    "task.warn": TemplateSpec(
        name="task.warn",
        category=TemplateCategory.USER_MESSAGE,
        filename="task-gate-warn.md",
        required_vars=(
            "task_bound_status",
            "hydrator_invoked_status",
            "critic_invoked_status",
        ),
        description="Warning when task gate is in warn mode",
        env_override="TASK_GATE_WARN_TEMPLATE",
    ),
    # --- Stop gate ---
    "stop.critic": TemplateSpec(
        name="stop.critic",
        category=TemplateCategory.CONTEXT_INJECTION,
        filename="stop-gate-critic.md",
        required_vars=(),
        description="Instruction to invoke critic before stopping",
        env_override="STOP_GATE_CRITIC_TEMPLATE",
    ),
    "stop.handover_block": TemplateSpec(
        name="stop.handover_block",
        category=TemplateCategory.CONTEXT_INJECTION,
        filename="stop-gate-handover-block.md",
        required_vars=(),
        description="Block message requiring handover before stop",
        env_override="STOP_GATE_HANDOVER_TEMPLATE",
    ),
    "stop.handover_warn": TemplateSpec(
        name="stop.handover_warn",
        category=TemplateCategory.CONTEXT_INJECTION,
        filename="stop-gate-handover-warn.md",
        required_vars=(),
        description="Warning about handover before stop",
    ),
    # --- Tool gate (unified PreToolUse message) ---
    "tool.gate_message": TemplateSpec(
        name="tool.gate_message",
        category=TemplateCategory.USER_MESSAGE,
        filename="tool-gate-message.md",
        required_vars=(
            "mode",
            "tool_name",
            "tool_category",
            "missing_gates",
            "gate_status",
            "next_instruction",
        ),
        description="Unified tool gate block/warn message",
    ),
    # --- Utility templates ---
    "fail_fast.reminder": TemplateSpec(
        name="fail_fast.reminder",
        category=TemplateCategory.CONTEXT_INJECTION,
        filename="fail-fast-reminder.md",
        required_vars=(),
        description="Reminder when tool returns error",
    ),
    "simple_question.instruction": TemplateSpec(
        name="simple_question.instruction",
        category=TemplateCategory.CONTEXT_INJECTION,
        filename="simple-question-instruction.md",
        required_vars=(),
        description="Instruction for simple question handling",
    ),
}


# =============================================================================
# TEMPLATE REGISTRY
# =============================================================================


class TemplateRegistry:
    """Central registry for gate templates.

    Singleton pattern - use instance() to get the shared instance.
    Use reset() or configure() for test isolation.
    """

    _instance: ClassVar[TemplateRegistry | None] = None

    def __init__(self) -> None:
        """Initialize registry with default templates directory."""
        self._specs: dict[str, TemplateSpec] = TEMPLATE_SPECS.copy()
        self._templates_dir: Path = Path(__file__).parent.parent / "hooks" / "templates"

    @classmethod
    def instance(cls) -> TemplateRegistry:
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton for test isolation. Call in test teardown."""
        cls._instance = None

    @classmethod
    def configure(cls, templates_dir: Path | None = None) -> TemplateRegistry:
        """Reset and reconfigure registry. Returns new instance.

        Use in tests to inject custom templates_dir.

        Args:
            templates_dir: Custom templates directory path

        Returns:
            New TemplateRegistry instance
        """
        cls.reset()
        instance = cls()
        if templates_dir:
            instance._templates_dir = templates_dir
        cls._instance = instance
        return instance

    def get_spec(self, name: str) -> TemplateSpec:
        """Get template specification by name.

        Args:
            name: Template name (e.g., "hydration.block")

        Returns:
            TemplateSpec for the template

        Raises:
            KeyError: Template not found
        """
        if name not in self._specs:
            raise KeyError(f"Template not found: {name}")
        return self._specs[name]

    def list_templates(self, category: TemplateCategory | None = None) -> list[str]:
        """List all template names, optionally filtered by category.

        Args:
            category: Optional category filter

        Returns:
            List of template names
        """
        if category is None:
            return list(self._specs.keys())
        return [name for name, spec in self._specs.items() if spec.category == category]

    def render(self, name: str, variables: dict[str, Any] | None = None) -> str:
        """Render a template by name with variables.

        Args:
            name: Template name (e.g., "hydration.block")
            variables: Variables to interpolate

        Returns:
            Rendered template content as string

        Raises:
            KeyError: Template not found
            ValueError: Required variable missing
            FileNotFoundError: Template file not found
        """
        return self.render_with_metadata(name, variables).content

    def render_with_metadata(
        self, name: str, variables: dict[str, Any] | None = None
    ) -> RenderedTemplate:
        """Render a template with full metadata.

        Args:
            name: Template name (e.g., "hydration.block")
            variables: Variables to interpolate

        Returns:
            RenderedTemplate with content, spec, and variables used

        Raises:
            KeyError: Template not found
            ValueError: Required variable missing
            FileNotFoundError: Template file not found
        """
        spec = self.get_spec(name)
        variables = variables or {}

        # Validate required variables
        missing = [var for var in spec.required_vars if var not in variables]
        if missing:
            raise ValueError(f"Template '{name}' missing required variables: {', '.join(missing)}")

        # Build complete variables dict with optional defaults
        complete_vars = dict(variables)
        for var in spec.optional_vars:
            if var not in complete_vars:
                complete_vars[var] = ""

        # Resolve template path (with env override support)
        template_path = self._resolve_template_path(spec)

        # Load and render
        content = load_template(template_path, complete_vars)

        return RenderedTemplate(
            content=content,
            spec=spec,
            variables_used=variables,
        )

    def _resolve_template_path(self, spec: TemplateSpec) -> Path:
        """Resolve actual template path, checking env override.

        Priority:
        1. Environment variable (if set and file exists)
        2. Default path in templates_dir

        Args:
            spec: Template specification

        Returns:
            Path to template file

        Raises:
            FileNotFoundError: If resolved path doesn't exist (fail-fast P#8)
        """
        if spec.env_override:
            override = os.environ.get(spec.env_override)
            if override:
                # Env var can be absolute or relative to templates_dir
                path = Path(override)
                if not path.is_absolute():
                    path = self._templates_dir / path
                if not path.exists():
                    raise FileNotFoundError(
                        f"Template override {spec.env_override}={override} points to "
                        f"non-existent file: {path}"
                    )
                return path

        # Default path
        default = self._templates_dir / spec.filename
        if not default.exists():
            raise FileNotFoundError(f"Template not found: {default}")
        return default
