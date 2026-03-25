"""
Internal Pydantic models for hook scripts.

These models define typed structures for internal hook operations.
External API contracts are defined in schemas.py (HookContext, CanonicalHookOutput).
"""

from pydantic import BaseModel, Field

from hooks.schemas import HookContext


class SessionCleanupResult(BaseModel):
    """Result of end-of-session cleanup operations.

    Cleanup steps (fail-fast order):
    1. Generate transcript (includes insights extraction)
    2. Verify insights JSON exists
    3. Delete session state file

    Attributes:
        success: All cleanup steps succeeded
        transcript_generated: Transcript was generated successfully
        insights_verified: Insights JSON file exists
        state_deleted: Session state file was deleted
        message: Human-readable status message
    """

    success: bool = False
    transcript_generated: bool = False
    insights_verified: bool = False
    state_deleted: bool = False
    message: str = ""


# --- Autocommit State Models (autocommit_state.py) ---


class RepoSyncStatus(BaseModel):
    """Status of repository sync operation.

    Attributes:
        can_sync: Whether sync is possible (not detached HEAD, has tracking)
        reason: Reason if sync not possible
        is_behind: Local is behind remote
        commits_behind: Number of commits behind remote
        fetch_error: Error from fetch operation if any
    """

    can_sync: bool = True
    reason: str = ""
    is_behind: bool = False
    commits_behind: int = 0
    fetch_error: str = ""


class CommitPushResult(BaseModel):
    """Result of commit and push operation.

    Attributes:
        success: Operation completed successfully
        committed: Changes were committed
        pushed: Changes were pushed to remote
        sync_warning: Warning message from sync operation
        message: Human-readable status message
    """

    success: bool = False
    committed: bool = False
    pushed: bool = False
    sync_warning: str = ""
    message: str = ""


class HookLogEntry(HookContext):
    """Single entry in the per-session hooks JSONL log.
    Inherits all fields from HookContext, plus additional metadata and caching.

    Attributes:
        hook_event: Name of the hook event (e.g., UserPromptSubmit)
        trace_id: Unique ID for this specific hook invocation
        logged_at: ISO timestamp when event was logged
        exit_code: Exit code of the hook (0 = success)
    """

    hook_event: str
    trace_id: str | None = None
    logged_at: str
    exit_code: int = 0
    output: dict | None = None
    raw_input: dict = Field(default_factory=dict)


# --- Policy Enforcer Models (policy_enforcer.py) ---


class PolicyCheckResult(BaseModel):
    """Result of a policy check.

    Attributes:
        passed: Policy check passed
        policy_name: Name of the policy that was checked
        message: Human-readable result message
        details: Additional details about the check
    """

    passed: bool = True
    policy_name: str = ""
    message: str = ""
    details: dict = Field(default_factory=dict)
