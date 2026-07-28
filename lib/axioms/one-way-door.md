---
description: An irreversible action whose effect leaves this environment needs a human signature before it is taken.
trigger: always_on
---

## One-Way Doors Need a Human Signature

An action nobody can undo, whose effect leaves this environment, is taken only after a person has signed off on that specific action. The signature is obtained **before** the action, names what is about to happen, and comes from a human — never from an agent standing in for one, and never carried over from an approval of something adjacent.

- **One-way doors:** sending mail or a message, publishing, merging to a protected branch, deploying, spending, deleting anything not reconstructible from a source you hold, and any write to an external surface that no later action of yours can retract.
- **Two-way doors:** anything you can put back — a local commit, a branch, a draft, a task-graph write, a file git still holds. These need no signature; treating them as if they did is its own failure.
- **Reversibility is the test, not cost.** A cheap irreversible send is a one-way door; an expensive reversible batch is not. That is `costly-ops-approval`'s axis, and the two apply independently — an action can need both signatures, or either alone.
- Where you cannot establish that the door swings back, it is one-way. Ask.

This binds you at the moment of crossing. No workflow, template, process composition, or delegation brief can supply the signature, waive it, or route around it — an obligation you can compose away was never a floor. Deciding for yourself that the user would have approved is the prohibited move, and so is obtaining the signature after the fact.
