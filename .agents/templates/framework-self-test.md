---
title: Framework Self-Test
type: template
category: process
description: Execute end-to-end framework self-test suite across plugins, hooks, and subagent orchestration. Select when certifying framework runtime integrity.
tags: [self-test, certification, test-suite, framework, integrity, process]
---

# Process: Framework Self-Test

Comprehensive self-test verification procedure for all active framework plugins and runtime components.

## 1. Test Environment Setup

- Verify clean workspace state and build all plugins (`make build`).
- Ensure test virtual environment has required dependencies installed.

## 2. Unit and Integration Test Execution

- Run full pytest test suite across all plugin packages (`<test-runner>`).
- Verify all unit tests pass with zero errors.

## 3. End-to-End Hook and Tool Certification

- Execute end-to-end hook dispatch tests to verify runtime event wiring.
- Test MCP tool registration, schema validation, and tool invocation.

## 4. Subagent Orchestration Sanity Check

- Dispatch a test subagent to execute a bounded task in an isolated container.
- Confirm transcript logging, token accounting, and return channels operate correctly.

## 5. Certification Report

- Emit structured test summary: passed count, skipped count, duration, and commit hash.
