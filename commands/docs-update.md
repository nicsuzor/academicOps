Invoke the `docs-update` skill to update and verify framework documentation.

This will:
1. Scan repository structure
2. Compare actual files vs documented structure
3. Validate ALL cross-references (wikilinks, markdown links, agent refs)
4. Detect documentation conflicts
5. Update README.md file tree with annotations
6. Report any broken references or aspirational documentation

**Fail-fast**: Halts immediately if broken references found.
