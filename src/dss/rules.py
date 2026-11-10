"""Underwriting rules: model probability + business rules -> GREEN / YELLOW / RED.

Placeholder thresholds below are a starting point only.
TODO: set thresholds from the model's score distribution / business cost of errors,
and document every rule in docs/kpi_definitions.md and the report (Chapter 4).
"""
from __future__ import annotations

from dataclasses import dataclass, field

GREEN, YELLOW, RED = "GREEN", "YELLOW", "RED"

P_GREEN_MAX = 0.08   # p(default) below this -> approve
P_RED_MIN = 0.20     # p(default) at or above this -> reject
DTI_MAX = 0.40       # annuity / income
DPD_HARD_STOP = 90   # any history over 90 days past due


@dataclass
class Decision:
    flag: str
    reasons: list[str] = field(default_factory=list)


def evaluate(app: dict, p_default: float | None) -> Decision:
    """app: dict with at least debt_to_income, max_dpd_days, has_current_overdue."""
    reasons: list[str] = []
    flag = GREEN

    def worsen(to: str, why: str) -> None:
        nonlocal flag
        order = [GREEN, YELLOW, RED]
        if order.index(to) > order.index(flag):
            flag = to
        reasons.append(why)

    if p_default is not None:
        if p_default >= P_RED_MIN:
            worsen(RED, f"Model risk {p_default:.1%} >= {P_RED_MIN:.0%}")
        elif p_default >= P_GREEN_MAX:
            worsen(YELLOW, f"Model risk {p_default:.1%} between {P_GREEN_MAX:.0%} and {P_RED_MIN:.0%}")
    else:
        worsen(YELLOW, "No model score yet - manual review")

    dti = app.get("debt_to_income")
    if dti is not None and dti > DTI_MAX:
        worsen(YELLOW, f"Debt-to-income {dti:.2f} > {DTI_MAX:.2f}")
    if (app.get("max_dpd_days") or 0) > DPD_HARD_STOP:
        worsen(RED, f"History of more than {DPD_HARD_STOP} days past due")
    if app.get("has_current_overdue"):
        worsen(YELLOW, "Currently overdue in the Credit Bureau")

    if not reasons:
        reasons.append("All checks passed")
    return Decision(flag, reasons)
