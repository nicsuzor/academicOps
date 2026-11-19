# aops-debug Plugin Core

- **Diagnostic Tracing**: The `aops-debug` plugin passively intercepts runtime hook payloads and exports telemetry traces to OpenTelemetry.
- **Inspection**: Raw hook payloads are written to temp directory files for debugging runtime events, arguments, and transcript state.
- **Zero Ingestion Side-Effects**: This plugin emits no instructions or behavioral restrictions into session context; do not alter execution flow based on debug outputs.
