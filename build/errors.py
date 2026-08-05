"""The one exception type every build failure raises. Fail loudly, no silent skips."""


class BuildError(Exception):
    """A hard build failure: missing plugin, missing manifest, unresolved
    unknown client, or a malformed plugin.toml / marketplace.toml."""
