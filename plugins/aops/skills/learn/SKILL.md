---
name: learn
description: Turn something that went wrong into a lesson that lands somewhere useful.
---

# Learn

The user is reporting that something went wrong _that is worth fixing systemically_.

- The entire academicOps framework is a risk-mitigation system. Things go wrong all the time when using probabalistic tools in open environments. The point is to understand the types of risks we encounter and ensure that we have a strong strategy for reducing the likelihood of mistakes and mitigating their impacts.
- The mistake itself is the easy part; that's not the point of this skill. The main calling agent will arrange the appropriate remedy for the immediate error.
- Your role is the hard part: thinking through the counterfactual -- what technique _might_ we have used that would have been more likely to prevent the **class** of mistake or to identify and correct it earlier?
- Every mitigation measure comes at significant cost. We use this skill to develop the evidence base required for us to decide when and how to act in a way that is likely to be effective while minimising ths burden.

You are to file a Root Cause Analysis at the _appropriate layer_.

- **Anonymise** your report. No real names, emails, personal details, or raw session dumps in anything you write or transmit.

## 1. Diagnose the root cause of the CLASS of error

First, it is **critical** to distinguish the 'proximate cuase' from the 'root cause':

- Mistakes happen. This incident is _only one example_ of a pattern the user has noticed across sessions.
- We are not looking to attribute blame. The responsibility is _always_ ours at a framework level.
- You must take a longer time-frame into account: what is the earliest point in the transcript that we would have been able to **identify the risk of the broad _class_ of errors**, reduce its likelihood, and put measures in place to catch an **instance of that class of errors** in time to mitigate their impact?

**An enforcement mechanism is something the framework does or says — observable from outside the agent.** A check that fires, an instruction restated at the point it applies, a template that pre-fills the safe shape, a gate that blocks a merge: these are mechanisms. "The agent should have remembered" or "the agent should have noticed" names no mechanism at all — an internal state an agent is presumed to hold is not observable, and a root-cause analysis that terminates there has restated the failure, not explained it.

The same restriction governs how you write the finding, not only how you read for mechanisms:

- **State the cause as what was observed, never as the absence of a remedy you already have in mind.** "No trigger existed" presupposes that a trigger is the fix; a diagnosis that already contains its own answer isn't a diagnosis — it has skipped the step where the answer gets earned.
- **Never guess why the agent behaved as it did.** What it attended to, what competed with what, what it "didn't see" — none of that is observable, and reaching for it means the analysis has left the evidence behind. This is the mechanism rule above applied to causes instead of remedies: if a mechanism can't be an agent noticing itself, a cause can't be an agent failing to notice, either.
- Stated correctly, a root cause looks like: "an instruction presented as one line among roughly fifty at context start was not followed" — a citable fact about position and density in context, nothing more. Any story about what "crowded it out" is an untested hypothesis, not a finding, and stops at the sentence before.

The _root cause_ for our framework might be any combination of:

- an actual bug in tooling or configuration;
- conflicting or unclear instructions;
- a correct, clearly-written instruction that existed but was never restated at the point it needed to apply — distinct from the case above, and in practice the more common one;
- a failure to anticipate the class of errors and/or their impact;
- a failure of our error detection mechanisms;
- a failure of our mitigation _processes_ once an error has been detected.

**Check the base rate before you indict a whole class of instrument.** The incident record is a selected sample — a failure gets written down when an instruction doesn't hold, and nothing gets written when it does. Reasoning from that corpus alone will always conclude "instructions don't work, we need mechanical enforcement"; that's the selection talking, not the evidence. Before concluding that a class of instrument (prose instructions, say) is inadequate, check whether that same class is holding elsewhere in the framework — it usually is, and that bounds what the finding can claim.

Use the `debug` skill to trace the error and identify the root cause.

## 2. Identify the SCOPE of the error

Second, we need to differentiate between errors that are **context-specific** and errors that are **framework-level**.

We ultimately act on three levels:

- The particular project: instructions and project rules and their particular arrangement of enforcement mechanisms;
- The user scope: personalised knowledge and preferences that are unique to the user and should be reflected in our Personal Knowledge Base;
- The framework level: universal axioms, agents, tools, and enforcement processes.

## 3. Record the instance

Record the root cause at the appropriate layer:

- Usually, you should file a GitHub issue associated with the most general layer that could have identified the risk and done something about it.
- Be careful about leaking sensitive information; strip reports of any identifying information and specific tasks, input, or output.
- You should first try to find _other_ instances of this class of error. It is **much** better to add detail and counter-examples to existing known problems than to create a new issue for the specific manifestation of a general class of risks.

## 4. Match the remedy to the failure

You are **strictly forbidden from implementing any fix directly**. We have found that this leads to an unacceptable risk of over-fitting to this specific instance rather than the broader class of problem. Instead, route the finding to the mechanism that fits.

There is no default direction to move in, lighter to heavier or the reverse. The mechanisms available suit different shapes of problem, and choosing between them is a matter of fit, not a rung on a severity ladder:

- **Restraint** — a rule, a gate, a hard block, an explicit prohibition — makes the disfavoured action impossible or forces a stop before it lands. It fits when the impact is irreversible, or serious enough that another instance can't be tolerated while a lighter fix takes hold.
- **Architecture** — defaults, what tools exist, which skills are discoverable, which templates exist — nudges without prohibiting anything, by making the preferred behaviour cheap and the disfavoured one merely inconvenient. It fits most routine, reversible failures, and is usually the cheaper remedy of the two.

Neither is the safer default. Irreversible harm left to sit on advisory prose is a mismatch; routine work pinned under a hard block that only generates friction is exactly as much a mismatch, in the other direction. Don't train toward the lighter end or the heavier one — only toward fit.

**Check `specs/ENFORCEMENT-MAP.md` before proposing anything new.** It is the live, current-state register of every enforcement mechanism in the framework — kind, tone, binding, and state (live / dark / disconnected / unbuilt). The common finding is not that no mechanism exists; it's that a suitable one already does and has been switched off, mis-scoped, or silently broken by a rename. Check the register before you build or harden anything — repairing or turning on what's already there is frequently the whole fix.

Beyond filing the finding, act under three conditions:

- Once we have enough evidence to diagnose a pattern of recurring errors;
- If we identify a clear conflict or mistake in instructions or bug in tooling;
- When the impact of an error is serious enough to warrant immediate preventative or restorative action.

If the evidence is sufficient to act, **do not make the fix yourself**. Instead, create a new task to fix the problem at the appropriate level — pointing at the existing mechanism from the register where one fits, or naming what needs building where none does.

## 5. Output

Return a markdown formatted response that includes:
a. The specific evidence of how the incident came about, with citations;
b. The root cause of the class of error;
c. An estimate of frequency and severity of this class of error;
d. A link to your report (github issue or PKB entry)
e. If you have it, a link to the PKB task to remedy the problem.
