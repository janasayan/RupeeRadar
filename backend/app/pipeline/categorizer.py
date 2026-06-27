"""Hybrid categorizer — rule-based first, LLM fallback for unmatched transactions."""

from __future__ import annotations

import json
import logging

from app.config.categories import CATEGORIES, classify
from app.config.needs_wants import classify_needs_wants
from app.pipeline.cleaner import CleanedTransaction

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a personal finance categorizer for Indian bank transactions.
Given a list of transactions, return a JSON array with one object per transaction in the same order.
Each object must have exactly: {"index": <int>, "category": <string>, "confidence": <float 0-1>}
Valid categories: Food, Travel, Shopping, Bills, EMI, Subscriptions, Salary, Rent, Investments, Other
Rules:
- Swiggy/Zomato → Food, Uber/Ola/IRCTC → Travel, Netflix/Spotify → Subscriptions
- NACH DR / EMI / LOAN → EMI, SIP/Zerodha/Groww → Investments
- SALARY/PAYROLL credits → Salary
- When unsure, use Other with confidence 0.4
Return ONLY the JSON array, no commentary."""


def categorize(txns: list[CleanedTransaction]) -> tuple[list[CleanedTransaction], int]:
    """Categorize transactions. Returns (txns, llm_count).

    Uses rules first; batches unmatched descriptions to LLM if available.
    """
    unmatched_indices: list[int] = []

    for i, txn in enumerate(txns):
        category, confidence, merchant = classify(txn.description_clean)
        txn.__dict__["category"] = category
        txn.__dict__["category_confidence"] = confidence
        txn.__dict__["category_source"] = "rule"
        txn.__dict__["needs_wants"] = classify_needs_wants(category, txn.description_clean)
        if merchant and not txn.merchant:
            txn.__dict__["merchant"] = merchant
        if category == "Other" and confidence == 0.0:
            unmatched_indices.append(i)

    llm_count = 0
    if unmatched_indices:
        llm_count = _llm_categorize(txns, unmatched_indices)

    return txns, llm_count


def _llm_categorize(txns: list[CleanedTransaction], indices: list[int]) -> int:
    """Send unmatched transactions to LLM in batches of 40. Returns count categorized."""
    from app.services.llm import llm_service

    if not llm_service.available:
        return 0

    # Batch size capped at 10 to stay within 1 K tokens/minute on llama-3.3-70b-versatile.
    total = 0
    batch_size = 10
    for batch_start in range(0, len(indices), batch_size):
        batch_indices = indices[batch_start: batch_start + batch_size]
        payload = [
            {
                "index": idx,
                "description": txns[idx].description_clean[:100],
                "amount": round(abs(txns[idx].amount), 2),
                "type": txns[idx].txn_type,
            }
            for idx in batch_indices
        ]
        try:
            raw = llm_service.complete(
                system_prompt=_SYSTEM_PROMPT,
                user_prompt=json.dumps(payload),
                temperature=0.1,
                estimated_tokens=800,  # ~10 txns × ~50 tokens input + ~250 tokens output
            )
            results: list[dict] = json.loads(raw)
            for item in results:
                idx = int(item["index"])
                cat = item.get("category", "Other")
                conf = float(item.get("confidence", 0.5))
                if cat not in CATEGORIES:
                    cat = "Other"
                    conf = 0.0
                if conf >= 0.6 and cat != "Other":
                    txns[idx].__dict__["category"] = cat
                    txns[idx].__dict__["category_confidence"] = conf
                    txns[idx].__dict__["category_source"] = "llm"
                    txns[idx].__dict__["needs_wants"] = classify_needs_wants(cat, txns[idx].description_clean)
                    total += 1
        except Exception as exc:
            logger.warning("LLM categorization batch failed: %s", exc)

    return total

