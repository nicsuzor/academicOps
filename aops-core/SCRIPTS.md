# aops-core Scripts

Utility scripts for the academicOps framework core.

## User Scripts

These scripts are intended to be run by users or in automated workflows.

| Script                 | Purpose                                                                                                                                 |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `transcript.py`        | Generate markdown transcripts from session logs (.jsonl/.json)                                                                          |
| `sync_gha_sessions.py` | Sync Claude session artifacts from GitHub Actions to local storage. Configured via `AOPS_GHA_REPOS` env var or `~/.aops/gha-repos.txt`. |

## Internal Scripts

These scripts are primarily used by the framework internally or during installation.

| Script                | Purpose                                                   |
| --------------------- | --------------------------------------------------------- |
| `ensure-path.sh`      | Ensure framework paths exist and have correct permissions |
| `run-mcp.sh`          | Entrypoint for running the MCP server                     |
| `compliance_block.py` | Script used by the enforcer to explain policy blocks      |
| `pkb_perf_proxy.py`   | Performance proxy for PKB operations                      |
