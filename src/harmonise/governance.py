"""Table B2 step 5, and the cohort 6 governance gate.

Two application sentences are enforced here rather than described:

  "constructs that cannot be harmonised are declared non-harmonisable" — a
  non-harmonisable row without a stated reason is refused, not written; and

  cohort 6 "proceeds only where First Nations leadership determines the question,
  measures and interpretation are culturally meaningful, and culturally grounded
  wellbeing indicators are not forced into diagnosis" — mapping a governed cohort's
  wellbeing indicators as a proxy for a diagnostic construct raises an error.
"""
from __future__ import annotations


class GovernanceError(RuntimeError):
    pass


class NonHarmonisableWithoutReason(RuntimeError):
    pass


def check_declarations(constructs) -> None:
    """Refuse to run if a declared non-harmonisable construct carries no reason."""
    offenders = [
        c["id"] for c in constructs
        if c.get("declared_non_harmonisable") and not str(c.get("reason", "")).strip()
    ]
    if offenders:
        raise NonHarmonisableWithoutReason(
            "Table B2 step 5 requires a stated reason for every declared non-harmonisable "
            f"construct. Missing for: {', '.join(offenders)}"
        )


def forbidden_proxy(cohort_spec: dict, construct_id: str, status: str) -> bool:
    gov = cohort_spec.get("governance", {}) or {}
    forbidden = gov.get("forbid_proxy_for_constructs") or []
    return status == "proxy" and construct_id in forbidden


def enforce(cohort_spec: dict, construct_id: str, status: str) -> str:
    """Downgrade a forbidden proxy to a governed status instead of asserting equivalence."""
    if forbidden_proxy(cohort_spec, construct_id, status):
        return "governed_not_proxied"
    return status


def gate(cohort_spec: dict, include_governed: bool) -> bool:
    """Governed cohorts are excluded unless the operator opts in explicitly."""
    gov = cohort_spec.get("governance", {}) or {}
    if gov.get("requires_signoff") and not include_governed:
        return False
    return True
