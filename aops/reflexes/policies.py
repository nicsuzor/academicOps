"""Reflexes CoPE Policy Registry for academicOps.

Maps canonical axiom rule files (.agents/rules/*.md - SSoT) to their derived
CoPE-format runtime policy renderings (aops/reflexes/policies/*.md).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

REFLEXES_DIR = Path(__file__).resolve().parent
POLICIES_DIR = REFLEXES_DIR / "policies"
RULES_DIR = REFLEXES_DIR.parent.parent / ".agents" / "rules"


@dataclass(frozen=True)
class AxiomPolicyMapping:
    slug: str
    ssot_rule_file: str
    cope_policy_file: str
    code: str
    trigger: str


AXIOM_POLICIES: list[AxiomPolicyMapping] = [
    AxiomPolicyMapping(
        slug="bounded-execution",
        ssot_rule_file="bounded-execution.md",
        cope_policy_file="Bounded-Execution.md",
        code="BE",
        trigger="before_tool_call",
    ),
    AxiomPolicyMapping(
        slug="categorical-imperative",
        ssot_rule_file="categorical-imperative.md",
        cope_policy_file="Categorical-Imperative.md",
        code="CI",
        trigger="before_response",
    ),
    AxiomPolicyMapping(
        slug="cite-sources",
        ssot_rule_file="cite-sources.md",
        cope_policy_file="Cite-Sources.md",
        code="CS",
        trigger="before_response",
    ),
    AxiomPolicyMapping(
        slug="closure",
        ssot_rule_file="closure.md",
        cope_policy_file="Closure.md",
        code="CL",
        trigger="before_tool_call",
    ),
    AxiomPolicyMapping(
        slug="costly-ops-approval",
        ssot_rule_file="costly-ops-approval.md",
        cope_policy_file="Costly-Ops-Approval.md",
        code="CO",
        trigger="before_tool_call",
    ),
    AxiomPolicyMapping(
        slug="data-boundaries",
        ssot_rule_file="data-boundaries.md",
        cope_policy_file="Data-Boundaries.md",
        code="DB",
        trigger="before_tool_call",
    ),
    AxiomPolicyMapping(
        slug="do-one-thing",
        ssot_rule_file="do-one-thing.md",
        cope_policy_file="Do-One-Thing.md",
        code="DT",
        trigger="before_response",
    ),
    AxiomPolicyMapping(
        slug="evidence-immutable",
        ssot_rule_file="evidence-immutable.md",
        cope_policy_file="Evidence-Immutable.md",
        code="EI",
        trigger="before_tool_call",
    ),
    AxiomPolicyMapping(
        slug="exercise-authority",
        ssot_rule_file="exercise-authority.md",
        cope_policy_file="Exercise-Authority.md",
        code="EA",
        trigger="before_tool_call",
    ),
    AxiomPolicyMapping(
        slug="full-observability",
        ssot_rule_file="full-observability.md",
        cope_policy_file="Full-Observability.md",
        code="FO",
        trigger="before_response",
    ),
    AxiomPolicyMapping(
        slug="halt-on-failure",
        ssot_rule_file="halt-on-failure.md",
        cope_policy_file="Halt-On-Failure.md",
        code="HF",
        trigger="before_tool_call",
    ),
    AxiomPolicyMapping(
        slug="honest-epistemics",
        ssot_rule_file="honest-epistemics.md",
        cope_policy_file="Honest-Epistemics.md",
        code="HE",
        trigger="before_response",
    ),
    AxiomPolicyMapping(
        slug="judgment-non-delegable",
        ssot_rule_file="judgment-non-delegable.md",
        cope_policy_file="Judgment-Non-Delegable.md",
        code="JD",
        trigger="before_tool_call",
    ),
    AxiomPolicyMapping(
        slug="pull-over-push",
        ssot_rule_file="pull-over-push.md",
        cope_policy_file="Pull-Over-Push.md",
        code="PP",
        trigger="before_response",
    ),
    AxiomPolicyMapping(
        slug="single-source-of-truth",
        ssot_rule_file="single-source-of-truth.md",
        cope_policy_file="Single-Source-Of-Truth.md",
        code="ST",
        trigger="before_tool_call",
    ),
]


def get_policy_file(slug: str) -> Path | None:
    """Get the derived CoPE policy file path for a given axiom slug."""
    for policy in AXIOM_POLICIES:
        if policy.slug == slug:
            path = POLICIES_DIR / policy.cope_policy_file
            if path.exists():
                return path
    return None
