---
description: "Worker: write a technical specification for a non-trivial feature or change -- problem, users, scope, design, interfaces and acceptance."
id: wf-spec
tags:
  - wf-template
  - spec
title: Technical specification
type: template
---

## What this step does

Writes the specification a build will follow, grounded in the existing code and decisions.

## Procedure

1. State the problem and who it is for, in human user stories (a researcher, operator, reader), never an agent's.
2. Say what is in scope and what is not.
3. Describe the design: components, data flow, dependencies, error handling. Check the repository's existing decision records first, and add one only for a real architectural fork.
4. Define the interfaces precisely enough to build against.
5. Write acceptance criteria a reviewer can check.

## Output contract

The specification, placed where the composed workflow and task specify.

## When to include

A non-trivial feature, architectural change or integration where building without a written design invites drift.
