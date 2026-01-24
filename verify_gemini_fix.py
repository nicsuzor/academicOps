
import os
import sys
import hashlib
import tempfile
from pathlib import Path

# Mock dependencies
os.environ["GEMINI_CLI"] = "1"
# Ensure TMPDIR is NOT set to confuse the logic (force it to fallback to hash)
if "TMPDIR" in os.environ:
    del os.environ["TMPDIR"]

# Set AOPS to current directory
cwd = Path.cwd()
os.environ["AOPS"] = str(cwd)

print(f"Testing with AOPS={cwd}")

# Calculate expected hash
abs_root = str(cwd.resolve())
project_hash = hashlib.sha256(abs_root.encode()).hexdigest()
expected_path = Path.home() / ".gemini" / "tmp" / project_hash

print(f"Expected path: {expected_path}")

# Import the hook logic (add to path)
sys.path.insert(0, str(cwd / "aops-core"))
sys.path.insert(0, str(cwd / "aops-core" / "hooks"))  # Add hooks dir explicitly
try:
    from hooks.user_prompt_submit import get_hydration_temp_dir
except ImportError as e:
    print(f"Error importing hook: {e}")
    sys.exit(1)

# Run the function
actual_path = get_hydration_temp_dir()
print(f"Actual path:   {actual_path}")

# Assert
if actual_path == expected_path:
    print("\nSUCCESS: Path matches expected Gemini temp directory.")
    
    # Also verify the directory exists (it should, from my earlier tool calls)
    if actual_path.exists():
        print("SUCCESS: Directory exists.")
        sys.exit(0)
    else:
        print("WARNING: Directory does not exist (but path calculation is correct).")
        # Attempt to create it to verify we can
        try:
            actual_path.mkdir(parents=True, exist_ok=True)
            print("SUCCESS: Directory created.")
            sys.exit(0)
        except Exception as e:
            print(f"FAILURE: Could not create directory: {e}")
            sys.exit(1)
else:
    print(f"\nFAILURE: Path mismatch.\nExpected: {expected_path}\nGot:      {actual_path}")
    sys.exit(1)
