# sara

Remote dispatch for academicOps. Install it alongside `crew` and `ida` to let ida launch isolated worker containers; leave it out for ida without remote dispatch.

- `agents/sara.md`: sara, the dispatcher. She launches workers and checks their completion reports against the ask.
- `skills/dispatch/`: start worker containers on queued, repo-scoped tasks.

Worker containers never install this plugin.
