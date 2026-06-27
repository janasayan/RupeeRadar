"""Template-based insight generator — Phase 1 + Phase 2 tiers + Phase 3 LLM narratives."""

from __future__ import annotations

import logging

from app.pipeline.metrics import Metrics
from app.pipeline.recurring import RecurringGroup

logger = logging.getLogger(__name__)

_NARRATIVE_SYSTEM = (
    "You are a personal finance advisor. "
    "Given a summary of someone's Indian bank statement, generate exactly 2 brief, "
    "actionable insights in plain English. "
    "One insight per line. No bullet points, no numbering. Use ₹ for amounts. No PII."
)


def _build_summary(metrics: Metrics) -> str:
    lines = [
        f"Income: ₹{metrics.total_income:,.0f}",
        f"Spend: ₹{metrics.total_spend:,.0f}",
        f"Savings: ₹{metrics.savings:,.0f}",
    ]
    if metrics.top_categories:
        top3 = ", ".join(
            f"{c.category} ₹{c.total:,.0f}" for c in metrics.top_categories[:3]
        )
        lines.append(f"Top categories: {top3}")
    if metrics.recurring_total > 0:
        lines.append(f"Recurring payments: ₹{metrics.recurring_total:,.0f}/month")
    if len(metrics.monthly_breakdown) >= 2:
        last = metrics.monthly_breakdown[-1]
        prev = metrics.monthly_breakdown[-2]
        if prev.spend > 0:
            delta_pct = round((last.spend - prev.spend) / prev.spend * 100, 1)
            direction = "up" if delta_pct > 0 else "down"
            lines.append(f"Spend trend: {abs(delta_pct)}% {direction} last month")
    return "\n".join(lines)


def generate(metrics: Metrics, recurring_groups: list[RecurringGroup] | None = None) -> list[str]:
    insights: list[str] = []

    # 1. Summary
    insights.append(
        f"Total income ₹{metrics.total_income:,.0f}, "
        f"total spend ₹{metrics.total_spend:,.0f}, "
        f"savings ₹{metrics.savings:,.0f}"
        + (f" ({metrics.savings_rate}% savings rate)." if metrics.savings_rate is not None else ".")
    )

    # 2. Top category
    if metrics.top_categories:
        top = metrics.top_categories[0]
        insights.append(
            f"Your biggest spend category is {top.category} — "
            f"₹{top.total:,.0f} across {top.count} transaction(s)."
        )

    # 3. Biggest transaction
    if metrics.biggest_debit_amount is not None:
        insights.append(
            f"Your largest single transaction was ₹{metrics.biggest_debit_amount:,.0f} "
            f"to {metrics.biggest_debit_merchant} on {metrics.biggest_debit_date}."
        )

    # 4. Recurring payment insight
    if recurring_groups:
        monthly_recurring = [g for g in recurring_groups if g.frequency == "monthly"]
        n = len(recurring_groups)
        total_rec = metrics.recurring_total
        if monthly_recurring:
            insights.append(
                f"We detected {n} recurring payment(s) totalling "
                f"₹{total_rec:,.0f}/month — including "
                f"{', '.join(g.label for g in monthly_recurring[:3])}."
            )
        else:
            insights.append(
                f"We detected {n} recurring payment(s) totalling ₹{total_rec:,.0f}."
            )

    # 5. Deficit warning
    if metrics.savings < 0:
        insights.append(
            f"You spent ₹{abs(metrics.savings):,.0f} more than you earned this period. "
            "Consider reviewing discretionary expenses."
        )

    # 6. Second category if available (only if no deficit warning took slot 5)
    if len(metrics.top_categories) >= 2 and metrics.savings >= 0:
        second = metrics.top_categories[1]
        insights.append(
            f"{second.category} was your second-largest spend category at ₹{second.total:,.0f}."
        )

    # 7. LLM categorization note
    if metrics.llm_categorized > 0:
        insights.append(
            f"{metrics.llm_categorized} transaction(s) were categorized using AI "
            "because they didn't match known merchants."
        )

    # 8. LLM narrative insights (Phase 3)
    llm_insights = _generate_llm_narratives(metrics)
    insights.extend(llm_insights)

    return insights[:8]


def _generate_llm_narratives(metrics: Metrics) -> list[str]:
    try:
        from app.services.llm import llm_service
        if not llm_service.available:
            return []
        summary = _build_summary(metrics)
        raw = llm_service.complete(
            system_prompt=_NARRATIVE_SYSTEM,
            user_prompt=summary,
            temperature=0.3,
            estimated_tokens=600,
        )
        lines = [line.strip() for line in raw.strip().splitlines() if line.strip()]
        return lines[:3]
    except Exception as exc:
        logger.debug("LLM narrative insights skipped: %s", exc)
        return []
