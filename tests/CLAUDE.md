# Testing Context

When writing tests, follow these methodologies:

@../agents/_CORE.md
@../docs/TESTING.md
@../.claude/skills/test-writing/SKILL.md

## Testing Pyramid

- **Unit tests**: Fast (<1s), test business logic in isolation
- **Integration tests**: Slow (~10-30s), test components working together, use `model="haiku"`
- **No redundant coverage**: Don't test the same behavior at multiple levels

See TESTING.md for complete philosophy and examples.
