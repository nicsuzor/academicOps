#!/usr/bin/env python3
"""
Minimal email management script.
Keeps it simple - let the LLM handle the intelligence.
"""

import json
import os
import subprocess
import sys
import re
from datetime import datetime, UTC
from pathlib import Path

# Configuration
SCRIPTS_DIR = Path(__file__).parent
ROOT = SCRIPTS_DIR.parent.parent
TASKS_INBOX = ROOT / "data" / "tasks" / "inbox"
TASKS_QUEUE = ROOT / "data" / "tasks" / "queue"
TASKS_ARCHIVED = ROOT / "data" / "tasks" / "archived"

def print_json(obj):
    print(json.dumps(obj))

def run_powershell(script_name, *args):
    """Run PowerShell script and return JSON output."""
    cmd = ['powershell.exe', '-ExecutionPolicy', 'Bypass', 
           str(SCRIPTS_DIR / script_name)] + list(args)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        # Debug: Check if output is not JSON (might be help text or error)
        output = result.stdout.strip()
        if output and not output.startswith('{'):
            print(f"Non-JSON output from PowerShell: {output[:200]}", file=sys.stderr)
        return json.loads(output) if output else {}
    except subprocess.CalledProcessError as e:
        print(f"PowerShell error: {e.stderr}", file=sys.stderr)
        return {}
    except json.JSONDecodeError as je:
        print(f"Invalid JSON from PowerShell: {je}", file=sys.stderr)
        print(f"Output was: {result.stdout[:500]}", file=sys.stderr)
        return {}

# Note: Fetching content is handled directly via PowerShell in workflows.


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return None


def _iter_task_files():
    files = []
    for d in [TASKS_INBOX, TASKS_QUEUE, TASKS_ARCHIVED]:
        if d.exists():
            files.extend(sorted(d.glob('*.json')))
    return files


def _find_task_by_id(task_id: str):
    if not task_id:
        return None
    for p in _iter_task_files():
        if p.stem == task_id:
            t = _load_json(p)
            if isinstance(t, dict):
                return (p, t)
    return None


def _find_task_by_email_id(email_id: str):
    if not email_id:
        return None
    for p in _iter_task_files():
        t = _load_json(p)
        if not isinstance(t, dict):
            continue
        # Check new location: source.email_id
        source_email_id = t.get('source', {}).get('email_id')
        # Also check old location for backwards compatibility during transition
        old_email_id = t.get('metadata', {}).get('email_id')
        if (source_email_id and str(source_email_id) == str(email_id)) or \
           (old_email_id and str(old_email_id) == str(email_id)):
            return (p, t)
    return None


def _archive_local_task(task_path: Path, task: dict):
    TASKS_ARCHIVED.mkdir(parents=True, exist_ok=True)
    task['archived_at'] = datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
    dest = TASKS_ARCHIVED / task_path.name
    dest.write_text(json.dumps(task, ensure_ascii=False, indent=2))
    if task_path.exists():
        try:
            task_path.unlink()
        except Exception:
            pass
    return dest

def create_draft(draft_json):
    """Create draft in Outlook."""
    # Write to temp file to avoid command line escaping issues
    temp_file = SCRIPTS_DIR / 'tmp' / 'draft.json'
    temp_file.parent.mkdir(exist_ok=True)
    temp_file.write_text(json.dumps(draft_json, ensure_ascii=False, indent=2))
    
    print(f"Temp file path: {temp_file.resolve()}", file=sys.stderr)

    result = run_powershell('outlook-draft.ps1', '-JsonFile', str(temp_file))
    # Best-effort: update task source with draft info
    try:
        msg_id = draft_json.get('messageId') if isinstance(draft_json, dict) else None
        if result and result.get('success') and msg_id:
            # Find task by email ID
            task_info = _find_task_by_email_id(msg_id)
            if task_info:
                task_path, task_dict = task_info
                task_dict.setdefault('source', {}).setdefault('draft_history', []).append({
                    'created_at': datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'draft_id': result.get('draftId'),
                    'subject': result.get('subject'),
                    'type': result.get('type')
                })
                task_path.write_text(json.dumps(task_dict, ensure_ascii=False, indent=2))
    except Exception:
        pass
    # temp_file.unlink()
    return result


