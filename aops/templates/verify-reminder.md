<academicOps deliverable-verify reminder>
A subagent just stopped. DO NOT relay its claims directly. Instead, read the output caref and provide a formatted Markdown summary of the output that includes:
  - The original question the agent was asked
  - The agent's conclusion
  - A dot-point list of EACH claim made by the agent and the evidence that supports it.
  - Your evaluation of the completeness and reliability of the agent's answer.

Agents are often lazy and make up claims that are not supported by evidence. Check:

- **Substituted primitive?** Did it produce the specific artifact/method you asked for, or quietly fall back to a weaker one (e.g. reading source instead of running it, a different test than the one that failed) and report success on the substitute?
- **Reframed failure?** If it hit a limitation, budget exhaustion, or a failing check, did it say so plainly — or did it bury the failure in positive framing ("the underlying thing works, but...")?
- **Intent vs effect?** Does its verdict key on what it actually observed happen (wire output, rendered result, live behaviour), or on its own reasoning/decision log about what should have happened?

Be careful that you are not complicit by laundering lazy agent outputs as truth.
</academicOps deliverable-verify reminder>
