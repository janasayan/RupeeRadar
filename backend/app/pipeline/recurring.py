"""Recurring payment detection.

Groups transactions by fuzzy description similarity, then checks:
- ≥ 2 occurrences
- Amount within ±10% across occurrences
- Infers frequency from date intervals
"""

from __future__ import annotations

import re
import uuid
from collections import defaultdict
from dataclasses import dataclass, field

from app.pipeline.cleaner import CleanedTransaction


@dataclass
class RecurringGroup:
    id: str
    label: str
    category: str
    amount: float           # typical (negative = debit)
    frequency: str          # "monthly" | "weekly" | "irregular"
    occurrence_count: int
    last_seen: str          # YYYY-MM-DD
    transaction_ids: list[str] = field(default_factory=list)


def detect(txns: list[CleanedTransaction]) -> list[RecurringGroup]:
    """Return detected recurring groups; mutates txn.is_recurring in-place."""
    debits = [t for t in txns if t.txn_type == "debit"]

    # Group by canonical key (normalised description)
    buckets: dict[str, list[CleanedTransaction]] = defaultdict(list)
    for txn in debits:
        key = _canonical_key(txn)
        buckets[key].append(txn)

    groups: list[RecurringGroup] = []
    for _, members in buckets.items():
        if len(members) < 2:
            continue

        amounts = [abs(t.amount) for t in members]
        avg_amount = sum(amounts) / len(amounts)

        # Require all amounts within ±10% of average
        if not all(abs(a - avg_amount) / avg_amount <= 0.10 for a in amounts):
            continue

        members.sort(key=lambda t: t.date)
        frequency = _infer_frequency(members)

        for txn in members:
            txn.__dict__["is_recurring"] = True

        grp = RecurringGroup(
            id=str(uuid.uuid4()),
            label=_best_label(members),
            category=getattr(members[0], "category", "Other"),
            amount=-avg_amount,          # store as negative (debit convention)
            frequency=frequency,
            occurrence_count=len(members),
            last_seen=members[-1].date,
            transaction_ids=[id(t) for t in members],  # python object ids for in-memory linking
        )
        groups.append(grp)

    return groups


def _canonical_key(txn: CleanedTransaction) -> str:
    """Normalise description to a stable grouping key."""
    if txn.merchant:
        return txn.merchant.upper()
    s = txn.description_clean.upper()
    # strip amounts/dates embedded in description
    s = re.sub(r"\d{2,}", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:60]   # cap length


def _infer_frequency(members: list[CleanedTransaction]) -> str:
    if len(members) < 2:
        return "irregular"
    from datetime import date as dt_date
    dates = [dt_date.fromisoformat(t.date) for t in members]
    gaps = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
    avg_gap = sum(gaps) / len(gaps)
    if 25 <= avg_gap <= 35:
        return "monthly"
    if 6 <= avg_gap <= 8:
        return "weekly"
    return "irregular"


def _best_label(members: list[CleanedTransaction]) -> str:
    if members[0].merchant:
        return members[0].merchant
    return members[0].description_clean[:60]
