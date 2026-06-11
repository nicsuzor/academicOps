"""Consumer-side accept-contract for the Antigravity (agy) hook harness.

WHY THIS EXISTS
---------------
The agy/antigravity harness (`json_hook_caller.go`) parses every hook result as
**protojson** against `exa.hooks_pb.*Result` and rejects on the first unknown
field. Our router historically had **zero** consumer-side coverage of that
accept-contract (`grep -r protojson|protobuf` over the repo = 0 hits), so when
commit ``4c73f02a`` ("update agy build", 2026-06-03) folded ``--client agy``
into the Claude-schema ``output_for_gemini`` path, every agy hook verdict began
being silently discarded by the harness — and CI stayed green. See task
``aops-27004ffd`` (finding) and ``aops-2dc18411`` (the live-agy fix epic).

The live, in-container failure looked like (verbatim from cli.log):

    post-hook ... failed to unmarshal result via protojson:
      {"decision":"allow","metadata":{}}: proto: unknown field "decision"
    pre-tool hook ... {"systemMessage":"...","decision":"deny",...}:
      unknown field "systemMessage"

This module encodes that accept-contract as strict (``extra="forbid"``) Pydantic
models so the per-client acceptance test (``test_agy_protojson_contract.py``)
can reproduce the rejection deterministically in CI, instead of only surfacing
it in a live agy session whose logs get auto-nuked.

PROVENANCE / CAVEAT
-------------------
The field map below is transcribed from the ``exa.hooks_pb`` binary descriptor
notes recorded in epic ``aops-2dc18411``. Two things are deliberately NOT pinned
here because they are not yet live-verified (blocked task ``aops-939b6c3a``):

  * the enum STRING values for ``decision`` (Pre/Stop) and ``terminationBehavior``
    (PostInvocation) — typed as free ``str`` so this contract does not assert a
    guessed enum;
  * Struct-typed fields (``overwrite``, injected-step bodies) — modelled loosely
    as ``dict`` since their inner shape is not load-bearing for the
    unknown-field rejection this guard targets.

``extra="forbid"`` reproduces protojson's *unknown-field* rejection (the actual
failure mode). protojson is additionally strict about types/oneofs; this model
guards the unknown-field axis only, which is the one ``4c73f02a`` tripped.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

__all__ = [
    "PermissionOverride",
    "PreToolHookResult",
    "PostToolHookResult",
    "PreInvocationHookResult",
    "PostInvocationHookResult",
    "StopHookResult",
    "ACCEPT_MODEL_BY_EVENT",
    "is_accepted_by_agy",
]


class _Strict(BaseModel):
    """Base for every accept model: reject unknown fields like protojson does."""

    model_config = ConfigDict(extra="forbid")


class PermissionOverride(BaseModel):
    """One entry of the ``PreToolHookResult.permission_overrides`` *repeated* list.

    The inner shape (tool-name / read-only / reason etc.) is not load-bearing for
    the unknown-field rejection axis this contract guards, so the body is left
    loose (``extra="allow"``). The CRITICAL fact this contract pins is that
    ``permissionOverrides`` is a *repeated* (list-valued) field in protojson —
    NOT a single message — and that ``allowTool`` / ``denyReason`` are TOP-LEVEL
    fields of ``PreToolHookResult``, not nested here. Nesting them under a
    message-valued ``permissionOverrides`` produced a protojson syntax error
    (expected ``[`` for the repeated field, got ``{``) and silently dropped
    every enforcer DENY in live agy (aops-891c0e36).
    """

    model_config = ConfigDict(extra="allow")


class PreToolHookResult(_Strict):
    """``exa.hooks_pb.PreToolHookResult``.

    Allow is the empty object ``{}``. A deny is expressed structurally via the
    TOP-LEVEL ``allowTool=false`` + ``denyReason`` fields — that path needs NO
    enum string, which is why it is implementable/verifiable ahead of the
    ``decision`` enum discovery.

    Field map sourced from the ``exa.hooks_pb`` FileDescriptorProto embedded in
    the agy binary (aops-891c0e36):

        PreToolHookResult
          decision              (string)
          reason                (string)
          overwrite             (google.protobuf.Struct)
          permission_overrides  (REPEATED PermissionOverride — protojson list)
          allow_tool            (bool, top-level)
          deny_reason           (string, top-level)
    """

    decision: str | None = None
    reason: str | None = None
    overwrite: dict[str, Any] | None = None  # google.protobuf.Struct
    permissionOverrides: list[PermissionOverride] | None = None
    allowTool: bool | None = None
    denyReason: str | None = None


class PostToolHookResult(_Strict):
    """``exa.hooks_pb.PostToolHookResult`` — empty object ``{}``."""


class HookInjectedStep(_Strict):
    """``exa.hooks_pb.HookInjectedStep`` — oneof step body.

    Field types decoded directly from the ``exa.hooks_pb`` FileDescriptorProto
    embedded in the agy 1.0.7 binary (``~/.local/bin/agy``, FieldDescriptorProto
    ``type`` field per member, aops-2dc18411 follow-up):

        oneof step:
          tool_call          (1)  TYPE_MESSAGE  .exa.hooks_pb.HookToolCall
          user_message       (2)  TYPE_STRING   (scalar — NOT a nested message)
          ephemeral_message  (3)  TYPE_STRING   (scalar — NOT a nested message)
          system_message     (4)  TYPE_MESSAGE  .exa.hooks_pb.HookSystemMessage

    ``HookSystemMessage`` is ``{system_message:string, metadata}``, so the
    ``systemMessage`` member is the nested ``{"systemMessage": "..."}`` object;
    ``userMessage`` / ``ephemeralMessage`` are PLAIN STRINGS in protojson
    (``{"ephemeralMessage": "..."}``), not objects. Modelling them as ``dict``
    was wrong and would have masked a malformed string-vs-message emission.
    """

    toolCall: dict[str, Any] | None = None
    userMessage: str | None = None
    ephemeralMessage: str | None = None
    systemMessage: dict[str, Any] | None = None


class PreInvocationHookResult(_Strict):
    injectSteps: list[HookInjectedStep] | None = None


class PostInvocationHookResult(_Strict):
    injectSteps: list[HookInjectedStep] | None = None
    terminationBehavior: str | None = None


class StopHookResult(_Strict):
    decision: str | None = None
    reason: str | None = None


# Map the hook event the harness fires to the `*Result` it will parse the
# router's stdout against. PreInvocation/PostInvocation correspond to the
# router's UserPromptSubmit/Stop internal events, but the agy harness consumes
# them under their native Antigravity names.
ACCEPT_MODEL_BY_EVENT: dict[str, type[_Strict]] = {
    "PreToolUse": PreToolHookResult,
    "PostToolUse": PostToolHookResult,
    "PreInvocation": PreInvocationHookResult,
    "PostInvocation": PostInvocationHookResult,
    "Stop": StopHookResult,
}


def is_accepted_by_agy(payload: dict[str, Any], event: str) -> tuple[bool, str]:
    """Return (accepted, detail) for a router output payload under `event`.

    `accepted` is True iff the payload validates against the agy accept model
    for that event (i.e. the agy harness would NOT reject it on an unknown
    field). `detail` carries the offending field(s) when rejected.
    """
    model = ACCEPT_MODEL_BY_EVENT.get(event)
    if model is None:
        raise KeyError(f"No agy accept model registered for event {event!r}")
    try:
        model.model_validate(payload)
        return True, ""
    except ValidationError as exc:
        fields = ", ".join(".".join(str(p) for p in err["loc"]) for err in exc.errors())
        return False, fields
