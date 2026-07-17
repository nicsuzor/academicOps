"""Layer A: session-transcript parse/render adapters.

Each source (Claude Code, agy) gets a thin adapter delegating to a
maintained parser where one exists. See specs/ (transcript pipeline,
once written) and PKB task aops_82823c43 for the architecture.
"""
