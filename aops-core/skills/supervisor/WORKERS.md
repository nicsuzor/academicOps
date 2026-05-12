# WORKERS — Worker Registry

## Worker Types

Three worker types are wired into the supervisor today:

| Worker   | Engine             | Dispatch                              | Sandbox        | Async? |
| -------- | ------------------ | ------------------------------------- | -------------- | ------ |
| `claude` | Claude (Anthropic) | `polecat run -t <id> -p <project>`    | local worktree | No     |
| `gemini` | Gemini (Google)    | `polecat run -t <id> -p <project> -g` | local worktree | No     |
| `jules`  | Jules (Google)     | `pkb task <id> \| jules new --repo …` | Google infra   | Yes    |

`claude` and `gemini` are the two polecat flavours: same dispatcher, same
worktree pattern, different underlying CLI. `jules` is a different beast —
asynchronous, runs on Google infrastructure, returns a session URL and
requires human approval on the Jules web UI before a PR appears.

## Polecat Capability

Polecats are **full-judgment** agents (powered by `claude-sonnet-4-6` by default, per `polecat/defaults/polecat.yaml.example` → `session_defaults.model`, or the Gemini CLI) with the full claude-worker tool surface: Bash, Edit, Write, Read, Skill, and PKB tools (see `.agents/AGENT-TOOLS.md`). Trust them to make in-repo architectural and design decisions. If a task is ambiguous but stays within the target repository, **dispatch with a brief** rather than halting. See [[SKILL.md#halt-on-substitute]].

