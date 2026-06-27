"""Pipeline orchestrator: parse → clean → categorize → recurring → metrics → insights → persist."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.db import Transaction, AnalysisResult, RecurringGroup as DBRecurringGroup, SavingsRecommendation
from app.parsers.registry import parse_file
from app.pipeline.cleaner import clean, CleanedTransaction
from app.pipeline.categorizer import categorize
from app.pipeline.recurring import detect as detect_recurring, RecurringGroup as PipelineRecurringGroup
from app.pipeline.metrics import compute
from app.pipeline.insights import generate
from app.pipeline.recommendations import compute as compute_recommendations
from app.services import session as session_svc


def run(db: Session, session_id: str, filename: str, content: bytes) -> tuple[int, list[str], int]:
    """Run the full pipeline. Returns (row_count, warnings, llm_categorized)."""
    all_warnings: list[str] = []

    # 1. Parse
    parse_result = parse_file(filename, content)
    all_warnings.extend(parse_result.warnings)

    if not parse_result.transactions:
        session_svc.update_status(db, session_id, "failed",
                                  error_message="; ".join(all_warnings) or "No transactions found")
        return 0, all_warnings, 0

    # 2. Clean
    clean_result = clean(parse_result.transactions)
    all_warnings.extend(clean_result.warnings)

    if not clean_result.transactions:
        session_svc.update_status(db, session_id, "failed",
                                  error_message="No valid transactions after cleaning")
        return 0, all_warnings, 0

    # 3. Categorize (rules + LLM fallback)
    txns: list[CleanedTransaction]
    txns, llm_count = categorize(clean_result.transactions)

    # 4. Detect recurring payments (mutates txn.is_recurring in-place)
    recurring_groups = detect_recurring(txns)

    # 5. Build a lookup from python object id → recurring_group
    obj_id_to_group: dict[int, PipelineRecurringGroup] = {}
    for grp in recurring_groups:
        for oid in grp.transaction_ids:
            obj_id_to_group[oid] = grp

    # 6. Persist recurring groups first (need IDs for transaction FK)
    group_id_map: dict[str, str] = {}   # recurring.id → db_group.id
    for grp in recurring_groups:
        db_grp = DBRecurringGroup(
            id=grp.id,
            session_id=session_id,
            label=grp.label,
            category=grp.category,
            amount=grp.amount,
            frequency=grp.frequency,
            occurrence_count=grp.occurrence_count,
            last_seen=grp.last_seen,
        )
        db.add(db_grp)
        group_id_map[grp.id] = grp.id
    db.flush()

    # 7. Persist transactions
    db_txns = []
    for t in txns:
        grp = obj_id_to_group.get(id(t))
        db_txns.append(Transaction(
            id=str(uuid.uuid4()),
            session_id=session_id,
            date=t.date,
            description_raw=t.description_raw,
            description_clean=t.description_clean,
            amount=t.amount,
            txn_type=t.txn_type,
            balance=t.balance,
            category=getattr(t, "category", "Other"),
            category_confidence=getattr(t, "category_confidence", 0.0),
            category_source=getattr(t, "category_source", "rule"),
            is_recurring=getattr(t, "is_recurring", False),
            recurring_group_id=grp.id if grp else None,
            merchant=t.merchant,
            needs_wants=getattr(t, "needs_wants", None),
        ))
    db.add_all(db_txns)
    db.flush()

    # 8. Metrics
    metrics = compute(txns, llm_categorized=llm_count)

    # 9. Insights
    insight_texts = generate(metrics, recurring_groups)

    # 10. Persist analysis
    analysis = AnalysisResult(
        id=str(uuid.uuid4()),
        session_id=session_id,
        metrics={
            "total_income": metrics.total_income,
            "total_spend": metrics.total_spend,
            "savings": metrics.savings,
            "savings_rate": metrics.savings_rate,
            "top_categories": [
                {"category": c.category, "total": c.total, "count": c.count}
                for c in metrics.top_categories
            ],
            "biggest_debit_amount": metrics.biggest_debit_amount,
            "biggest_debit_merchant": metrics.biggest_debit_merchant,
            "biggest_debit_date": metrics.biggest_debit_date,
            "period_start": metrics.period_start,
            "period_end": metrics.period_end,
            "recurring_total": metrics.recurring_total,
            "monthly_breakdown": [
                {"month": m.month, "income": m.income, "spend": m.spend}
                for m in metrics.monthly_breakdown
            ],
            "llm_categorized": llm_count,
            "needs_total": metrics.needs_total,
            "wants_total": metrics.wants_total,
        },
        insights=insight_texts,
    )
    db.add(analysis)

    # 11. Savings recommendations
    rec_result = compute_recommendations(txns, metrics)
    db_rec = SavingsRecommendation(
        id=str(uuid.uuid4()),
        session_id=session_id,
        salary_monthly=rec_result.salary_monthly,
        wants_budget_pct=rec_result.wants_budget_pct,
        wants_budget=rec_result.wants_budget,
        wants_actual=rec_result.wants_actual,
        needs_actual=rec_result.needs_actual,
        is_over_budget=rec_result.is_over_budget,
        recommendations=[
            {
                "category": r.category,
                "amount_spent": r.amount_spent,
                "suggested_cap": r.suggested_cap,
                "potential_saving": r.potential_saving,
                "top_merchants": r.top_merchants,
                "suggestion_text": r.suggestion_text,
            }
            for r in rec_result.recommendations
        ],
        summary=rec_result.summary,
    )
    db.add(db_rec)

    # 12. Update session
    session_svc.update_status(db, session_id, "ready",
                              row_count=len(db_txns),
                              warnings=all_warnings)
    db.commit()

    return len(db_txns), all_warnings, llm_count

