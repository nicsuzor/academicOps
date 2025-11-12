# Workflow 3: Experiment Design

**When**: Testing new framework approach, optimization, or capability.

**Requirements**: Experiments must be well-designed, discrete, and evaluable.

**Steps**:

1. **Define hypothesis**
   - Clear statement of expected outcome
   - Measurable success criteria
   - Bounded scope (discrete, not sprawling)

2. **Design experiment**
   - Single variable changed
   - Control and test conditions defined
   - Evaluation method specified upfront

3. **Create experiment log**
   - Location: `data/projects/aops/experiments/YYYY-MM-DD_name.md`
   - Template:
     ```markdown
     # Experiment: [Name]

     **Date**: YYYY-MM-DD **Hypothesis**: [Clear, testable statement] **Success Criteria**: [Measurable outcomes]

     ## Design

     [What will be changed and how]

     ## Control

     [Baseline behavior/configuration]

     ## Implementation

     [Changes made - scripts, hooks, config, or instructions]

     ## Results

     [Actual outcomes with evidence]

     ## Evaluation

     - [ ] Success criteria met
     - [ ] No documentation conflicts introduced
     - [ ] Integration tests pass
     - [ ] Bloat check passed

     ## Decision

     - [ ] Keep (success)
     - [ ] Revert (failure)
     - [ ] Iterate (partial success)

     ## Lessons

     [What we learned]
     ```

4. **Implement experiment**
   - Make minimal required changes
   - Document all modifications
   - Maintain documentation integrity throughout

5. **Evaluate against criteria**
   - Measure actual outcomes
   - Compare to hypothesis
   - Document evidence objectively

6. **Decide and act**
   - Keep if success criteria met AND no conflicts introduced
   - Revert if failed OR conflicts detected
   - Iterate only if clear path to success defined

7. **Clean up**
   - Remove experimental code if reverting
   - Update documentation if keeping
   - Archive experiment log with final decision
