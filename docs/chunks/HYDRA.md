## RULES

- **NO configuration in code** - All config lives in YAML files
- **NO direct environment variable access** - Use `${oc.env:VAR}` in YAML only
- **NO defaults** - Fail fast when config is missing (see Axiom 7)
- **Composable, not monolithic** - Small, focused YAML files that compose
- **Explicit, not implicit** - Always use `_self_`, never rely on defaults

### Key Hydra Concept

**"Last one wins"** - If multiple configs define the same value, the last one in composition order wins.

## Key References

### Configuration with Hydra

When working with configuration files, refer to the comprehensive guide:

📖 **[Hydra Configuration - Complete Guide](@docs/resources/hydra.md)**

This guide covers:
- Core principles (no config in code, fail-fast, composability)
- Testing with Hydra (pytest patterns, fixtures, golden tests)
- Interpolation patterns and environment variables
- Common errors and solutions
- Best practices for academicOps projects

**Use this guide when:**
- Setting up new Hydra configs
- Writing tests that use Hydra
- Debugging composition or override errors
- Working with secrets and environment variables
