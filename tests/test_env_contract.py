import os
import re
from pathlib import Path

import yaml

AOPS_ROOT = Path(__file__).parent.parent
CONTRACT_FILE = AOPS_ROOT / "specs" / "env-contract.yaml"


def get_referenced_vars():
    vars_found = set()
    py_pattern = re.compile(r'(?:os\.environ(?:\.get)?|os\.getenv)\(\s*["\']([A-Z_0-9]+)["\']')
    py_pattern2 = re.compile(r'os\.environ\[["\']([A-Z_0-9]+)["\']\]')
    sh_pattern = re.compile(r"\$\{([A-Z_0-9]+)(?:[:\-+?][^}]+)?\}")
    sh_pattern2 = re.compile(r"\$([A-Z_0-9]+)\b")

    for root_dir, _, files in os.walk(AOPS_ROOT):
        if (
            ".git" in root_dir
            or "node_modules" in root_dir
            or ".agents" in root_dir
            or "dist" in root_dir
        ):
            continue
        for file in files:
            if not file.endswith((".py", ".sh", ".yaml", ".yml", ".ts")):
                continue
            path = Path(root_dir) / file
            try:
                content = path.read_text(encoding="utf-8")
                vars_found.update(py_pattern.findall(content))
                vars_found.update(py_pattern2.findall(content))
                vars_found.update(sh_pattern.findall(content))
                vars_found.update(sh_pattern2.findall(content))
            except Exception:
                pass

    # Filter only framework-relevant variables
    prefixes = (
        "AOPS",
        "POLECAT",
        "PKB",
        "GH_TOKEN",
        "GITHUB_TOKEN",
        "GEMINI",
        "CLAUDE",
        "ACA_DATA",
    )
    return {v for v in vars_found if v.startswith(prefixes)}


def test_env_contract_validation():
    assert CONTRACT_FILE.exists(), f"Contract file missing: {CONTRACT_FILE}"

    with open(CONTRACT_FILE) as f:
        contract = yaml.safe_load(f)

    declared_vars = contract.get("variables", {})
    referenced_vars = get_referenced_vars()

    undeclared = referenced_vars - set(declared_vars.keys())
    assert not undeclared, f"Undeclared environment variables referenced in code: {undeclared}"

    unconsumed = set(declared_vars.keys()) - referenced_vars
    assert not unconsumed, f"Contract entries declared but never consumed in codebase: {unconsumed}"

    for var, details in declared_vars.items():
        setters = details.get("authoritative_source", "")
        if isinstance(setters, list):
            assert len(setters) <= 1, (
                f"Variable {var} has multiple authoritative setters: {setters}"
            )
        elif isinstance(setters, str):
            assert " and " not in setters and "," not in setters, (
                f"Variable {var} has multiple authoritative setters: {setters}"
            )
