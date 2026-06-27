from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.models.db import Transaction, AnalysisResult, RecurringGroup
from app.models.schemas import (
    SessionStatus,
    TransactionOut,
    TransactionPage,
    Metrics,
    CategoryBreakdown,
    MonthlyBreakdown,
    InsightsOut,
    RecurringGroupOut,
)
from app.services.database import get_db
from app.services import session as session_svc

router = APIRouter(tags=["sessions"])


def _get_session_or_404(db: Session, session_id: str):
    s = session_svc.get_session(db, session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return s


# ── Session status ─────────────────────────────────────────────────────────────

@router.get("/sessions/{session_id}", response_model=SessionStatus)
def get_session(session_id: str, db: Session = Depends(get_db)):
    s = _get_session_or_404(db, session_id)
    return SessionStatus(
        id=s.id,
        filename=s.filename,
        status=s.status,
        row_count=s.row_count,
        warnings=s.warnings,
        error_message=s.error_message,
    )


# ── Transactions ───────────────────────────────────────────────────────────────

@router.get("/sessions/{session_id}/transactions", response_model=TransactionPage)
def get_transactions(
    session_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    _get_session_or_404(db, session_id)

    total = db.query(Transaction).filter(Transaction.session_id == session_id).count()
    items = (
        db.query(Transaction)
        .filter(Transaction.session_id == session_id)
        .order_by(Transaction.date)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return TransactionPage(
        items=[TransactionOut.model_validate(t) for t in items],
        total=total,
        page=page,
        page_size=page_size,
    )


# ── Analytics ──────────────────────────────────────────────────────────────────

@router.get("/sessions/{session_id}/analytics", response_model=Metrics)
def get_analytics(session_id: str, db: Session = Depends(get_db)):
    _get_session_or_404(db, session_id)

    analysis = db.query(AnalysisResult).filter(AnalysisResult.session_id == session_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not ready")

    m = analysis.metrics
    return Metrics(
        total_income=m["total_income"],
        total_spend=m["total_spend"],
        savings=m["savings"],
        savings_rate=m.get("savings_rate"),
        top_categories=[
            CategoryBreakdown(**c) for c in m.get("top_categories", [])
        ],
        biggest_debit_amount=m.get("biggest_debit_amount"),
        biggest_debit_merchant=m.get("biggest_debit_merchant"),
        biggest_debit_date=m.get("biggest_debit_date"),
        period_start=m.get("period_start"),
        period_end=m.get("period_end"),
        recurring_total=m.get("recurring_total", 0.0),
        monthly_breakdown=[
            MonthlyBreakdown(**mb) for mb in m.get("monthly_breakdown", [])
        ],
        llm_categorized=m.get("llm_categorized", 0),
    )


# ── Insights ───────────────────────────────────────────────────────────────────

@router.get("/sessions/{session_id}/insights", response_model=InsightsOut)
def get_insights(session_id: str, db: Session = Depends(get_db)):
    _get_session_or_404(db, session_id)

    analysis = db.query(AnalysisResult).filter(AnalysisResult.session_id == session_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not ready")

    return InsightsOut(insights=analysis.insights or [])


# ── Recurring ──────────────────────────────────────────────────────────────────

@router.get("/sessions/{session_id}/recurring", response_model=list[RecurringGroupOut])
def get_recurring(session_id: str, db: Session = Depends(get_db)):
    _get_session_or_404(db, session_id)

    groups = (
        db.query(RecurringGroup)
        .filter(RecurringGroup.session_id == session_id)
        .order_by(RecurringGroup.amount)   # most expensive first (amount is negative)
        .all()
    )
    return [RecurringGroupOut.model_validate(g) for g in groups]


# ── Delete session ─────────────────────────────────────────────────────────────

@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(session_id: str, db: Session = Depends(get_db)):
    s = _get_session_or_404(db, session_id)
    db.delete(s)
    db.commit()
    return Response(status_code=204)

