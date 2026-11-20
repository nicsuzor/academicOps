---
id: glossary
title: Framework Glossary
type: state
---

# Framework Glossary

Terms defined in this glossary carry strict technical meanings across specifications, agent definitions, skills, workflow templates, and handback reports, and must never be used loosely or metaphorically.

## Terms

### gate

**Definition**: A boundary control or channel guard between two execution contexts, roles, sessions, or trust domains where a check inspects traffic and holds, blocks, or refuses passage until an explicit condition is met.

**Boundary and directionality**: A gate works both ways across a boundary: when a messenger crosses a gate, a guard can be positioned to stop passage going out (outbound / egress), coming in (inbound / ingress), or both. Therefore, an incoming message or subagent handback is never "ungated" merely because the sending subagent lacks an outbound guard -- the receiving agent's inbound gate (such as the hearsay and premise-check gate on arrived reports) guards arrival and holds the boundary.

**Prohibited loose usage**: Never use `gate`, `gated`, or `gating` loosely or metaphorically for ordinary workflow stages, review rubrics, quality standards, checklists, task acceptance criteria, or human decision steps that do not guard passage across a boundary or channel.

**Permitted alternatives**: `checkpoint`, `review lens`, `evaluation stage`, `stopping rule`, `decision boundary`, `requirement`, `check`, `criterion`.
