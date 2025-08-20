"""Unified Task model for all task sources (email, Slack, notes, etc.)."""
from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, Field, PrivateAttr


class Task(BaseModel):
    """Universal task representation for the academicOps system.
    
    Tasks can originate from various sources (email, Slack, notes, Zoom, etc.)
    but all share this common schema. Source-specific data goes in the 'source' field.
    """
    
    # Core task fields (required)
    id: str = Field(description="Unique task identifier (format: YYYYMMDD-<8hex>)")
    title: str = Field(description="Brief task title")
    description: str = Field(description="Full task description or summary")
    classification: Literal["Action", "Waiting", "Reference", "Optional", "Noise"] = Field(
        description="Task classification for triage"
    )
    priority: int = Field(description="Priority level: 1=High, 2=Medium, 3=Low", ge=1, le=3)
    created: str = Field(description="ISO 8601 timestamp of task creation")
    
    # Task management fields (optional)
    type: str = Field(default="generic", description="Task type: email_reply, slack_message, note, zoom_action, etc.")
    project: str = Field(default="", description="Associated project identifier")
    due: Optional[str] = Field(default=None, description="ISO 8601 timestamp of due date")
    preview: Optional[str] = Field(default=None, description="Short preview text (max ~160 chars)")
    
    # Source-specific data (flexible)
    # This replaces the old 'metadata' field and contains all source-specific information
    source: Dict[str, Any] = Field(
        default_factory=dict,
        description="Source-specific data. For email: {type: 'email', email_id, sender, etc.}"
    )
    
    # Analysis/AI fields (optional)
    summary: Optional[str] = Field(default=None, description="AI-generated summary")
    action_required: Optional[str] = Field(default=None, description="Specific action needed")
    requires_reply: Optional[bool] = Field(default=None, description="Whether task requires a reply")
    time_estimate: Optional[float] = Field(default=None, description="Estimated time in hours")
    response_draft: Optional[str] = Field(default=None, description="Draft response (for emails)")
    
    # System fields (optional)
    archived_at: Optional[str] = Field(default=None, description="ISO 8601 timestamp when archived")
    completed_at: Optional[str] = Field(default=None, description="ISO 8601 timestamp when completed")
    
    # Internal fields (not persisted, used by scripts)
    _filename: Optional[str] = PrivateAttr(default=None)
    
    class Config:
        # Allow extra fields for forward compatibility
        extra = "allow"
        # Use enum values for serialization
        use_enum_values = True
    
    def dict(self, **kwargs):
        """Override to ensure _filename is excluded from serialization."""
        kwargs.setdefault('exclude', set()).add('_filename')
        return super().dict(**kwargs)
    
    @classmethod
    def from_email(cls, email_data: dict, triage_result: dict) -> "Task":
        """Factory method to create a Task from email data and triage results.
        
        Args:
            email_data: Raw email data from Outlook
            triage_result: Analysis results from LLM triage
        
        Returns:
            Task instance configured for email source
        """
        from datetime import datetime, timezone
        import re
        
        def task_id() -> str:
            """Generate a compact task ID."""
            import time
            import uuid
            ts = datetime.now(timezone.utc).strftime("%Y%m%d")
            try:
                u = uuid.uuid4().hex[:8]
            except Exception:
                u = f"{int(time.time()*1000)%0xffffffff:08x}"
            return f"{ts}-{u}"
        
        def clip(s: str, n: int) -> str:
            """Clip string to max length."""
            if not s:
                return ""
            s2 = re.sub(r"\s+", " ", str(s)).strip()
            return s2 if len(s2) <= n else s2[:n-1] + "…"
        
        def get_field(d: dict, *paths, default=None):
            """Get field from dict with fallback paths."""
            for p in paths:
                if p in d and d[p] is not None:
                    return d[p]
            return default
        
        # Extract email fields
        email_id = get_field(email_data, "id", "Id")
        subject = get_field(email_data, "subject", "Subject", default="(no subject)")
        sender_email = get_field(email_data, "senderAddress", "sender_email", "senderEmailAddress", "From", "sender", default="")
        sender_name = get_field(email_data, "senderName", "FromName", default="")
        to_field = get_field(email_data, "to", "To", default="")
        cc_field = get_field(email_data, "cc", "Cc", default="")
        received_time = get_field(email_data, "receivedTime", "date", "Date", default=None)
        importance = get_field(email_data, "importance", default="Normal")
        has_attachments = bool(get_field(email_data, "hasAttachments", default=False))
        attachments = [a.get("fileName") or a.get("name") for a in (email_data.get("attachments") or []) if isinstance(a, dict)]
        
        # Build preview
        preview = clip(
            get_field(email_data, "snippet", "preview", "bodyPreview", "BodyPreview", "textBody", "TextBody", "body", "Body", default=""),
            160
        )
        
        # Build source data (all email-specific fields)
        source_data = {
            "type": "email",
            "email_id": email_id,
            "sender": sender_email,
            "sender_name": sender_name,
            "subject": subject,
            "to": to_field,
            "cc": cc_field,
            "has_attachments": has_attachments,
            "attachment_names": attachments,
            "received_time": received_time,
            "importance": importance,
        }
        
        # Add response draft to source if present
        if triage_result.get("response_draft"):
            source_data["response_draft"] = triage_result["response_draft"]
        
        return cls(
            id=task_id(),
            title=f"Email: {subject}",
            description=triage_result.get("description", ""),
            classification=triage_result["classification"],
            priority=triage_result["priority"],
            created=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            type="email_reply",
            project="",
            due=triage_result.get("due_date"),
            preview=preview,
            source=source_data,
            summary=triage_result.get("summary"),
            action_required=triage_result.get("action_required"),
            requires_reply=triage_result.get("requires_reply"),
            time_estimate=triage_result.get("time_estimate"),
            response_draft=triage_result.get("response_draft"),
        )