---
description: "Crew (needs GitHub access): take one open pull request to merged, or to a clearly recorded reason it cannot merge yet, under the repository's merge rules."
tags:
  - wf-template
  - pr
  - lifecycle
title: Move a PR along
type: template
---

## What this step does

Advances one open pull request under the composed workflow and repository rules.

## Obligations

1. **Merge authority**: read the repository's merge rules and the user's standing rulings. A merge no ruling covers needs the user's approval; never merge to a base with an outside audience without it.
2. **Get it ready**: checks green on the latest commit, any review requirements set by the composed workflow and repository rules satisfied, and open feedback answered by a commit or a reasoned reply. Mark a finished draft ready.
3. **Land or hold**: where a ruling or the user's approval covers it, update onto the base, resolve conflicts, re-run checks, and merge. Otherwise leave it open with the blocking reason recorded on the PR and its task.

## Must not

Merge with failing or pending required checks, unresolved change requests, or missing required approval.

## Output contract

The PR merged, or left open with its blocking reason recorded.

## When to include

Moving one pull request toward merge.
