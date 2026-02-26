---
name: workers
title: Worker Registry
type: index
category: framework
description: |
    Configurable worker types, capabilities, selection rules, and operational
    thresholds for the swarm-supervisor skill. Modify this file to customize
    worker dispatch behavior without changing the core skill prompt.
permalink: workers
tags: [framework, routing, workers, swarm, index]
---

> **Deployment-specific configuration** - Customize for your environment.
> Core dispatch protocol is in `skills/swarm-supervisor/SKILL.md`; this file
> contains only the configurable parameters.

# Worker Registry

Configuration for worker dispatch in the swarm-supervisor lifecycle.

## Worker Types

Available worker types and their profiles. Add or modify workers here to change
what the supervisor can dispatch to.

| Worker           | Capabilities                              | Cost | Local | Max Concurrent | Best For                     |
| ---------------- | ----------------------------------------- | ---- | ----- | -------------- | ---------------------------- |
| `polecat-claude` | code, docs, refactor, test, debug         | 3    | yes   | 2              | Most tasks                   |
| `polecat-gemini` | code, docs, analysis, bulk-ops            | 1    | yes   | 2              | Most tasks, cheaper          |
| `jules`          | deep-code, architecture, complex-refactor | 0    | no    | 7+             | Fire-and-forget, complex     |
| `github-agent`   | code, docs, refactor, test, bulk-ops      | 0    | no    | 3              | Free compute, standard tasks |

**Cost Scale**: 0-5, where 0 = free (vendor-hosted), 5 = highest token/API expense.
**Local**: Whether the worker consumes local machine resources.

## Capability Definitions

Capabilities that can be assigned to workers. Used for task-to-worker matching.

| Capability         | Description                                     |
| ------------------ | ----------------------------------------------- |
| `code`             | Standard implementation work                    |
| `docs`             | Documentation, comments, README updates         |
| `refactor`         | Code restructuring without behavior change      |
| `test`             | Test writing and updates                        |
| `debug`            | Bug investigation and fixes                     |
| `analysis`         | Code review, spike investigations               |
| `bulk-ops`         | Repetitive changes across many files            |
| `deep-code`        | Complex algorithms, performance-critical code   |
| `architecture`     | System design changes, API contracts            |
| `complex-refactor` | Multi-file refactors with behavior preservation |

## Selection Rules

### Tag-Based Routing

Tags that route tasks to specific worker types.

#### High-Stakes Tags → Claude

Tasks with these tags require Claude's judgment capabilities:

```
security, api, database, auth, payment
```

#### Bulk Tags → Gemini or GitHub Agent

Tasks with these tags are suitable for bulk execution:

```
formatting, lint-fix, dependency-bump, rename
```

### Complexity Routing

| Complexity Value      | Routed To          | Rationale                         |
| --------------------- | ------------------ | --------------------------------- |
| `needs-decomposition` | jules              | Requires architectural thinking   |
| `requires-judgment`   | claude             | Needs nuanced decision-making     |
| `multi-step`          | claude             | Complex coordination              |
| `mechanical`          | gemini / gh-agent  | Straightforward execution         |
| (unset)               | claude             | Safe default                      |

### Heuristic Thresholds

| Condition           | Worker | Rationale                   |
| ------------------- | ------ | --------------------------- |
| files_affected > 10 | gemini | Bulk operations             |
| effort > 2h         | claude | Complex work needs judgment |

## Domain Specialists

Registry of domain-specific reviewer agents. When task tags match these domains,
the supervisor may invoke the specialist for advisory review.

| Domain   | Specialist Agent              | Mandatory |
| -------- | ----------------------------- | --------- |
| security | `aops-core:security-reviewer` | No        |
| database | `aops-core:db-reviewer`       | No        |
| api      | `aops-core:api-reviewer`      | No        |
| frontend | `aops-core:ui-reviewer`       | No        |

**Note**: Domain specialists are advisory only. Their input informs but does not
block; final synthesis is done by the supervisor alongside mandatory reviewers
(Custodiet).

## Operational Thresholds

### Stale Task Cleanup

Workers that crash leave tasks in `in_progress`. Periodic cleanup resets them:

```bash
polecat reset-stalled --hours 4   # reset tasks stuck >4h
```

Run via `stale-check` cron hook. No active monitoring needed — stale tasks
get picked up on the next dispatch cycle.

### Exit Code Semantics

Standard exit codes from `polecat run` (informational — supervisor doesn't
need to act on these; workers handle their own lifecycle):

| Exit Code | Meaning       | What happens                          |
| --------- | ------------- | ------------------------------------- |
| 0         | Success       | Worker pushes branch, creates PR      |
| 1         | Task failure  | Task stays in_progress, stale-check resets |
| 2         | Setup failure | Task stays in_progress, stale-check resets |
| 3         | Queue empty   | Normal - worker exits cleanly         |

## Swarm Sizing Defaults

Recommended swarm composition based on queue characteristics. Prefer
cloud-hosted workers (Jules, GitHub agents) to minimize local resource use
and supervision. Local polecats for tasks needing framework context.

| Ready Tasks | Task Mix       | Recommended Dispatch                                       |
| ----------- | -------------- | ---------------------------------------------------------- |
| 1-3         | Any            | `polecat run` or 1-2 Jules sessions                        |
| 4-8         | Mostly simple  | 2-3 GitHub agents + 1-2 Jules for complex                  |
| 4-8         | Mostly complex | 3-4 Jules + `-c 1 -g 1` for framework-dependent tasks     |
| 8+          | Mixed          | 5 Jules + 3 GitHub agents + `-c 2 -g 2` if needed         |

**Graduated rollout**: Launch first wave (3-4 workers max), wait for first
PRs to land before scaling up. Catches systemic issues early.

## Capacity Limits

Hard limits on concurrent workers.

| Worker Type    | Max Concurrent | Reason                                         |
| -------------- | -------------- | ---------------------------------------------- |
| claude         | 2              | API rate limits, cost                          |
| gemini         | 2              | Free tier quota; was 4, reduced after crashes  |
| jules          | 7+             | Async on Google infra, no local limits         |
| github-agent   | 3              | Conservative default; increase once validated  |

**Note on Jules**: Jules sessions run asynchronously on Google infrastructure.
Unlike polecat workers which consume local resources, Jules sessions are
fire-and-forget. The practical limit is how many PRs you want to review at once.

**Note on Gemini**: Free tier quota is easily exhausted. Stagger Gemini worker
launches (`--gemini-stagger 15` flag) to avoid simultaneous quota hits.
See `aops-8f4ef5b5`.

**Note on GitHub Agents**: GitHub Copilot coding agents run on GitHub-hosted
infrastructure at no cost. They work from GitHub Issues — assign the agent to
an issue and it creates a PR. They lack framework context (no `.agent/`
instructions, no task MCP), so tasks need self-contained descriptions in the
issue body. Best for well-specified, bounded tasks. Dispatch via
`gh issue edit <num> --add-assignee @copilot-swe-agent` or assign through
the GitHub UI. PRs arrive from a `copilot/fix-*` branch.

---

## Customization Guide

To customize worker dispatch for your deployment:

1. **Add a new worker type**: Add row to Worker Types table with capabilities
2. **Change routing rules**: Modify tag lists or complexity routing table
3. **Adjust thresholds**: Update stale-check hours
4. **Add domain specialist**: Add row to Domain Specialists table
5. **Scale capacity**: Modify Max Concurrent in Capacity Limits

The swarm-supervisor skill reads this configuration at dispatch time. Changes
take effect on next supervisor invocation without modifying the skill itself.
