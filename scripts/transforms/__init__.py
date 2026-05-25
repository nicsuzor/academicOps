from .agent_schema import claude_agent_schema, gemini_agent_schema
from .hooks import gemini_hooks
from .tool_translation import translate_tool_calls_claude, translate_tool_calls_gemini

TRANSFORMS = {
    "translate_tool_calls_claude": translate_tool_calls_claude,
    "translate_tool_calls_gemini": translate_tool_calls_gemini,
    "claude_agent_schema": claude_agent_schema,
    "gemini_agent_schema": gemini_agent_schema,
    "gemini_hooks": gemini_hooks,
}


def apply_transforms(content: str, transform_names: list[str], ctx: dict) -> str:
    """Apply a list of transforms to the content."""
    for name in transform_names:
        if name not in TRANSFORMS:
            raise ValueError(f"Unknown transform: {name}")
        content = TRANSFORMS[name](content, ctx)
    return content
