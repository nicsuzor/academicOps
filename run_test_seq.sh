export ENFORCER_TOOL_CALL_THRESHOLD=2
export AOPS_SESSION_ID="test-enforcer-seq"
gemini "Run 'ls', then run 'date', then run 'pwd'. You MUST wait for each command's output before running the next command." < /dev/null
