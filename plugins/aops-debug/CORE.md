# aops-debug Plugin Core

- **Diagnostic Tracing**: Passively intercepts runtime hook payloads and exports telemetry traces to OpenTelemetry.
- **Inspection**: Writes raw hook payloads to temporary directory files for debugging runtime events, arguments, and transcript state.
- **Passive Telemetry**: Adds no behavioral restrictions to session execution; never alter control flow based on debug outputs.
