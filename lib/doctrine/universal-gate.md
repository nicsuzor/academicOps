Framework source and the framework's issue tracker are writable only from inside
the framework's own source tree. Test it: the tree has both `lib/axioms/` and
`build/marketplace.toml`. If either is missing, you are in a consuming project and
those two destinations are closed to you.

**When gated out, degrade — never drop, and never redirect to a surface you have
no standing to write.** Record the lesson as a tracked improvement task tagged
`framework-gap`, carrying the diagnosis, the evidence, and the destination it was
headed for. Raise it as an issue on the framework repository only when the user
asks. A lesson written to the wrong destination because the right one was closed
is worse than one parked where someone can find it.
