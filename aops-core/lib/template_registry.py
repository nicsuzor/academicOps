"""Template Registry: Centralized management of gate message templates.

Provides a unified system for:
- Template specification with required/optional variables
- Rendering with placeholder validation
- Category-based filtering (user messages, context injection, subagent instructions)
- Environment variable overrides for template paths

Usage:
    from lib.template_registry import TemplateRegistry

    registry = TemplateRegistry.instance()
    content = registry.render("exit_reflection.policy_message", {})

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
        name: Unique identifier, e.g., "rbg.policy_message"
        category: What kind of template (user message, context, subagent)
        filename: Template file name, e.g., "rbg-policy-message.md"
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
    "hydration.warn": TemplateSpec(
        name="hydration.warn",
        category=TemplateCategory.USER_MESSAGE,
        filename="hydration-gate-warn.md",
        required_vars=(),
        optional_vars=("session_id", "client_type"),
        description="Lightweight skills-routing hint (formerly hydration warning)",
        env_override="HYDRATION_WARN_TEMPLATE",
    ),
    "pkb.nudge": TemplateSpec(
        name="pkb.nudge",
        category=TemplateCategory.CONTEXT_INJECTION,
        filename="pkb-nudge.md",
        required_vars=(),
        optional_vars=(),
        description="Static UPS nudge to search the PKB before relying on memory (T0)",
        env_override="PKB_NUDGE_TEMPLATE",
    ),
    "task_notification.guidance": TemplateSpec(
        name="task_notification.guidance",
        category=TemplateCategory.CONTEXT_INJECTION,
        filename="task-notification-guidance.md",
        required_vars=(),
        optional_vars=(),
        description="Guidance injected on background task-notification prompts: act on it, absorb routine completions silently",
        env_override="TASK_NOTIFICATION_GUIDANCE_TEMPLATE",
    ),
    # --- Exit-reflection gate (consolidated rbg-review + qa + handover,
    # aops_4c2949d9) ---
    "exit_reflection.context": TemplateSpec(
        name="exit_reflection.context",
        category=TemplateCategory.SUBAGENT_INSTRUCTION,
        filename="exit-reflection-context.md",
        required_vars=(
            "session_context",
            "tool_name",
        ),
        optional_vars=("session_id", "gate_name", "active_skill", "skill_scope"),
        description="Turn record written to the temp file the FULL-tier exit-reflection checklist reads",
    ),
    "exit_reflection.bound": TemplateSpec(
        name="exit_reflection.bound",
        category=TemplateCategory.USER_MESSAGE,
        filename="exit-reflection-bound.md",
        required_vars=(),
        description="Status message when a task is bound and full exit-reflection will be required before exit",
    ),
    "exit_reflection.complete": TemplateSpec(
        name="exit_reflection.complete",
        category=TemplateCategory.USER_MESSAGE,
        filename="exit-reflection-complete.md",
        required_vars=(),
        description="Status message when the reflection auditor ran or a legal exit (honest completion/failure, /end-session, /dump, /continue) opened the gate",
    ),
    "exit_reflection.policy_message": TemplateSpec(
        name="exit_reflection.policy_message",
        category=TemplateCategory.USER_MESSAGE,
        filename="exit-reflection-policy-message.md",
        required_vars=(),
        description="Short user-facing message when the FULL-tier exit-reflection policy blocks/warns on Stop",
    ),
    "exit_reflection.policy_context": TemplateSpec(
        name="exit_reflection.policy_context",
        category=TemplateCategory.CONTEXT_INJECTION,
        filename="exit-reflection-policy-context.md",
        required_vars=("temp_path",),
        description="Full FULL-tier checklist context injection: RBG-lens self-audit, durable capture, commit/push/PR, /learn, /remember, prose handover with substance-vs-form guardrail",
    ),
    "exit_reflection.lite_reminder": TemplateSpec(
        name="exit_reflection.lite_reminder",
        category=TemplateCategory.CONTEXT_INJECTION,
        filename="exit-reflection-lite-reminder.md",
        required_vars=(),
        description="LITE-tier honesty/self-reflection reminder (ida-gate lineage) for subagents, sessions with no bound task, or read-only turns",
    ),
    "exit_reflection.degraded": TemplateSpec(
        name="exit_reflection.degraded",
        category=TemplateCategory.USER_MESSAGE,
        filename="exit-reflection-degraded.md",
        required_vars=("threshold",),
        description="Loud escape-hatch message when the FULL-tier exit-reflection gate degrades DENY to WARN-and-allow",
    ),
    # --- Ida (Ida B. Wells — proof-of-claim reminder) gate ---
    "ida.reminder": TemplateSpec(
        name="ida.reminder",
        category=TemplateCategory.CONTEXT_INJECTION,
        filename="ida-reminder.md",
        required_vars=(),
        description="Agent-facing honesty check injected into context on Stop",
    ),
    # ida.policy_message (ida-policy-message.md) removed: warn mode shows no
    # separate user banner (delivered non-blockingly via additionalContext,
    # same channel every warn-mode Stop gate uses), and block mode carries its
    # short line inline (gates/definitions.py).
    "ida.askuserquestion_reminder": TemplateSpec(
        name="ida.askuserquestion_reminder",
        category=TemplateCategory.CONTEXT_INJECTION,
        filename="ida-askuserquestion-reminder.md",
        required_vars=(),
        description="Capability-verification nudge injected on PreToolUse AskUserQuestion",
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
