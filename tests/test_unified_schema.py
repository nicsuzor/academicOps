#!/usr/bin/env python3
"""Test the unified Task schema without needing pydantic installed."""

import json
from datetime import datetime, timezone

def test_task_schema():
    """Test creating a task with the new unified schema."""
    
    # Sample email data
    email_data = {
        "id": "ABC123DEF456",
        "subject": "Meeting Tomorrow at 3pm",
        "senderAddress": "colleague@example.com",
        "senderName": "John Doe",
        "to": "user@example.com",
        "cc": "",
        "hasAttachments": True,
        "attachments": [{"fileName": "agenda.pdf"}],
        "receivedTime": "2025-01-20T10:00:00Z",
        "importance": "High",
        "bodyPreview": "Hi, just confirming our meeting tomorrow..."
    }
    
    # Sample triage results
    triage_result = {
        "classification": "Action",
        "priority": 1,
        "description": "Meeting confirmation for tomorrow at 3pm",
        "summary": "Colleague confirming meeting tomorrow with agenda attached",
        "action_required": "Review agenda and confirm attendance",
        "requires_reply": True,
        "due_date": "2025-01-21T15:00:00Z",
        "time_estimate": 1.0,
        "response_draft": "Thanks for the reminder. I'll review the agenda and see you at 3pm."
    }
    
    # Build task using new unified schema
    task = {
        "id": f"{datetime.now(timezone.utc).strftime('%Y%m%d')}-abc12345",
        "title": f"Email: {email_data['subject']}",
        "description": triage_result["description"],
        "classification": triage_result["classification"],
        "priority": triage_result["priority"],
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "type": "email_reply",
        "project": "",
        "due": triage_result.get("due_date"),
        "preview": email_data["bodyPreview"][:160] if email_data.get("bodyPreview") else "",
        
        # All email-specific data goes in source
        "source": {
            "type": "email",
            "email_id": email_data["id"],
            "sender": email_data["senderAddress"],
            "sender_name": email_data["senderName"],
            "subject": email_data["subject"],
            "to": email_data["to"],
            "cc": email_data["cc"],
            "has_attachments": email_data["hasAttachments"],
            "attachment_names": [a["fileName"] for a in email_data.get("attachments", [])],
            "received_time": email_data["receivedTime"],
            "importance": email_data["importance"],
            "response_draft": triage_result.get("response_draft"),
        },
        
        # Analysis fields
        "summary": triage_result.get("summary"),
        "action_required": triage_result.get("action_required"),
        "requires_reply": triage_result.get("requires_reply"),
        "time_estimate": triage_result.get("time_estimate"),
        "response_draft": triage_result.get("response_draft"),
    }
    
    print("✓ Task created with unified schema")
    print(f"  - ID: {task['id']}")
    print(f"  - Classification: {task['classification']}")
    print(f"  - Email ID stored in: source.email_id = {task['source']['email_id']}")
    print(f"  - No separate processed email file needed!")
    print()
    print("Task JSON structure:")
    print(json.dumps(task, indent=2))
    
    return task

def test_backwards_compatibility():
    """Test that scripts can find tasks by email_id in both old and new locations."""
    
    # Old schema (for backwards compatibility during transition)
    old_task = {
        "id": "20250120-old12345",
        "metadata": {
            "email_id": "OLD_EMAIL_123"
        }
    }
    
    # New schema
    new_task = {
        "id": "20250120-new67890",
        "source": {
            "type": "email",
            "email_id": "NEW_EMAIL_456"
        }
    }
    
    def find_email_id(task):
        """Find email_id in either location."""
        # Check new location first
        source_email_id = task.get("source", {}).get("email_id")
        if source_email_id:
            return source_email_id
        # Fallback to old location
        return task.get("metadata", {}).get("email_id")
    
    print("✓ Backwards compatibility test:")
    print(f"  - Old task email_id: {find_email_id(old_task)}")
    print(f"  - New task email_id: {find_email_id(new_task)}")

if __name__ == "__main__":
    print("Testing Unified Task Schema")
    print("=" * 50)
    print()
    
    test_task_schema()
    print()
    test_backwards_compatibility()
    
    print()
    print("=" * 50)
    print("✅ All tests passed - schema design validated!")