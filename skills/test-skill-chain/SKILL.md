---
name: test-skill-chain
category: instruction
description: EXPERIMENTAL - Tests whether TodoWrite-based skill chaining works.
allowed-tools: Read,Write,Edit,TodoWrite,Skill
version: 0.1.0
permalink: skills-test-skill-chain
---

# Test Skill Chain

**EXPERIMENTAL**: This skill tests whether skills can trigger other skills via TodoWrite.

## Workflow

**IMMEDIATELY call TodoWrite** with the following items, then work through each one:

```
TodoWrite(todos=[
  {content: "Step 1: Read the flowchart skill for context", status: "pending", activeForm: "Reading flowchart skill"},
  {content: "Step 2: Invoke Skill(skill='flowchart') to load flowchart guidance", status: "pending", activeForm: "Loading flowchart skill"},
  {content: "Step 3: Create /tmp/test-chain-output.md with a simple Mermaid flowchart", status: "pending", activeForm: "Creating test flowchart"},
  {content: "Step 4: Report completion", status: "pending", activeForm: "Reporting"}
])
```

**CRITICAL**: You MUST work through EACH todo item in sequence. When you reach Step 2, you MUST call `Skill(skill="flowchart")` to load that skill's guidance before proceeding.

## Expected Output

After completing all steps, `/tmp/test-chain-output.md` should contain a simple Mermaid flowchart that follows the conventions from the flowchart skill.
