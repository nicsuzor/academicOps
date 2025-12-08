#!/usr/bin/env python3
"""
Stop hook: Verify conclusive statements have evidential basis.

Uses Claude Haiku to scan conversation for confident claims about runtime
behavior and check whether actual state (not just defaults/capabilities)
was verified before making the claim.

Exit codes:
    0: Always (non-blocking)
"""

# CRITICAL: Stop hooks must NEVER crash - wrap everything in try/except
try:
    import json
    import os
    import sys
    from pathlib import Path
    from typing import Any

    import anthropic

    VERIFICATION_PROMPT = """Review this conversation for verification discipline.

TASK: Identify any CONCLUSIVE STATEMENTS about runtime behavior and check if they have sufficient evidential basis.

CONCLUSIVE STATEMENTS are confident claims about CURRENT state/behavior:
- "Confirmed: X"
- "Your system does/will Y"
- "This is configured to Z"
- "Records ARE shuffled" (not "can be" or "by default")
- "The config/setting is X"
- Any definitive statement about what IS happening (not what CAN happen)

For each conclusive statement found:
1. What was claimed?
2. What evidence was provided BEFORE the claim?
3. Did evidence show ACTUAL state (config file content, runtime output) or just DEFAULT/CAPABILITY (source code, documentation)?

CRITICAL DISTINCTION:
- Checking source code for default value = INSUFFICIENT (shows capability, not state)
- Checking actual config file being used = SUFFICIENT (shows actual state)
- Checking if feature exists in codebase = INSUFFICIENT
- Checking if feature is enabled in user's config = SUFFICIENT
- Reading documentation about how something works = INSUFFICIENT
- Reading the actual file/output that controls behavior = SUFFICIENT

Output ONLY valid JSON (no markdown, no explanation):
{
  "conclusions_found": [
    {
      "statement": "exact quote or close paraphrase",
      "evidence_type": "actual_state | default_only | capability_only | documentation_only | none",
      "evidence_description": "brief description of what was checked before the claim",
      "verdict": "grounded | ungrounded"
    }
  ],
  "overall_verdict": "pass | warn",
  "warning_message": "If warn, a clear message explaining what conclusions lack basis. null if pass."
}

If no conclusive statements found, return:
{"conclusions_found": [], "overall_verdict": "pass", "warning_message": null}
"""

    def extract_conversation(input_data: dict[str, Any]) -> str:
        """Extract conversation text from hook input."""
        # Stop hook receives transcript_path
        transcript_path = input_data.get("transcript_path")
        if transcript_path:
            path = Path(transcript_path)
            if path.exists():
                content = path.read_text()
                # Truncate if too long (keep last 50k chars - most recent context)
                if len(content) > 50000:
                    content = content[-50000:]
                return content
        return ""

    def verify_conclusions(transcript: str) -> dict[str, Any]:
        """Use Haiku to verify conclusions have evidential basis."""
        client = anthropic.Anthropic()

        response = client.messages.create(
            model="claude-haiku-4-5-20241022",
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": f"{VERIFICATION_PROMPT}\n\nConversation:\n{transcript}",
                }
            ],
        )

        # Parse JSON response
        try:
            text = response.content[0].text.strip()
            # Handle potential markdown code blocks
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            return json.loads(text)
        except (json.JSONDecodeError, IndexError, KeyError):
            return {"overall_verdict": "pass", "conclusions_found": [], "warning_message": None}

    def format_warning(result: dict[str, Any]) -> str:
        """Format a user-friendly warning message."""
        ungrounded = [c for c in result.get("conclusions_found", []) if c.get("verdict") == "ungrounded"]
        if not ungrounded:
            return ""

        lines = ["⚠️ VERIFICATION WARNING", "", "The following conclusions may lack sufficient evidential basis:", ""]

        for i, conclusion in enumerate(ungrounded, 1):
            lines.append(f"{i}. \"{conclusion.get('statement', 'unknown')}\"")
            lines.append(f"   - Evidence type: {conclusion.get('evidence_type', 'unknown')}")
            lines.append(f"   - What was checked: {conclusion.get('evidence_description', 'unknown')}")
            lines.append("")

        lines.append("Before acting on these conclusions, verify actual runtime state.")
        return "\n".join(lines)

    def main() -> None:
        """Main hook entry point."""
        input_data: dict[str, Any] = {}
        try:
            input_data = json.load(sys.stdin)
        except Exception:
            pass

        # Extract conversation
        transcript = extract_conversation(input_data)
        if not transcript:
            print(json.dumps({}))
            sys.exit(0)

        # Verify conclusions
        try:
            result = verify_conclusions(transcript)
        except Exception as e:
            # API error - don't block, just skip
            print(json.dumps({}))
            print(f"Warning: Verification failed: {e}", file=sys.stderr)
            sys.exit(0)

        # Output warning if needed
        if result.get("overall_verdict") == "warn":
            warning = result.get("warning_message") or format_warning(result)
            if warning:
                output = {"hookSpecificOutput": {"additionalContext": warning}}
                print(json.dumps(output))
                print(f"Verification warning issued", file=sys.stderr)
            else:
                print(json.dumps({}))
        else:
            print(json.dumps({}))

        sys.exit(0)

    if __name__ == "__main__":
        main()

except Exception as _import_error:
    # Import failed - output empty JSON and exit cleanly
    import sys

    print("{}")
    print(f"Warning: Hook import failed: {_import_error}", file=sys.stderr)
    sys.exit(0)
