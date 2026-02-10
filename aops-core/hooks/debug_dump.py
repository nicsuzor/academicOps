import json
import os
import sys
from pathlib import Path

def main():
    # Read stdin
    raw_input = {}
    if not sys.stdin.isatty():
        input_data = sys.stdin.read()
        if input_data.strip():
            raw_input = json.loads(input_data)
            
    # Dump to debug file
    debug_file = Path("/home/nic/src/academicOps/hook_debug.jsonl")
    with debug_file.open("a") as f:
        entry = {
            "pid": os.getpid(),
            "ppid": os.getppid(),
            "env": {k: v for k, v in os.environ.items() if "CLAUDE" in k or "GEMINI" in k or "AOPS" in k},
            "input": raw_input
        }
        f.write(json.dumps(entry) + "
")
        
    # Return allow
    print(json.dumps({"hookSpecificOutput": {"permissionDecision": "allow"}}))

if __name__ == "__main__":
    main()
