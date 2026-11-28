---
title: Repository change
type: template
alias: [wf-repo-change, wf-doc-base, wf-quick-fix]
description: "Worker: change files in one repository -- code, docs, instructions or config -- run the checks the repository already has, and commit to the working branch."
tags: [base, task, code, docs]
---

## What this step does

Makes a change in one repository and leaves it committed on the working branch (or where the composed workflow and task specify); review, sign-off, approval, or delivery steps run only when the composed workflow includes them.

## Procedure

1. Read the files you change in full, and follow the repository's own conventions and instructions.
2. Make the smallest change that meets the acceptance criteria.
3. Run the checks the repository already uses (its tests, linters, build) on what you changed. Add or update a test only when the repository keeps a test suite and the change is to code that executes; never for docs, instruction text or config, and never in a repository without tests or whose instructions forbid them.
4. Commit to the working branch with a short message saying what changed and why. No private task, session or knowledge-base identifiers in commits.

## Output contract

Commits on the working branch, and a report giving the check results (or that the repository has none) against each acceptance item.

## When to include

Any task whose output is a change to files in a repository.
