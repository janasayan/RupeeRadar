import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, ForeignKey, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class UploadSession(Base):
    __tablename__ = "upload_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    filename: Mapped[str] = mapped_column(String(255))
    file_type: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    row_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    warnings: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    transactions: Mapped[list["Transaction"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    analysis: Mapped[Optional["AnalysisResult"]] = relationship(back_populates="session", cascade="all, delete-orphan", uselist=False)
    recurring_groups: Mapped[list["RecurringGroup"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    savings_recommendation: Mapped[Optional["SavingsRecommendation"]] = relationship(back_populates="session", cascade="all, delete-orphan", uselist=False)


class RecurringGroup(Base):
    __tablename__ = "recurring_groups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("upload_sessions.id"))
    label: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(30))
    amount: Mapped[float] = mapped_column(Float)          # typical amount (negative = debit)
    frequency: Mapped[str] = mapped_column(String(20))    # "monthly" | "weekly" | "irregular"
    occurrence_count: Mapped[int] = mapped_column(Integer)
    last_seen: Mapped[str] = mapped_column(String(10))    # YYYY-MM-DD

    session: Mapped["UploadSession"] = relationship(back_populates="recurring_groups")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="recurring_group")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("upload_sessions.id"))
    date: Mapped[str] = mapped_column(String(10))
    description_raw: Mapped[str] = mapped_column(Text)
    description_clean: Mapped[str] = mapped_column(Text)
    amount: Mapped[float] = mapped_column(Float)
    txn_type: Mapped[str] = mapped_column(String(10))
    balance: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    category: Mapped[str] = mapped_column(String(30), default="Other")
    category_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    category_source: Mapped[str] = mapped_column(String(10), default="rule")  # "rule" | "llm" | "user"
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    recurring_group_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("recurring_groups.id"), nullable=True)
    merchant: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    needs_wants: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # "need" | "want" | "income"

    session: Mapped["UploadSession"] = relationship(back_populates="transactions")
    recurring_group: Mapped[Optional["RecurringGroup"]] = relationship(back_populates="transactions")


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("upload_sessions.id"), unique=True)
    metrics: Mapped[dict] = mapped_column(JSON)
    insights: Mapped[list] = mapped_column(JSON)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    session: Mapped["UploadSession"] = relationship(back_populates="analysis")


class SavingsRecommendation(Base):
    __tablename__ = "savings_recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("upload_sessions.id"), unique=True)
    salary_monthly: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    wants_budget_pct: Mapped[float] = mapped_column(Float, default=30.0)
    wants_budget: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    wants_actual: Mapped[float] = mapped_column(Float, default=0.0)
    needs_actual: Mapped[float] = mapped_column(Float, default=0.0)
    is_over_budget: Mapped[bool] = mapped_column(Boolean, default=False)
    recommendations: Mapped[list] = mapped_column(JSON, default=list)
    summary: Mapped[str] = mapped_column(Text, default="")
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    session: Mapped["UploadSession"] = relationship(back_populates="savings_recommendation")
