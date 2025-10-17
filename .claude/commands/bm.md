---
description: Activate BM development mode
---
Immediately read and adopt the following instruction sets:

* ${ACADEMICOPS_BOT}/agents/DEVELOPER.md
* ${ACADEMICOPS_PERSONAL}/docs/agents/DEVELOPER.md
* docs/agents/DEVELOPER.md


CRITICAL: FOR EVERY TASK, YOU MUST CREATE A CHECKLIST AND FOLLOW EACH STEP:

[] **SLOW DOWN AND THINK**: Understand the full problem scope before proposing solutions.
[] **CHECK AND UPDATE GITHUB ISSUES**: Look for existing related issues, attempted and proposed fixes, and document current state. Do not propose solutions yet!
[] **ANALYZE**: Map the system architecture and identify root causes
[] **PLAN**: Use github issues to track problems and document your plan or proposals with clear validation criteria
[] **FAILING TESTS**: Write a single test in `tests/` directory using pytest conventions that capture expected behavior. **CRITICAL**: NO standalone test scripts anywhere else - violating this rule means starting over.
[] **IMPLEMENT**: Make minimal changes that passes the failing test.
[] **REPEAT and REFACTOR**: TTD IS NOT OPTIONAL. Make ONE change at a time and refactor ONLY when necessary.
[] **COMMIT**
[] **UPDATE GITHUB ISSUES**

---
