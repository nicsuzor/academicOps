
import os
import sys
import json
import tempfile
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "aops-core"))

from lib.session_state import get_or_create_session_state, save_session_state, load_session_state
from lib.session_paths import get_session_status_dir, get_session_file_path

def test_repro():
    with tempfile.TemporaryDirectory() as tmp_dir:
        state_dir = Path(tmp_dir) / "claude-session"
        state_dir.mkdir()
        
        os.environ["AOPS_SESSION_STATE_DIR"] = str(state_dir)
        cwd = "/test/project"
        os.environ["CLAUDE_SESSION_ID"] = cwd
        os.environ["CLAUDE_CWD"] = cwd
        
        session_id = cwd
        
        print(f"DEBUG: AOPS_SESSION_STATE_DIR={state_dir}")
        print(f"DEBUG: Status Dir from lib: {get_session_status_dir(session_id)}")
        
        # 1. Create and Save State
        state = get_or_create_session_state(session_id)
        state["state"]["tool_calls_since_compliance"] = 10
        save_session_state(session_id, state)
        
        saved_path = get_session_file_path(session_id, state["date"])
        print(f"DEBUG: Saved to: {saved_path}")
        if saved_path.exists():
            print("DEBUG: File exists!")
            print(f"DEBUG: Content: {saved_path.read_text()}")
        else:
            print("DEBUG: File DOES NOT exist at expected path!")
            
        # 2. Load State
        loaded_state = load_session_state(session_id)
        if loaded_state:
            print(f"DEBUG: Loaded State Found. Tool calls: {loaded_state.get('state', {}).get('tool_calls_since_compliance')}")
        else:
            print("DEBUG: Load returned None!")
            
            # List directory to see what's there
            print("DEBUG: Directory contents:")
            for p in get_session_status_dir(session_id).iterdir():
                print(f"  - {p.name}")

if __name__ == "__main__":
    test_repro()
