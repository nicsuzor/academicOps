---
description: Load development workflow and coding standards
extra: |
   ## When to Use This Command

   Use `/dev` when:
   - Starting development work in a project
   - Need the structured workflow enforced
   - Want "EXPLORE MANDATORY" reminder (prevent rushing to code)
   - Beginning a coding session
   - Need access to capability guides (Hydra, dbt, Python, data science)

   ## Related Commands

   - `/ttd` - Load test-driven development methodology
   - `/ops` - View all available academicOps commands
   - `/trainer` - Switch to trainer mode for framework improvements

   ## What This Loads

   The `dev` skill provides:

   1. **🚨 CRITICAL 6-Step Development Workflow** (ONE STEP AT A TIME):
      - STOP & ANALYZE (check GitHub issues first)
      - EXPLORE (MANDATORY - search codebase, prevent rushing to code)
      - PLAN (document solution in issue)
      - TEST DRIVEN DEVELOPMENT (run tests first, write failing test, iterate)
      - VALIDATE (full test suite)
      - COMMIT & UPDATE (conventional commits, update issues)

   2. **Capabilities Index** with comprehensive guides:
      - Configuration (Hydra)
      - Data pipelines (dbt)
      - Python best practices
      - Visualization (Matplotlib, Seaborn)
      - Statistical modeling (Statsmodels)
      - Interactive dashboards (Streamlit)

   3. **Project Rules**:
      - Keep projects self-contained (polyrepo, not monorepo)
      - Everything self-documenting
      - Fail-fast (no fallbacks)
      - TDD mandatory
      - Document in GitHub issues

---

Invoke the `supervisor` agent to orchestrate development work through structured TDD workflow with proper delegation to specialized subagents (Explore, Plan, dev).

The supervisor will:
- Take full responsibility for the development task
- Enforce test-driven development discipline
- Delegate exploration and planning to specialized agents
- Tightly control developer subagent through atomic steps
- Ensure quality gates at each stage
- Handle test failures through iteration
- Manage commits via git-commit skill validation
