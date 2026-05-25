import os
import socket
from pathlib import Path
from urllib.parse import urlparse


class BootstrapError(Exception):
    """Raised when bootstrap validation fails."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("\n".join(errors))


def validate_bootstrap(aops_path: Path | str | None = None, client: str | None = None) -> None:
    """Perform fail-fast validation of the polecat runtime environment.

    Checks:
    1. Required environment variables (PKB_MCP_URL, AOPS, POLECAT_HOME, GH_TOKEN)
    2. PKB MCP server reachability
    3. Axioms file presence (aops-core/AXIOMS.md)
    4. Skill registry resolution (checks aops-core/skills/ directory)

    Raises:
        BootstrapError: If any validation check fails.
    """
    errors: list[str] = []

    # 1. Environment variables
    if not aops_path:
        aops_path = os.environ.get("AOPS")

    if not aops_path:
        errors.append("Missing required environment variable: AOPS (must point to framework root)")

    if not os.environ.get("POLECAT_HOME"):
        errors.append("Missing required environment variable: POLECAT_HOME (host config)")

    pkb_url = os.environ.get("PKB_MCP_URL")
    if not pkb_url:
        errors.append("Missing required environment variable: PKB_MCP_URL")

    # PAT secret — only AOPS_BOT_GH_TOKEN is accepted
    if not os.environ.get("AOPS_BOT_GH_TOKEN"):
        errors.append("Missing required secret: AOPS_BOT_GH_TOKEN")

    # Client-specific auth
    if client == "gemini":
        has_gemini_key = bool(os.environ.get("GEMINI_API_KEY"))
        has_gemini_oauth = (Path.home() / ".gemini" / "oauth_creds.json").exists()
        if not has_gemini_key and not has_gemini_oauth:
            errors.append(
                "Missing Gemini auth: GEMINI_API_KEY env var or ~/.gemini/oauth_creds.json required"
            )

    # 2. PKB MCP reachability
    if pkb_url:
        try:
            parsed = urlparse(pkb_url)
            host = parsed.hostname
            port = parsed.port or (80 if parsed.scheme == "http" else 443)

            if host:
                # Quick socket test (2s timeout) before full MCP handshake
                with socket.create_connection((host, port), timeout=2.0):
                    pass

                # Full MCP initialize
                try:
                    from polecat.pkb_bridge import _get_client

                    _get_client()
                except Exception as e:
                    errors.append(f"PKB MCP server failed handshake at {pkb_url}: {e}")
            else:
                errors.append(f"Invalid PKB_MCP_URL: {pkb_url}")
        except (TimeoutError, OSError) as e:
            errors.append(f"PKB MCP server unreachable at {pkb_url}: {e}")
        except Exception as e:
            errors.append(f"PKB MCP connection error: {e}")

    # 3. Axioms file
    if aops_path:
        axioms_path = Path(aops_path) / "aops-core" / "AXIOMS.md"
        if not axioms_path.exists():
            errors.append(f"Axioms file missing: {axioms_path}")

    # 4. Skill registry resolution
    if aops_path:
        skills_dir = Path(aops_path) / "aops-core" / "skills"
        if not skills_dir.exists():
            errors.append(f"Skills directory missing: {skills_dir}")
        else:
            # Check for critical 'sleep' skill mentioned in task
            sleep_skill = skills_dir / "sleep" / "SKILL.md"
            if not sleep_skill.exists():
                errors.append(f"Critical skill 'sleep' missing at {sleep_skill}")

    if errors:
        raise BootstrapError(errors)

    print("✓ Bootstrap validation successful")
