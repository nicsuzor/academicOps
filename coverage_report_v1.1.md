# Coverage Report v1.1 Baseline

**Date:** 2026-02-04
**Total Coverage:** 43%
**Test Status:** 5 Failures, 870 Passed

## Test Failures

1.  `tests/hooks/test_gate_registry_new.py::TestPostHydrationTrigger::test_detects_task_hydrator` (TypeError)
2.  `tests/hooks/test_gemini_gate_enforcement.py::TestGeminiHydrationGateNoStateFile::test_missing_state_file_should_block` (AssertionError)
3.  `tests/hooks/test_userpromptsubmit_first_prompt.py::TestFirstPromptHydration::test_context_template_loads_without_format_error` (KeyError: 'mcp_tools')
4.  `tests/hooks/test_userpromptsubmit_first_prompt.py::TestFirstPromptHydration::test_context_template_preserves_structure_after_formatting` (KeyError: 'mcp_tools')
5.  `aops-core/tests/test_hydration_strict.py::test_strict_hydration` (AssertionError)

## Modules Below 85% Threshold

### Core Hooks (Critical)
| Module | Coverage | Missing Lines |
|---|---|---|
| `hooks/autocommit_state.py` | 0% | All |
| `hooks/command_intercept.py` | 0% | All |
| `hooks/policy_enforcer.py` | 0% | All |
| `hooks/task_binding.py` | 0% | All |
| `hooks/gate_registry.py` | 60% | ~350 lines |
| `hooks/router.py` | 56% | ~130 lines |
| `hooks/gates.py` | 25% | Most |

### Core Libraries
| Module | Coverage | Missing Lines |
|---|---|---|
| `lib/extract_labor.py` | 0% | All |
| `lib/session_analyzer.py` | 12% | ~400 lines |
| `lib/task_storage.py` | 51% | ~135 lines |
| `lib/session_state.py` | 54% | ~166 lines |
| `lib/transcript_parser.py` | 56% | ~740 lines |
| `lib/task_index.py` | 62% | ~90 lines |

### MCP Servers
| Module | Coverage | Missing Lines |
|---|---|---|
| `mcp_servers/tasks_server.py` | 47% | ~470 lines |

### Scripts & Tools
| Module | Coverage | Missing Lines |
|---|---|---|
| `polecat/*.py` | 0% | All |
| `scripts/*.py` | 0% | Most |

## Prioritized Gaps (Next Steps)

1.  **Fix Current Failures**: Address the 5 failing tests in hydration and template logic.
2.  **Gate Registry & Router**: Increase coverage for `gate_registry.py` and `router.py` as they control flow.
3.  **Policy Enforcer**: 0% coverage on security/policy logic is a risk.
4.  **Task Storage & Index**: Critical for data integrity, currently ~50-60%.
5.  **Transcript Parser**: Heavy logic (1.6k LOC) with only 56% coverage.
