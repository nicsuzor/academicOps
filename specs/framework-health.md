---
title: Framework Health
type: spec
status: implemented
permalink: framework-health
tags:
  - spec
  - infrastructure
  - governance
  - ci-cd
---

# Framework Health

**Status**: Implemented

## Purpose

Automated enforcement of framework governance standards through measurable health metrics, pre-commit hooks, and CI/CD workflows.

## Problem Statement

Framework governance gaps include:
- Files not documented in INDEX.md
- Skills without corresponding specs
- Broken wikilinks fragmenting navigation
- Orphan files invisible in knowledge graph
- Oversized SKILL.md files with too much rationale
- Specs missing standard sections

Manual audits don't scale. We need automated detection and enforcement.

## Solution

A three-tier enforcement system:

| Tier | Mechanism | When | Action |
|------|-----------|------|--------|
| Local | Pre-commit hooks | Every commit | Warn on issues |
| CI | GitHub Actions | PRs to main | Report health, fail on critical |
| Audit | `/audit` skill | On demand | Full report with recommendations |

## Health Metrics

### Tracked Metrics

| Metric | Script | Threshold |
|--------|--------|-----------|
| Files not in INDEX.md | `check_index_completeness.py` | 0 (aspirational) |
| Skills without specs | `audit_framework_health.py` | < 5 |
| Axioms without enforcement | `audit_framework_health.py` | 0 |
| Orphan files | `check_orphan_files.py` | < 10 |
| Broken wikilinks | `check_broken_wikilinks.py` | 0 |
| Oversized skills (>500 lines) | `check_skill_line_count.py` | 0 |
| Specs missing sections | `audit_framework_health.py` | < 5 |

### Exit Codes

| Script | Code 0 | Code 1 | Code 2 |
|--------|--------|--------|--------|
| `audit_framework_health.py` | <20 issues | 20-50 issues | >50 issues |
| Individual checks | Pass | Fail | - |

## Implementation

### Pre-commit Hooks

`.pre-commit-config.yaml` includes:
- `check-skill-line-count` - Warns if SKILL.md > 500 lines
- `check-orphan-files` - Reports orphan files (warning only)

Disabled for speed (run manually):
- `check-index-completeness`
- `check-broken-wikilinks`

### GitHub Workflow

`.github/workflows/framework-health.yml`:
- Runs on PRs and pushes to main
- Executes full health audit
- Posts summary to PR comments
- Uploads health report as artifact

### Scripts

| Script | Purpose |
|--------|---------|
| `audit_framework_health.py` | Full audit with all metrics |
| `check_index_completeness.py` | INDEX.md accounting |
| `check_skill_line_count.py` | SKILL.md size limits |
| `check_broken_wikilinks.py` | Wikilink resolution |
| `check_orphan_files.py` | Orphan file detection |

## Relationships

### Depends On
- [[INDEX.md]] for file accounting
- [[RULES.md]] for enforcement mapping
- [[specs/specs.md]] for spec standards

### Used By
- [[audit-skill]] for manual invocation
- CI/CD pipeline for automated enforcement
- Pre-commit for local development

## Success Criteria

1. **Pre-commit installed**: `pre-commit install` works
2. **CI runs on PRs**: Health report posted to every PR
3. **Metrics tracked**: JSON/markdown reports generated
4. **Thresholds enforced**: Critical issues fail CI
5. **Artifacts preserved**: Reports retained for trend analysis

## Design Rationale

**Why three tiers?**

Local hooks catch issues immediately but must be fast. CI can run comprehensive checks without blocking developers. On-demand audit provides full context for maintenance.

**Why warnings for some checks?**

Some issues (orphan files, slight oversizes) are acceptable in transition. Hard failures for everything would block legitimate work. Warnings provide visibility without friction.

**Why not enforce INDEX.md completeness?**

Too many false positives from generated files, tests, and infrastructure. Better as periodic audit than commit-time gate.
