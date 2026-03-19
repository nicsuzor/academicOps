# Workflow Config: spec-audit

## Queue Source

Scan `specs/*.md`. One queue item per spec file.

## Worker Instructions

For the spec at `{source}`:

1. **Research**: Read the spec file (`{source}`) and search the codebase for all related skills, instructions, workflows, code, and tests to understand the current implementation.
2. **Vision Check**: Read `VISION.md` for alignment reference.
3. **Update Spec**: Update the "User Expectations" section (and any other relevant parts) of the spec to be:
   - **Accurate**: Reflect the current implementation.
   - **Aligned**: Consistent with VISION themes and language.
   - **Testable**: Provide clear pass/fail criteria that a QA agent or human can verify.
4. **Finalize**: Commit your changes and update the task status to `done`.

## Evaluation Criteria

- [ ] User expectations section exists and is non-empty.
- [ ] Each expectation is testable (clear pass/fail criteria).
- [ ] No aspirational claims about unimplemented features.
- [ ] Language and themes are aligned with `VISION.md`.
- [ ] Doesn't break existing spec structure or frontmatter.
