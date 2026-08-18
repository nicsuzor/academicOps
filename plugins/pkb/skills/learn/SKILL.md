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

The _root cause_ for our framework might be any combination of:

- an actual bug in tooling or configuration;
- conflicting or unclear instructions;
- a failure to anticipate the class of errors and/or their impact;
- a failure of our error detection mechanisms
- a failure of our mitigation _processes_ once an error has been detected.

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

## 4. Escalate when necessary

You are **strictly forbidden from implementing any fix directly**. We have found that this leads to an unacceptable risk of over-fitting to this specific instance rather than the broader class of problem. Instead, you must escalate as appropriate.

We escalate under three conditions:

- Once we have enough evidence to diagnose a pattern of recurring errors;
- If we identify a clear conflict or mistake in instructions or bug in tooling;
- When the impact of an error is serious enough to warrant immediate preventative or restorative action.

If the evidence is sufficient to act, **do not make the fix yourself**. Instead, create a new task to fix the problem at the appropriate level.

## 5. Output

Return a markdown formatted response that includes:
a. The specific evidence of how the incident came about, with citations;
b. The root cause of the class of error;
c. An estimate of frequency and severity of this class of error;
d. A link to your report (github issue or PKB entry)
e. If you have it, a link to the PKB task to remedy the problem.
