---
title: Decision-request axiom clarification
status: draft
---

# Decision-request axiom clarification

Every request for the user's decision, of any kind, arrives with enough information to make the decision, evidence proportionate to the decision, and a reasoned recommendation. This contract protects user attention and cognitive load across all interaction channels by eliminating bare, ungrounded, or un-evidenced decision requests.

## User stories

### US-1 Grounded decision requests

As the user, I want every decision request from any agent or workflow to arrive with complete decision context, proportionate evidence, and a reasoned recommendation, so that I can make informed decisions efficiently without hunting for missing reviews, test results, or rationale.

- **AC-1.1** Given an agent requesting a decision from the user (pull request approvals, merges, review sign-offs, and design choices included), when the request is presented on any channel (conversation, messaging, daily briefings, or pull request comments), then the request provides enough self-contained information for the user to understand the choice without manual log lookups.
- **AC-1.2** Given an agent requesting a decision from the user, when formulating the request, then the request includes primary evidence proportionate to the risk and consequence of the decision (such as posted review links, test status receipts, or verification summaries).
- **AC-1.3** Given an agent requesting a decision from the user, when formulating the request, then the request provides an explicit, reasoned recommendation stating functional rationale ("Recommend X because Y").

### US-2 Universal scope across all decision types

As a reviewer and system auditor, I want the rule to bind every category of user decision without exception, so that no workflow or interaction mode can bypass decision presentation requirements.

- **AC-2.1** Given any decision type--including pull request reviews, pull request merges, architectural choices, and escalation halts--when an agent interacts with the user, then the same threefold requirement applies unconditionally.
- **AC-2.2** Given a request for user action on an open pull request, when presented in daily notes, summaries, or conversational turns, then the entry includes the verification and review state alongside the recommendation.

## Design

### Contract: the threefold decision standard

Whenever an agent escalates outside its autonomous authority to request a decision from the user, the request must satisfy three cumulative elements:

1. **Enough information**: A clear, self-contained statement of what is being decided, the trade-offs in play, and the consequences of each choice. The choice must be understandable on its face without requiring the user to inspect background runner logs or reconstruct agent scratchpads.
2. **Proportionate evidence**: Verifiable receipts and primary evidence scaled to the risk and consequence of the decision. For pull request approvals and merges, this requires the link to the posted review and test suite status receipts. For design choices, this requires references to governing specifications and empirical probes.
3. **Reasoned recommendation**: A concrete suggestion supported by functional rationale explaining why the recommended option is preferred.

### Presentation invariants

Across all delivery surfaces (interactive conversation, chat, daily briefings, and task handovers):

- **Serialization**: Exactly one decision or question per message or turn; never dump or batch decisions into unprioritized lists.
- **Actionable options**: Provide structured, low-friction choices, always including a "do nothing" or deferral option to prevent false dichotomies.
- **Brevity with progressive disclosure**: Deliver bottom-line context and recommendations concisely on the primary surface, with deep technical receipts, trace payloads, and logs linked or nested under expandable details.

### Rejected choices

- **Mechanical regex or AST linting**: Rejected because evaluating whether natural language or complex multimodal artifacts provide "enough information" or "proportionate evidence" requires semantic understanding that cannot be delegated to deterministic scripts.

## Open questions

None. The behavioural contract, invariants, and scope are fully resolved.
