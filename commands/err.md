---
description: Log agent performance failure to experiment tracking system
permalink: aops/commands/err
---

Pause what you are doing and **IMMEDIATELY** invoke the `aops` skill. The user is reporting that an agent violated coding standards, instructions, or expected behavior. Use the `aops` skill to review the conversation and identify the problem, saving your diagnosis to the nicsuzor/academicOps github issues using the github issues skill.

**CRITICAL - Documentation-Only Mode**: When invoked via this command, the aops skill operates in DOCUMENTATION-ONLY mode. You MUST:

✅ **DO**:

- Analyze and categorize the violation
- Search for and update related GitHub issues
- Report findings to the user

❌ **DO NOT**:

- Fix the user's original request that triggered the failure
- Implement solutions or attempt workarounds
- Investigate beyond initial pattern identification

**Rationale**: This command logs single data points for pattern tracking. Solutions require multiple data points and experiment-driven validation.
