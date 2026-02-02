# /relax Command Skill

Disable hard-blocking stop hook for this session.

## Purpose

In interactive sessions where the user is actively engaged, the stop hook's hard-blocking can be disruptive. This skill sets the session to "relaxed mode" where:
- Stop hook warnings are still shown
- But session end is not blocked

## Usage

```
/relax
```

## Execution

Run this Python snippet to set the relaxed flag:

```bash
cd /home/nic/src/academicOps && PYTHONPATH=aops-core python -c "
from lib.session_state import set_stop_hook_relaxed
import os
session_id = os.environ['CLAUDE_SESSION_ID']
set_stop_hook_relaxed(session_id)
print('Stop hook relaxed for this session. Will warn but not block.')
"
```

After running, confirm to user:

```
Stop hook set to warn-only mode for this session.
```

## To Restore Hard-Blocking

If user wants to re-enable hard-blocking:

```bash
cd /home/nic/src/academicOps && PYTHONPATH=aops-core python -c "
from lib.session_state import clear_stop_hook_relaxed
import os
session_id = os.environ['CLAUDE_SESSION_ID']
clear_stop_hook_relaxed(session_id)
print('Stop hook restored to hard-blocking mode.')
"
```
