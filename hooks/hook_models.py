#!/usr/bin/env python3
"""
Pydantic models for Claude Code hook output schemas.

Based on official Claude Code hooks specification:
https://docs.claude.com/en/docs/claude-code/hooks
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class HookSpecificOutputBase(BaseModel):
    """Base class for hook-specific output."""

    hookEventName: str = Field(..., description="Name of the hook event")


class PreToolUseHookOutput(HookSpecificOutputBase):
    """Hook-specific output for PreToolUse events."""

    hookEventName: Literal["PreToolUse"] = "PreToolUse"
    permissionDecision: Literal["allow", "deny", "ask"] = Field(
        ...,
        description=(
            "Permission decision: 'allow' bypasses permission system, "
            "'deny' prevents execution, 'ask' requests user confirmation"
        ),
    )
    permissionDecisionReason: str | None = Field(
        None, description="Explanation for the permission decision"
    )


class PostToolUseHookOutput(HookSpecificOutputBase):
    """Hook-specific output for PostToolUse events."""

    hookEventName: Literal["PostToolUse"] = "PostToolUse"
    additionalContext: str | None = Field(
        None, description="Additional context to inject into conversation"
    )


class UserPromptSubmitHookOutput(HookSpecificOutputBase):
    """Hook-specific output for UserPromptSubmit events."""

    hookEventName: Literal["UserPromptSubmit"] = "UserPromptSubmit"
    additionalContext: str | None = Field(
        None, description="Additional context to inject into conversation"
    )


class SessionStartHookOutput(HookSpecificOutputBase):
    """Hook-specific output for SessionStart events."""

    hookEventName: Literal["SessionStart"] = "SessionStart"
    additionalContext: str | None = Field(
        None, description="Additional context to inject into conversation"
    )


class HookOutputBase(BaseModel):
    """
    Base model for all hook outputs with common fields.

    All fields are optional per the Claude Code specification.
    """

    model_config = ConfigDict(populate_by_name=True)

    continue_: bool | None = Field(
        None,
        alias="continue",
        description="Whether Claude should continue after hook execution",
    )
    stopReason: str | None = Field(
        None, description="Message shown when continue is false"
    )
    suppressOutput: bool | None = Field(
        None, description="Hide stdout from transcript mode"
    )
    systemMessage: str | None = Field(
        None, description="Warning message displayed to user"
    )


class PreToolUseOutput(HookOutputBase):
    """Complete output structure for PreToolUse hooks."""

    hookSpecificOutput: PreToolUseHookOutput


class PostToolUseOutput(HookOutputBase):
    """Complete output structure for PostToolUse hooks."""

    hookSpecificOutput: PostToolUseHookOutput
    decision: Literal["block"] | None = Field(
        None, description="Legacy decision field (use hookSpecificOutput instead)"
    )
    reason: str | None = Field(
        None, description="Legacy reason field (use hookSpecificOutput instead)"
    )


class UserPromptSubmitOutput(HookOutputBase):
    """Complete output structure for UserPromptSubmit hooks."""

    hookSpecificOutput: UserPromptSubmitHookOutput
    decision: Literal["block"] | None = Field(
        None, description="Legacy decision field (use hookSpecificOutput instead)"
    )
    reason: str | None = Field(
        None, description="Legacy reason field (use hookSpecificOutput instead)"
    )


class SessionStartOutput(HookOutputBase):
    """Complete output structure for SessionStart hooks."""

    hookSpecificOutput: SessionStartHookOutput


class StopHookOutput(HookOutputBase):
    """Complete output structure for Stop/SubagentStop hooks."""

    decision: Literal["block"] | None = Field(None, description="Block decision")
    reason: str | None = Field(
        None, description="Reason for blocking (required when blocking)"
    )
