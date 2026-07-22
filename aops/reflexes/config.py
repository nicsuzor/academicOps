"""Configuration loader for Reflexes policy evaluator harness.

Loads evaluator settings (model choice, timeout, fail-open policy) from the
plugin's distributed configuration surface (aops/reflexes/config.json).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

REFLEXES_DIR = Path(__file__).resolve().parent
CONFIG_FILE = REFLEXES_DIR / "config.json"

DEFAULT_EVALUATOR_MODEL = "claude-3-5-haiku-20241022"


@dataclass(frozen=True)
class ReflexesConfig:
    evaluator_model: str = DEFAULT_EVALUATOR_MODEL
    provider: str = "anthropic"
    timeout_seconds: float = 5.0
    fail_open: bool = True


def load_config() -> ReflexesConfig:
    """Load Reflexes configuration from distributed config.json or return defaults."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return ReflexesConfig(
                evaluator_model=data.get("evaluator_model", DEFAULT_EVALUATOR_MODEL),
                provider=data.get("provider", "anthropic"),
                timeout_seconds=float(data.get("timeout_seconds", 5.0)),
                fail_open=bool(data.get("fail_open", True)),
            )
        except Exception:
            return ReflexesConfig()
    return ReflexesConfig()
