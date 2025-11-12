# Workflow 1: Design New Component

**When**: Adding new framework capability (hook, skill, script, command).

**Steps**:

1. **Verify necessity**
   - Search existing components for similar functionality
   - Document why existing components insufficient
   - Confirm alignment with framework philosophy

2. **Design integration test FIRST**
   - Define success criteria
   - Create test that validates component works end-to-end
   - Test must fail before component exists (prove it's testing correctly)

3. **Document in experiment log**
   - Create `data/projects/aops/experiments/YYYY-MM-DD_component-name.md`
   - Include hypothesis, design, expected outcomes
   - Reference relevant axioms and principles

4. **Implement component**
   - Follow single source of truth principles
   - Reference existing documentation, don't duplicate
   - Keep scope minimal and bounded

5. **Run integration test**
   - Test must pass completely
   - No partial success
   - Document actual vs expected behavior

6. **Update authoritative sources**
   - Update README.md if directory structure changes
   - Update relevant documentation to reference new component
   - Verify no documentation conflicts introduced

7. **Commit only if all tests pass**
   - Verify documentation integrity
   - Confirm single source of truth maintained
   - Validate no bloat introduced
