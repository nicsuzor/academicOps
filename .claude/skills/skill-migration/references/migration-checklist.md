# Skill Migration Checklist

Use this checklist to ensure complete and thorough skill migration. Each migration should follow all steps.

## Pre-Migration Planning

- [ ] User request clearly understood
- [ ] Target workflow/task identified
- [ ] Source files identified (agents/*.md, docs/*.md, etc.)
- [ ] Success criteria defined
- [ ] Scope is atomic (ONE primary capability)

## Analysis Phase

- [ ] All source files read using Read tool
- [ ] Workflow sections identified
- [ ] Dependencies noted (tools, files, other workflows)
- [ ] Repository-specific content flagged
- [ ] Code examples and templates extracted
- [ ] Optional: Run extract_workflow.py for automated analysis

## Design Phase

- [ ] Skill scope defined (atomic, single responsibility)
- [ ] Skill structure chosen (workflow/task/reference/capabilities)
- [ ] Resources planned (scripts/references/assets)
- [ ] Generalization strategy defined
- [ ] Skill name chosen (hyphen-case, descriptive)
- [ ] Optional: Run generalize_content.py for automated suggestions

## Creation Phase

- [ ] Skill initialized with init_skill.py
- [ ] SKILL.md written with:
  - [ ] Complete YAML frontmatter (name, description)
  - [ ] Clear overview
  - [ ] Imperative/infinitive form throughout
  - [ ] Workflow or task sections with specific instructions
  - [ ] Concrete examples from source files
  - [ ] References to bundled resources
- [ ] Scripts created (if needed)
  - [ ] Executable permissions set
  - [ ] Documented with usage examples
  - [ ] Tested independently
- [ ] References created (if needed)
  - [ ] Detailed documentation written
  - [ ] Organized logically
  - [ ] Referenced from SKILL.md
- [ ] Assets added (if needed)
  - [ ] Templates copied
  - [ ] Boilerplate code included
  - [ ] Examples provided
- [ ] Example files removed (scripts/example.py, etc.)
- [ ] Repository-specific content generalized

## Cleanup Phase

**CRITICAL - Don't skip this step**

- [ ] Content to remove identified in each source file
- [ ] Backups created for all source files to be modified
- [ ] Content removed from source files using Edit tool
- [ ] Skill references added to source files
- [ ] Agent frontmatter updated (if needed)
  - [ ] Tools list adjusted
  - [ ] Description updated
- [ ] Optional: Run cleanup_sources.py for automated suggestions
- [ ] Verified no duplication:
  - [ ] Grepped for key phrases from skill in sources
  - [ ] Confirmed skill is authoritative source
  - [ ] Checked cross-references

## Validation Phase

- [ ] Skill tested manually in test scenario
- [ ] Verified skill works without repo-specific knowledge
- [ ] Tested in multiple contexts (if possible)
- [ ] Bundled resources load correctly
- [ ] quick_validate.py passes (if available)
- [ ] package_skill.py succeeds
- [ ] Modified source files re-read and verified clean

## Documentation Phase

- [ ] Migration summary created
- [ ] Source files modified listed
- [ ] Content sections removed documented
- [ ] Generalization strategy explained
- [ ] Dependencies/prerequisites noted
- [ ] Agent instructions updated (if needed)
- [ ] Report provided to user with:
  - [ ] Skill location
  - [ ] Package file location (if packaged)
  - [ ] Source files cleaned
  - [ ] Next steps

## Post-Migration Verification

- [ ] Skill can be invoked successfully
- [ ] Source files reference skill correctly
- [ ] No duplicate instructions remain
- [ ] Skill is portable (no hardcoded paths)
- [ ] Skill is atomic (single clear purpose)
- [ ] Skill is reusable (can compose with others)

## Common Mistakes to Avoid

- [ ] NOT creating repository-specific skills (hardcoded paths)
- [ ] NOT creating mega-skills (multiple responsibilities)
- [ ] NOT leaving duplicate content (violates DRY)
- [ ] NOT skipping generalization (copy-paste from sources)
- [ ] NOT forgetting cleanup (content stays in both places)
- [ ] NOT using second-person in SKILL.md ("you should")
- [ ] NOT testing skill before claiming completion

## Success Metrics

A successful migration achieves ALL of these:

1. **Portable**: Skill works in any repository without modification
2. **Atomic**: Skill has ONE clear, focused purpose
3. **Clean**: Source files are leaner, no content duplication
4. **Authoritative**: Skill is THE source for its workflow
5. **Complete**: All use cases from original content work
6. **Structured**: Follows skill-creator best practices
7. **Validated**: Passes validation, tested in practice

## Notes

- Each checkbox represents a decision point or action item
- Not all items apply to every migration (e.g., not all skills need scripts)
- When in doubt, over-communicate with user about scope and decisions
- Fail-fast: If something is unclear or blocked, stop and ask
- Document everything: Future you (or another AI) has no memory of this session
