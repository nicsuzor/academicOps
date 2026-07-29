# Plugin Template

This is a base template for creating a new `academicOps` plugin.

## Creating a New Plugin

1. Copy this directory to `plugins/<your-plugin-name>`.
2. Add an entry for your plugin in `build/marketplace.toml`. For example:

```toml
[[plugins]]
directory = "<your-plugin-name>"
name = "aops-<your-plugin-name>"
description = "Description of your plugin functionality."
category = "productivity"
```

## Manifests & Configuration (Optional)

You do **not** need to create any manifest files (like `plugin.json` or `plugin.template.json`) just to build your plugin. The build system will automatically generate a base `plugin.json` using the name, description, and owner information from `marketplace.toml`.

You only need to create a `manifest` directory if your plugin needs to:

- Declare MCP servers (`mcp.template.json`)
- Add lifecycle hooks (`hooks.template.json`)
- Specify custom fields like `userConfig` or `keywords` in `plugin.template.json` (which will be merged with the automatically generated defaults).
- Include shared library files via `plugin.toml`

If you need any of these, simply keep the `manifest` directory and adjust the specific template files you require.

## Included Stubs

This template includes basic examples for common plugin components:

- **`skills/example/SKILL.md`**: An example skill that the agent can read and execute.
- **`commands/example.md`**: An example slash command (`/example`).
- **`axioms/example.md`**: An example axiom (project rule) that the agent must always follow while this plugin is active.
- **`hooks/handlers.py`**: Example handlers loaded by the standard `dispatch.py` hook router, paired with `manifest/hooks.template.json`.
- **`manifest/`**: Example manifest files (`mcp.template.json`, `plugin.template.json`, `plugin.toml`) to demonstrate custom configurations.

Feel free to delete any of these stubs that your new plugin does not need!
