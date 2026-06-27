from __future__ import annotations

from typing import Optional, List
from pydantic import BaseModel, Field


class SessionStatus(BaseModel):
    id: str
    filename: str
    status: str
    row_count: Optional[int] = None
    warnings: Optional[List[str]] = None
    error_message: Optional[str] = None


class TransactionOut(BaseModel):
    id: str
    date: str
    description_raw: str
    description_clean: str
    amount: float
    txn_type: str
    balance: Optional[float]
    category: str
    category_confidence: float
    category_source: str = "rule"
    is_recurring: bool = False
    merchant: Optional[str]
    needs_wants: Optional[str] = None

    model_config = {"from_attributes": True}


class TransactionPage(BaseModel):
    items: List[TransactionOut]
    total: int
    page: int
    page_size: int


class CategoryUpdateRequest(BaseModel):
    category: str


class CategoryBreakdown(BaseModel):
    category: str
    total: float
    count: int


class MonthlyBreakdown(BaseModel):
    month: str        # "YYYY-MM"
    income: float
    spend: float


class RecurringGroupOut(BaseModel):
    id: str
    label: str
    category: str
    amount: float
    frequency: str
    occurrence_count: int
    last_seen: str

    model_config = {"from_attributes": True}


class Metrics(BaseModel):
    total_income: float
    total_spend: float
    savings: float
    savings_rate: Optional[float] = None
    top_categories: List[CategoryBreakdown]
    biggest_debit_amount: Optional[float] = None
    biggest_debit_merchant: Optional[str] = None
    biggest_debit_date: Optional[str] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    recurring_total: float = 0.0
    monthly_breakdown: List[MonthlyBreakdown] = Field(default_factory=list)
    llm_categorized: int = 0
    needs_total: float = 0.0
    wants_total: float = 0.0


class RecommendationItem(BaseModel):
    category: str
    amount_spent: float
    suggested_cap: float
    potential_saving: float
    top_merchants: List[str]
    suggestion_text: str


class RecommendationsOut(BaseModel):
    salary_monthly: Optional[float] = None
    wants_budget_pct: float = 30.0
    wants_budget: Optional[float] = None
    wants_actual: float
    needs_actual: float
    is_over_budget: bool
    recommendations: List[RecommendationItem] = Field(default_factory=list)
    summary: str


class RecommendationSettingsRequest(BaseModel):
    salary_monthly: Optional[float] = None
    wants_budget_pct: Optional[float] = None


class InsightsOut(BaseModel):
    insights: List[str]


class UploadResponse(BaseModel):
    session_id: str
    status: str
    row_count: Optional[int] = None
    warnings: List[str] = Field(default_factory=list)
    llm_categorized: int = 0
