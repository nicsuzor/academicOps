<aOps-notification>
<id>dump-gate.md</id>
<title>HANDOVER REQUIRED: run `/dump` before you stop</title>
<warning>Your work does not leave this session until it is committed and handed over</warning>
<note>

You are running in an isolated, ephemeral environment. Anything you have not committed will be destroyed when this session ends, and your report is the only channel back to whoever dispatched you.

Run the `dump` skill now. It carries the obligations your handover is judged against:

- commit and push every change, including partial work;
- release any task you claimed, with its status and a resume path;
- emit one final report in which every load-bearing claim carries its basis tag and a pinpoint citation.

If you have already run `dump` this turn, stop as you intended -- this gate withholds the stop once and will not ask again.
</note>
</aOps-notification>
