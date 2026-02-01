#!/usr/bin/env python3
"""
Wrapper for the Universal Hook Router.
Redirects to the main router at aops-core/hooks/router.py.
"""
import sys
from pathlib import Path

# Get the path to the main router
HOOK_DIR = Path(__file__).parent.parent
ROUTER_PATH = HOOK_DIR / "router.py"

# Add aops-core to path
AOPS_CORE_DIR = HOOK_DIR.parent
if str(AOPS_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE_DIR))

# Import main (since we added to sys.path, we can import from hooks)
try:
    from hooks.router import main
    if __name__ == "__main__":
        main()
except ImportError as e:
    print(f"CRITICAL: Failed to import main router: {e}", file=sys.stderr)
    sys.exit(1)