<academicOps deliverable-verify reminder>
A subagent just stopped. Before you relay its output as fact, check:

- **Substituted primitive?** Did it produce the specific artifact/method you asked for, or quietly fall back to a weaker one (e.g. reading source instead of running it, a different test than the one that failed) and report success on the substitute?
- **Reframed failure?** If it hit a limitation, budget exhaustion, or a failing check, did it say so plainly — or did it bury the failure in positive framing ("the underlying thing works, but...")?
- **Intent vs effect?** Does its verdict key on what it actually observed happen (wire output, rendered result, live behaviour), or on its own reasoning/decision log about what should have happened?

If any of these are unclear from what the subagent returned, verify the deliverable yourself before restating its verdict as fact.
</academicOps deliverable-verify reminder>