def modify_email(message_id, archive=False, flag_action=None, add_categories=None, remove_categories=None, use_json=False, priority=None, due=None):
    """Modify an existing email (archive, categories, flags).
    
    Args:
        message_id: The Outlook message ID
        archive: Whether to archive the message
        flag_action: Flag action (set/clear/complete)
        add_categories: List of categories to add
        remove_categories: List of categories to remove
        use_json: Force JSON mode (useful for complex/multiline content)
        priority: New priority for the task
        due: New due date for the task
    """
    
    # Check if we have any actions
    has_actions = archive or flag_action or add_categories or remove_categories or priority is not None or due is not None
    if not has_actions:
        print("No actions specified.")
        return {}
    
    # If the provided id is actually a local task id (pattern YYYYMMDD-XXXXXXXX or file exists),
    # do NOT call Outlook. Perform local modifications only.
    task_id_pattern = re.compile(r"^\d{8}-[0-9a-fA-F]{8}$")
    local_task = _find_task_by_id(message_id)
    if local_task or task_id_pattern.match(str(message_id) or ""):
        # Treat as local task
        if not local_task:
            print_json({"success": False, "error": "task_not_found", "message": "No local task with this id"})
            return {}
        task_path, task = local_task
        result = {"success": True, "local": True, "taskId": message_id}
        modified_fields = []

        if priority is not None:
            try:
                task['priority'] = int(priority)
                modified_fields.append("priority")
            except (ValueError, TypeError):
                result.update({"success": False, "error": "invalid_priority", "message": "Priority must be an integer."})
                return result
        
        if due is not None:
            task['due'] = due
            modified_fields.append("due")

        if modified_fields:
            task_path.write_text(json.dumps(task, ensure_ascii=False, indent=2))
            result["modified"] = modified_fields

        if archive:
            dest = _archive_local_task(task_path, task)
            result.update({"archived": True, "taskPath": str(dest.relative_to(ROOT))})
        
        return result

    # Use JSON mode if explicitly requested or if dealing with complex data
    # (For now, simple operations can use direct params)
    if use_json:
        # Original JSON-based approach (preserved for compatibility)
        payload = {
            "messageId": message_id,
            "actions": {}
        }
        if archive:
            payload["actions"]["archive"] = True
        if flag_action:
            payload["actions"]["flag"] = flag_action
        if add_categories:
            payload["actions"]["addCategories"] = add_categories
        if remove_categories:
            payload["actions"]["removeCategories"] = remove_categories

        temp_file = SCRIPTS_DIR / 'tmp' / 'modify.json'
        temp_file.parent.mkdir(exist_ok=True)
        temp_file.write_text(json.dumps(payload))

        try:
            result = run_powershell('outlook-message.ps1', '-JsonFile', str(temp_file))
        finally:
            if temp_file.exists():
                temp_file.unlink()
        return result
    else:
        # Direct parameter mode (simpler for basic operations)
        args = ['-MessageId', message_id]
        
        if archive:
            args.append('-Archive')
        if flag_action:
            args.extend(['-Flag', flag_action])
        if add_categories:
            # PowerShell array parameter - pass as comma-separated string
            # PowerShell will handle splitting when defined as [string[]]
            args.extend(['-AddCategories', ','.join(add_categories)])
        if remove_categories:
            args.extend(['-RemoveCategories', ','.join(remove_categories)])

        # Keep track of corresponding local task to update after success
        related_task = _find_task_by_email_id(message_id)
        result = run_powershell('outlook-message.ps1', *args)
        # Best-effort: record archive action in local task
        try:
            if archive and result and result.get('success'):
                # Archive local task mirror if present
                if related_task:
                    t_path, t_data = related_task
                    # Preserve finalMessageId if changed
                    fm = result.get('finalMessageId') or (result.get('actions') or {}).get('archive', {}).get('newId')
                    if fm:
                        t_data.setdefault('source', {})['final_message_id'] = fm
                    _archive_local_task(t_path, t_data)
        except Exception:
            pass
        return result

# Listing and fetching utilities removed to enforce preferred workflow (work from selected tasks only).


def main():
    if len(sys.argv) < 2:
        print("Usage: task_process.py [draft|modify]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == 'draft':
        # Accept JSON from either stdin or file
        if len(sys.argv) > 2:
            # File path provided as argument
            json_file = sys.argv[2]
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    draft_data = json.load(f)
            except FileNotFoundError:
                print(f"Error: File not found: {json_file}", file=sys.stderr)
                sys.exit(1)
            except json.JSONDecodeError as e:
                print(f"Invalid JSON in file {json_file}: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            # Read from stdin (original behavior)
            raw = sys.stdin.read()
            if not raw.strip():
                print("Error: no JSON provided. Usage:", file=sys.stderr)
                print("  From file: task_process.py draft /path/to/draft.json", file=sys.stderr)
                print("  From stdin: echo '{...}' | task_process.py draft", file=sys.stderr)
                sys.exit(1)
            try:
                draft_data = json.loads(raw)
            except json.JSONDecodeError as e:
                snippet = raw[:200].replace('\n', '\\n')
                print(f"Invalid JSON: {e}. First chars: {snippet}", file=sys.stderr)
                sys.exit(1)
        
        result = create_draft(draft_data)
        print_json(result)

    elif cmd == 'modify':
        if len(sys.argv) < 3:
            print("Usage: task_process.py modify <task_id> [--archive] [--priority 1] [--due YYYY-MM-DD]")
            sys.exit(1)
        task_id = sys.argv[2]
        archive = False
        priority = None
        due = None
        i = 3
        while i < len(sys.argv):
            arg = sys.argv[i]
            if arg == '--archive':
                archive = True
                i += 1
            elif arg == '--priority' and i + 1 < len(sys.argv):
                priority = sys.argv[i+1]
                i += 2
            elif arg == '--due' and i + 1 < len(sys.argv):
                due = sys.argv[i+1]
                i += 2
            else:
                print(f"Unknown or incomplete modify argument: {arg}")
                sys.exit(1)
        result = modify_email(task_id, archive=archive, priority=priority, due=due)
        print_json(result)

    else:
        print(f"Unknown command: {cmd}")
        print("Available commands: draft, modify")
        sys.exit(1)

if __name__ == '__main__':
    main()