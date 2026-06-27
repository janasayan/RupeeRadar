"""Recommendations API routes — Phase 2.5."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models.db import Transaction, AnalysisResult, SavingsRecommendation
from app.models.schemas import RecommendationsOut, RecommendationItem, RecommendationSettingsRequest
from app.services.database import get_db
from app.services import session as session_svc
from app.pipeline.cleaner import CleanedTransaction
from app.pipeline.recommendations import compute as compute_recommendations
from app.pipeline.metrics import Metrics, CategoryBreakdown, MonthlyBreakdown

router = APIRouter(tags=["recommendations"])


def _get_session_or_404(db: Session, session_id: str):
    s = session_svc.get_session(db, session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return s


def _load_rec_or_404(db: Session, session_id: str) -> SavingsRecommendation:
    rec = db.query(SavingsRecommendation).filter(
        SavingsRecommendation.session_id == session_id
    ).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendations not ready")
    return rec


def _rec_to_schema(rec: SavingsRecommendation) -> RecommendationsOut:
    return RecommendationsOut(
        salary_monthly=rec.salary_monthly,
        wants_budget_pct=rec.wants_budget_pct,
        wants_budget=rec.wants_budget,
        wants_actual=rec.wants_actual,
        needs_actual=rec.needs_actual,
        is_over_budget=rec.is_over_budget,
        recommendations=[RecommendationItem(**r) for r in (rec.recommendations or [])],
        summary=rec.summary,
    )


@router.get("/sessions/{session_id}/recommendations", response_model=RecommendationsOut)
def get_recommendations(session_id: str, db: Session = Depends(get_db)):
    _get_session_or_404(db, session_id)
    return _rec_to_schema(_load_rec_or_404(db, session_id))


@router.patch("/sessions/{session_id}/recommendations/settings", response_model=RecommendationsOut)
def update_settings(
    session_id: str,
    body: RecommendationSettingsRequest,
    db: Session = Depends(get_db),
):
    _get_session_or_404(db, session_id)
    rec = _load_rec_or_404(db, session_id)

    salary = body.salary_monthly if body.salary_monthly is not None else rec.salary_monthly
    pct = body.wants_budget_pct if body.wants_budget_pct is not None else rec.wants_budget_pct

    # Re-run recommendations with new settings using raw transactions from DB
    db_txns = db.query(Transaction).filter(Transaction.session_id == session_id).all()
    analysis = db.query(AnalysisResult).filter(AnalysisResult.session_id == session_id).first()

    # Reconstruct lightweight CleanedTransaction-like objects from DB rows
    txns = [_db_txn_to_cleaned(t) for t in db_txns]

    m = analysis.metrics if analysis else {}
    metrics = Metrics(
        total_income=m.get("total_income", 0),
        total_spend=m.get("total_spend", 0),
        savings=m.get("savings", 0),
        savings_rate=m.get("savings_rate"),
        top_categories=[CategoryBreakdown(**c) for c in m.get("top_categories", [])],
        biggest_debit_amount=m.get("biggest_debit_amount"),
        biggest_debit_merchant=m.get("biggest_debit_merchant"),
        biggest_debit_date=m.get("biggest_debit_date"),
        period_start=m.get("period_start"),
        period_end=m.get("period_end"),
        recurring_total=m.get("recurring_total", 0),
        needs_total=m.get("needs_total", 0),
        wants_total=m.get("wants_total", 0),
    )

    result = compute_recommendations(txns, metrics, salary_monthly=salary, wants_budget_pct=pct)

    rec.salary_monthly = result.salary_monthly
    rec.wants_budget_pct = result.wants_budget_pct
    rec.wants_budget = result.wants_budget
    rec.wants_actual = result.wants_actual
    rec.needs_actual = result.needs_actual
    rec.is_over_budget = result.is_over_budget
    rec.recommendations = [
        {
            "category": r.category,
            "amount_spent": r.amount_spent,
            "suggested_cap": r.suggested_cap,
            "potential_saving": r.potential_saving,
            "top_merchants": r.top_merchants,
            "suggestion_text": r.suggestion_text,
        }
        for r in result.recommendations
    ]
    rec.summary = result.summary
    db.commit()
    db.refresh(rec)

    return _rec_to_schema(rec)


# ---------------------------------------------------------------------------
# Helper — reconstruct a duck-typed transaction from DB row
# ---------------------------------------------------------------------------

class _TxnProxy:
    """Minimal duck-type matching CleanedTransaction used by recommendations engine."""
    __slots__ = ("date", "amount", "txn_type", "category", "needs_wants", "merchant", "description_clean")

    def __init__(self, t: Transaction) -> None:
        self.date = t.date
        self.amount = t.amount
        self.txn_type = t.txn_type
        self.category = t.category
        self.needs_wants = t.needs_wants or "want"
        self.merchant = t.merchant
        self.description_clean = t.description_clean


def _db_txn_to_cleaned(t: Transaction) -> CleanedTransaction:  # type: ignore[return-value]
    return _TxnProxy(t)  # type: ignore[return-value]
