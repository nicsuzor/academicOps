# Workflow 5: Review Pull Request

**When**: PR exists and needs review before merge.

**Steps**:

1. **Check roadmap alignment**
   - Are changes on current stage priorities in [[../ROADMAP.md]]?
   - Is there evidence/justification for infrastructure changes?
   - Do experiment logs validate the approach?
   - **HALT if changes aren't on roadmap without clear justification**

2. **Checkout to worktree**
   ```bash
   git fetch origin {branch}
   git worktree add ../writing-pr{N} origin/{branch}
   cd ../writing-pr{N}
   git checkout -b review-fixes
   ```

3. **Review against AXIOMS**
   - Single source of truth maintained?
   - Documentation conflicts introduced?
   - Fail-fast principles followed?
   - Integration tests exist and pass?
   - File creation justified and tested?

4. **Review external feedback**
   - Get PR review comments (both general and line-specific)
   - Evaluate suggestions against framework principles
   - Apply suggestions that align with [[../../../AXIOMS.md]]
   - Question/reject suggestions that violate principles
   - Document reasoning for rejections

5. **Address needed changes**
   - Fix in review-fixes branch
   - Run integration tests
   - Commit fixes with clear rationale
   - Push and update original PR branch

6. **Critical evaluation**
   - Does PR follow the principles it introduces?
   - Are infrastructure changes premature?
   - Should changes be split into separate PRs?
   - Is evidence supporting the changes?

7. **Decision**
   - **Merge**: All tests pass, roadmap-aligned, evidence-supported
   - **Request changes**: Issues found, need fixes before merge
   - **Reject/revert parts**: Premature changes without justification
   - **Close**: Fundamentally misaligned with framework

8. **Cleanup**
   ```bash
   cd {original-repo}
   git worktree remove ../writing-pr{N}
   ```

**Critical rule**: PRs that introduce rigorous processes must demonstrate those processes. Never merge a PR that violates the principles it establishes.
