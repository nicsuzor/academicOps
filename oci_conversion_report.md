# Report: Converting Polecat to Open Container Initiative (OCI) Standards

## What would it take?

To convert the current Docker implementation in `polecat` to a generic OCI-standard approach (e.g., natively supporting Podman, nerdctl), we would need to implement the following changes:

1. **CLI Abstraction**: The `docker` command is heavily hardcoded throughout `lib/polecat/cli.py`, `Makefile`, and the entire `tests/polecat/` suite. We would need to introduce an abstraction (e.g., an environment variable like `CONTAINER_RUNTIME=podman`) and pass this down gracefully.
2. **Networking Adapters**: The codebase relies explicitly on `host.docker.internal` for host gateway resolution (especially critical for the local OpenTelemetry Collector relays and MCP setups). Podman uses `host.containers.internal`, meaning we must build runtime detection to inject the correct `--add-host` arguments dynamically.
3. **Volume and Permission Mappings**: Docker handles volume mapping differently from rootless daemonless runtimes like Podman, which use user namespaces. `polecat` heavily relies on bind-mounting host directories (session logs, transcripts, config) and pre-creating directories to avoid root ownership conflicts. Adapting this requires robust UID/GID mapping handling (e.g., `--userns=keep-id`).
4. **Socket Sharing**: The configuration permits mounting `/var/run/docker.sock` to allow containers to spawn siblings. This logic must be generalized to locate and mount `/run/user/$UID/podman/podman.sock` for rootless Podman execution.

## Would we gain anything?

1. **Enhanced Security**: OCI alternatives like Podman are daemonless and can be run rootless by default, mitigating the security risks associated with the Docker daemon's root privileges (and escaping via `docker.sock`).
2. **Developer Flexibility**: As you noted, some developers prefer specialized, lightweight tools natively integrated with Systemd (like Podman) over Docker Desktop’s monolithic architecture, especially on Linux environments.

## Is it worth the effort?

**Currently, no.**

While the benefits to security and developer preference are real, the cost-to-benefit ratio is poor for the current state of the repository.
- **High Refactoring Cost**: We would need to rewrite and test over a dozen test files (`test_container_invocation.py`, `test_container_smoke.py`, etc.), the `Makefile`, and `lib/polecat/cli.py`.
- **Complexity in Maintenance**: Managing the nuanced networking differences (`host.docker.internal` vs `host.containers.internal`) and volume permission layers between Docker and Podman adds significant fragility to the container orchestration layer.
- **Ubiquity of Docker**: Docker remains ubiquitous enough that requiring it is rarely a blocking issue for users or CI pipelines.

**Recommendation:** Unless there is a strict security compliance mandate demanding rootless container execution, or a large portion of the userbase is entirely blocked by the Docker requirement, the effort is better spent stabilizing core agent functionality. If developers want to use Podman today, they can likely alias `docker=podman` in their shell, as Podman is designed to be CLI-compatible with Docker for most basic use cases.
