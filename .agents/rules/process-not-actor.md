---
trigger: always_on
description: State what must happen rather than who does it; avoid hardcoding specific agents or people.
---

## Name the process, not the actor

Instructions, specs, and docs say what must happen, not who does it.

- Do not hardcode a particular agent as the actor for a step. Agents instantiate roles; any capable agent may run the step.
- Never write user stories from an agent's perspective (`As an agent...`, `As a knowledge base custodian...`, `As a worker...`). Agents do not want anything; an agent is given capabilities in order to fulfil human user requirements. Every user story in a specification must have a human person as its subject.
- Describe review as a process -- "escalate for review" -- without specifying whether the reviewer is a person or an agent, or boxing in exactly how review workflows operate.
- Refer to the principal as "the user", never by a personal name.
- Use gender-neutral language and pronouns throughout, including agent definitions.
