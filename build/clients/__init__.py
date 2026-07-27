"""Client adapters. Each module exposes exactly one function, `adapt(build_dir,
ctx)`, and is the ONLY place that client's packaging quirks may live. Adding a
plugin must never require a change here."""
