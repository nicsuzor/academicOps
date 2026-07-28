## A hook the session relies on is degraded

Part of the academicOps hook framework did not do its job on this call:

{faults}

The framework fails open, so nothing was blocked, nothing was retried, and the
call you made proceeded untouched. What is missing is the check, not the call.

Two things follow. Do not try to repair the hook from inside the task — it is
not the work you were asked to do, and a hook is not fixable from the session it
runs in. And say so: the next time you address the person whose session this is,
tell them in one line what stopped working and what it means for what you are
about to hand them. If a rule check is what failed, you are now the only thing
checking it, so check it yourself before you claim the work is done.
