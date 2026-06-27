"""Metrics & aggregations calculator."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from app.pipeline.cleaner import CleanedTransaction


@dataclass
class CategoryBreakdown:
    category: str
    total: float
    count: int


@dataclass
class MonthlyBreakdown:
    month: str      # "YYYY-MM"
    income: float
    spend: float


@dataclass
class Metrics:
    total_income: float
    total_spend: float
    savings: float
    savings_rate: float | None       # None when income = 0
    top_categories: list[CategoryBreakdown]
    biggest_debit_amount: float | None
    biggest_debit_merchant: str | None
    biggest_debit_date: str | None
    period_start: str | None
    period_end: str | None
    recurring_total: float = 0.0
    monthly_breakdown: list[MonthlyBreakdown] = field(default_factory=list)
    llm_categorized: int = 0
    needs_total: float = 0.0
    wants_total: float = 0.0


def compute(txns: list[CleanedTransaction], llm_categorized: int = 0) -> Metrics:
    total_income = 0.0
    total_spend = 0.0
    recurring_total = 0.0
    needs_total = 0.0
    wants_total = 0.0
    category_totals: dict[str, float] = defaultdict(float)
    category_counts: dict[str, int] = defaultdict(int)
    monthly_income: dict[str, float] = defaultdict(float)
    monthly_spend: dict[str, float] = defaultdict(float)
    biggest_debit: CleanedTransaction | None = None

    dates: list[str] = []

    for txn in txns:
        dates.append(txn.date)
        cat = getattr(txn, "category", "Other")
        month = txn.date[:7]    # "YYYY-MM"

        if txn.txn_type == "credit":
            total_income += txn.amount
            monthly_income[month] += txn.amount
        else:
            spend = abs(txn.amount)
            total_spend += spend
            monthly_spend[month] += spend
            nw = getattr(txn, "needs_wants", "want")
            if nw == "need":
                needs_total += spend
            else:
                wants_total += spend
            if cat != "Salary":
                category_totals[cat] += spend
                category_counts[cat] += 1
            if getattr(txn, "is_recurring", False):
                recurring_total += spend
            if biggest_debit is None or abs(txn.amount) > abs(biggest_debit.amount):
                biggest_debit = txn

    savings = total_income - total_spend
    savings_rate = round((savings / total_income) * 100, 1) if total_income > 0 else None

    top_categories = sorted(
        [CategoryBreakdown(cat, round(total, 2), category_counts[cat])
         for cat, total in category_totals.items()],
        key=lambda x: x.total,
        reverse=True,
    )

    all_months = sorted(set(list(monthly_income.keys()) + list(monthly_spend.keys())))
    monthly_breakdown = [
        MonthlyBreakdown(
            month=m,
            income=round(monthly_income[m], 2),
            spend=round(monthly_spend[m], 2),
        )
        for m in all_months
    ]

    return Metrics(
        total_income=round(total_income, 2),
        total_spend=round(total_spend, 2),
        savings=round(savings, 2),
        savings_rate=savings_rate,
        top_categories=top_categories,
        biggest_debit_amount=round(abs(biggest_debit.amount), 2) if biggest_debit else None,
        biggest_debit_merchant=biggest_debit.merchant or biggest_debit.description_clean[:40] if biggest_debit else None,
        biggest_debit_date=biggest_debit.date if biggest_debit else None,
        period_start=min(dates) if dates else None,
        period_end=max(dates) if dates else None,
        recurring_total=round(recurring_total, 2),
        monthly_breakdown=monthly_breakdown,
        llm_categorized=llm_categorized,
        needs_total=round(needs_total, 2),
        wants_total=round(wants_total, 2),
    )

