**rbg's rule set is empty. No rule is being checked on any tool call.**

{detail}

This is a deliberate state, not a fault: every rule carries `trigger: off`, and
rules are being switched back on one at a time. Nothing is checking your tool
calls against the axioms or this project's rules, so hold your own line — and
if you hit something a rule would have caught, that is the signal worth
reporting.
