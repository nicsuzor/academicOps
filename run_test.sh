export ENFORCER_TOOL_CALL_THRESHOLD=2
export AOPS_SESSION_ID="test-enforcer-loop"
gemini "Run the 'ls' command 3 times using run_shell_command. Then stop." < /dev/null
