"""Savings recommendations engine — Phase 2.5."""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field

from app.pipeline.cleaner import CleanedTransaction
from app.pipeline.metrics import Metrics

logger = logging.getLogger(__name__)

_WANTS_BUDGET_PCT_DEFAULT = 30.0


@dataclass
class Recommendation:
    category: str
    amount_spent: float
    suggested_cap: float
    potential_saving: float
    top_merchants: list[str]
    suggestion_text: str


@dataclass
class RecommendationsResult:
    salary_monthly: float | None
    wants_budget_pct: float
    wants_budget: float | None       # None when no salary
    wants_actual: float
    needs_actual: float
    is_over_budget: bool
    recommendations: list[Recommendation] = field(default_factory=list)
    summary: str = ""


def compute(
    txns: list[CleanedTransaction],
    metrics: Metrics,
    salary_monthly: float | None = None,
    wants_budget_pct: float = _WANTS_BUDGET_PCT_DEFAULT,
) -> RecommendationsResult:
    """Compute needs/wants split and savings recommendations."""

    # --- aggregate wants and needs spend ---
    wants_by_category: dict[str, float] = defaultdict(float)
    merchants_by_category: dict[str, list[str]] = defaultdict(list)
    needs_actual = 0.0

    for txn in txns:
        if txn.txn_type != "debit":
            continue
        nw = getattr(txn, "needs_wants", "want")
        spend = abs(txn.amount)
        if nw == "want":
            cat = getattr(txn, "category", "Other")
            wants_by_category[cat] += spend
            merchant = txn.merchant or txn.description_clean[:30]
            if merchant not in merchants_by_category[cat]:
                merchants_by_category[cat].append(merchant)
        elif nw == "need":
            needs_actual += spend

    wants_actual = sum(wants_by_category.values())

    # --- infer salary if not provided ---
    if salary_monthly is None:
        salary_monthly = _infer_salary(txns, metrics)

    wants_budget = (salary_monthly * wants_budget_pct / 100.0) if salary_monthly else None

    is_over_budget = bool(wants_budget and wants_actual > wants_budget)

    recommendations: list[Recommendation] = []

    if is_over_budget and wants_budget:
        # Distribute the budget proportionally across want categories by their share of actual spend
        for cat, spent in sorted(wants_by_category.items(), key=lambda x: x[1], reverse=True):
            share = spent / wants_actual if wants_actual > 0 else 0
            cap = round(wants_budget * share, 2)
            saving = round(spent - cap, 2)
            if saving <= 0:
                continue
            merchants = merchants_by_category[cat][:3]
            text = _build_suggestion(cat, spent, cap, saving, merchants)
            recommendations.append(Recommendation(
                category=cat,
                amount_spent=round(spent, 2),
                suggested_cap=cap,
                potential_saving=saving,
                top_merchants=merchants,
                suggestion_text=text,
            ))

        # Try LLM-enhanced suggestions (best-effort; falls back to template)
        _enrich_with_llm(recommendations)

        # Sort by saving potential descending
        recommendations.sort(key=lambda r: r.potential_saving, reverse=True)

    summary = _build_summary(
        salary_monthly, wants_budget, wants_actual, needs_actual, is_over_budget
    )

    return RecommendationsResult(
        salary_monthly=salary_monthly,
        wants_budget_pct=wants_budget_pct,
        wants_budget=wants_budget,
        wants_actual=round(wants_actual, 2),
        needs_actual=round(needs_actual, 2),
        is_over_budget=is_over_budget,
        recommendations=recommendations,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _infer_salary(txns: list[CleanedTransaction], metrics: Metrics) -> float | None:
    """Use max salary-category credit as monthly salary proxy."""
    monthly_salary: dict[str, float] = defaultdict(float)
    for txn in txns:
        if txn.txn_type == "credit" and getattr(txn, "category", "") == "Salary":
            monthly_salary[txn.date[:7]] += txn.amount
    if not monthly_salary:
        return None
    return round(max(monthly_salary.values()), 2)


def _build_suggestion(
    category: str,
    spent: float,
    cap: float,
    saving: float,
    merchants: list[str],
) -> str:
    merchant_hint = f" (top spends: {', '.join(merchants)})" if merchants else ""
    return (
        f"Consider reducing {category} spend from ₹{spent:,.0f} to ₹{cap:,.0f}"
        f"{merchant_hint} — you could save ₹{saving:,.0f}/month."
    )


def _enrich_with_llm(recommendations: list[Recommendation]) -> None:
    """Replace suggestion_text with LLM-generated one where possible."""
    import json
    from app.services.llm import llm_service

    if not llm_service.available or not recommendations:
        return

    payload = [
        {
            "category": r.category,
            "amount_spent": r.amount_spent,
            "suggested_cap": r.suggested_cap,
            "potential_saving": r.potential_saving,
            "top_merchants": r.top_merchants,
        }
        for r in recommendations
    ]

    system = (
        "You are a concise personal finance advisor for Indian users. "
        "Given a list of overspent categories, return a JSON array with one object per category in the same order. "
        'Each object: {"index": <int>, "suggestion": "<one actionable sentence in ₹ terms, under 20 words>"}. '
        "Return ONLY the JSON array."
    )

    try:
        raw = llm_service.complete(
            system_prompt=system,
            user_prompt=json.dumps(payload),
            temperature=0.3,
            estimated_tokens=600,
        )
        results: list[dict] = json.loads(raw)
        for item in results:
            idx = int(item["index"])
            if 0 <= idx < len(recommendations) and item.get("suggestion"):
                recommendations[idx].suggestion_text = item["suggestion"]
    except Exception as exc:
        logger.warning("LLM enrichment for recommendations failed: %s", exc)


def _build_summary(
    salary: float | None,
    budget: float | None,
    wants_actual: float,
    needs_actual: float,
    is_over: bool,
) -> str:
    if salary is None:
        return (
            f"You spent ₹{wants_actual:,.0f} on wants and ₹{needs_actual:,.0f} on needs. "
            "Add your salary to see personalised savings targets."
        )
    if not is_over:
        return (
            f"You're within your ₹{budget:,.0f} wants budget — "
            f"actual wants spend was ₹{wants_actual:,.0f}. Great discipline!"
        )
    over_by = wants_actual - (budget or 0)
    return (
        f"You exceeded your wants budget of ₹{budget:,.0f} by ₹{over_by:,.0f}. "
        "See recommendations below to get back on track."
    )
