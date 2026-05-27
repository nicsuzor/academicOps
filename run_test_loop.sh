export ENFORCER_TOOL_CALL_THRESHOLD=1
export AOPS_SESSION_ID="test-enforcer-loop"
gemini "Run the 'ls' command using run_shell_command. After you see the output, run 'echo Done'." < /dev/null
