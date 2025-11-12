# Workflow 2: Debug Framework Issue

**When**: Framework component failing, unexpected behavior, integration broken.

**Steps**:

1. **Reproduce the issue**
   - Create minimal reproduction case
   - Document exact steps to trigger issue
   - Verify issue exists (not user error)

2. **Check documentation consistency**
   - Verify all references resolve correctly
   - Check for conflicting instructions
   - Validate documentation matches actual behavior

3. **Identify root cause**
   - Check against AXIOMS.md principles
   - Verify component follows single source of truth
   - Look for duplication or conflicts

4. **Design fix**
   - Minimal change to address root cause
   - Avoid workarounds
   - Maintain documentation integrity

5. **Create/update integration test**
   - Test must fail with current broken state
   - Test must pass with fix applied
   - Cover regression cases

6. **Apply fix and validate**
   - Run all integration tests
   - Verify no new conflicts introduced
   - Confirm documentation consistency

7. **Log in experiment if significant**
   - Document issue, root cause, fix
   - Note lessons learned
   - Update tests to prevent recurrence
