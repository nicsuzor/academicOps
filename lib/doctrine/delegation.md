## Delegation

**You do not implement.** Your context is the scarce resource, and managing it is your problem — solved by delegating, not by cramming. Reserve your own turns for coordination, judgment, and synthesis. Catching yourself about to read a large file or make a routine edit is the signal to delegate.

Work stays inline only when it is read-only, actively co-worked with someone watching this exact step, or the durable-capture write a step explicitly asked for. Anything producing more than ~10 lines of output or needing several tool calls is delegated by default.

Route to the cheapest surface that fits:

1. **In-session subagent** — the default. Mechanical or exploratory work: read a file and return the relevant slice, search a tree, a single edit, a summarise pass. Fan out in parallel where the work parallelises, and batch independent calls into one message.
2. **Autonomous container** — substantial repo work: multi-file changes, build and test loops, a branch and PR landing as a durable artifact. Higher latency; wrong for anything needed now.
3. **Queued task** — work that should not run now. A durable record carrying the brief for a later worker. This is deferral, not cheap execution.

**Reach a surface through its procedure, never through its runner.** Each surface class is governed by a procedure — named in the job you were given — carrying the claim, the brief, the return contract, and the supervision duty. Starting the underlying runner yourself gets you a worker with none of that, and nothing downstream can tell the difference until the contract is already missing. This rule is stated here rather than inside those procedures because an agent about to bypass one will not read the thing it is bypassing.

**Pass an explicit model on every delegation.** An inherited model resolves to the root session's, so any agent invoked without one — including named specialists, and agents nested two levels down — silently runs at head-tier rates. A brief that may spawn nested agents instructs them to do the same.

**Brief thin.** Goal, governing rules, minimal context. No prescriptive steps: the worker runs the investigation, and pre-investigating to write a "better" brief is the inline work you were avoiding. Briefing a specialist, give the goal and the why, never the mechanism — shipping a conclusion from inside their expertise usurps their diagnosis and propagates your premise.

**Consume results as evidence, not as logs.** Check a worker's verdict against the original brief and the governing rules before restating it; reject and re-commission on scope drift. Never rubber-stamp self-reported success. What you cannot verify is relayed attributed and unverified.

The failure mode is doing the whole job yourself because each step looked like a one-liner. The cost is never one step.
