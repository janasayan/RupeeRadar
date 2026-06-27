"""Transaction-level operations — Phase 2: category override."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config.categories import CATEGORIES
from app.models.db import Transaction, AnalysisResult
from app.models.schemas import CategoryUpdateRequest, TransactionOut
from app.services.database import get_db
from app.services import session as session_svc

router = APIRouter(tags=["transactions"])


@router.patch(
    "/sessions/{session_id}/transactions/{transaction_id}",
    response_model=TransactionOut,
)
def update_category(
    session_id: str,
    transaction_id: str,
    body: CategoryUpdateRequest,
    db: Session = Depends(get_db),
):
    s = session_svc.get_session(db, session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Session not found")

    txn = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id, Transaction.session_id == session_id)
        .first()
    )
    if txn is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if body.category not in CATEGORIES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid category. Must be one of: {', '.join(CATEGORIES)}",
        )

    txn.category = body.category
    txn.category_source = "user"
    txn.category_confidence = 1.0

    # Recompute metrics stored in AnalysisResult
    _recompute_metrics(db, session_id)

    db.commit()
    db.refresh(txn)
    return TransactionOut.model_validate(txn)


def _recompute_metrics(db: Session, session_id: str) -> None:
    """Update category breakdown in the stored AnalysisResult after an override."""
    from collections import defaultdict

    analysis = db.query(AnalysisResult).filter(AnalysisResult.session_id == session_id).first()
    if not analysis:
        return

    all_txns = (
        db.query(Transaction)
        .filter(Transaction.session_id == session_id)
        .all()
    )

    cat_totals: dict[str, float] = defaultdict(float)
    cat_counts: dict[str, int] = defaultdict(int)
    for t in all_txns:
        if t.txn_type == "debit" and t.category != "Salary":
            cat_totals[t.category] += abs(t.amount)
            cat_counts[t.category] += 1

    top_categories = sorted(
        [{"category": cat, "total": round(tot, 2), "count": cat_counts[cat]}
         for cat, tot in cat_totals.items()],
        key=lambda x: x["total"],
        reverse=True,
    )

    metrics = dict(analysis.metrics)
    metrics["top_categories"] = top_categories
    analysis.metrics = metrics
