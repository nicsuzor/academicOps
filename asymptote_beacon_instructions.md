# Agent Beacon Installation & Configuration Guide

"Asymptote" refers to Agent Beacon, an open-source endpoint telemetry layer developed by Asymptote Labs. Agent Beacon captures and normalizes telemetry (like prompts, tool usage, and file edits) from AI agent harnesses like Claude Code and Antigravity CLI (AGY).

## 1. Installation

### macOS (Homebrew)

```bash
brew tap asymptote-labs/tap
brew trust --formula asymptote-labs/tap/beacon
brew install beacon
```

### Debian / Linux

Beacon publishes pre-compiled archives for Linux (`amd64` and `arm64`) on their [GitHub Releases page](https://github.com/Asymptote-Labs/agent-beacon/releases).

To install on Debian:

1. Download the latest Linux archive from the GitHub Releases page.
2. Extract the archive.
3. Move the `beacon` and `beacon-otelcol` binaries to a directory in your PATH (e.g., `/usr/local/bin/`).

Alternatively, you can build from source:

```bash
git clone https://github.com/Asymptote-Labs/agent-beacon.git
cd agent-beacon/cli/beacon
make build
```

## 2. Initialize the Local Endpoint

After installing the CLI, run the endpoint installer to create the shared configuration and the local `runtime.jsonl` log path:

```bash
beacon endpoint install
```

## 3. Configure Agent Harnesses

### Claude Code

Claude Code natively supports local OTLP export, but you can also install Beacon's hooks for richer lifecycle and tool telemetry:

```bash
beacon endpoint hooks install --harness claude
```

_(Add `--level project` if you want to install these hooks strictly in the local project directory instead of globally)._

### Antigravity CLI (AGY)

AGY natively supports Beacon hooks for prompt telemetry, file edits, and tool tracking:

```bash
beacon endpoint hooks install --harness antigravity
```

_(Restart AGY after installing or removing hooks so new sessions load the updated configuration)._

## 4. Google Cloud Storage Forwarding (The "Bigger Sink" for Agents)

Beacon normalizes OTLP data and saves it locally as JSONL (e.g., `~/.beacon/endpoint/logs/runtime.jsonl` or `/var/log/beacon-agent/runtime.jsonl`). To forward this to a data lake or SIEM platform like Google Cloud Storage (GCS) for large-scale agent observability, Asymptote provides a configuration generator for **Vector** (an open-source observability pipeline).

1. **Generate the GCS Forwarding Config Pack:**
   Run the following command to generate the Vector config tailored for Google Cloud Storage:
   ```bash
   sudo /opt/beacon/bin/beacon endpoint gcs install-pack --system --output ./beacon-gcs-pack
   ```
   _(This generates a `vector.toml` configuration, a smoke test script, and sample events)._

2. **Deploy Vector:**
   Install [Vector](https://vector.dev/) on your system using your standard management tooling.

3. **Configure and Run:**
   Copy the generated `vector.toml` into Vector's configuration directory (e.g., `/etc/vector/beacon-gcs.toml`). Ensure that you set your destination environment variables (like the bucket name) and that your system has the appropriate Application Default Credentials or workload identity enabled to write to the GCS bucket.

   ```bash
   sudo cp ./beacon-gcs-pack/vector.toml /etc/vector/beacon-gcs.toml
   export BEACON_GCS_BUCKET="your-gcs-bucket-name"
   export BEACON_GCS_PREFIX="beacon/runtime"
   vector --config /etc/vector/beacon-gcs.toml
   ```

Vector will tail the Beacon JSONL logs, batch the events, compress them into `NDJSON` objects, and stream them securely to your Google Cloud Storage bucket.
