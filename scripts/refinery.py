#!/usr/bin/env python3
import sys
from pathlib import Path

# Add project root to path
SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT))

# Also add aops-core to path for engineer.py dependencies
sys.path.insert(0, str(REPO_ROOT / "aops-core"))

try:
    from polecat.engineer import Engineer

    print("🚀 Starting Refinery Scan...")
    eng = Engineer()
    eng.scan_and_merge()
    print("✅ Refinery Scan Complete.")
except Exception as e:
    print(f"❌ Refinery Error: {e}", file=sys.stderr)
    import traceback

    traceback.print_exc()
    sys.exit(1)
