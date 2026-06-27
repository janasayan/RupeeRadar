"""Tests for HDFC parser and cleaning pipeline."""

import pytest

from app.parsers.hdfc import HdfcParser
from app.parsers.registry import parse_file
from app.pipeline.cleaner import clean, _parse_date
from app.pipeline.categorizer import categorize
from app.pipeline.metrics import compute
from app.pipeline.insights import generate

HDFC_CSV = b"""Date,Narration,Withdrawal Amt.,Deposit Amt.,Closing Balance
01-03-2025,UPI-SWIGGY-BANGALORE-987654321,450.00,,48550.00
02-03-2025,UPI/DR/123456/ZOMATO,680.00,,47870.00
03-03-2025,NEFT CR-SALARY ACME CORP,,75000.00,122870.00
05-03-2025,NETFLIX.COM MUMBAI,649.00,,122221.00
07-03-2025,UPI-AMAZON-IN-ORDER-998877,2499.00,,119722.00
10-03-2025,UBER TRIP MUMBAI,285.00,,119437.00
12-03-2025,NACH-DR-HOME LOAN EMI,8500.00,,110937.00
15-03-2025,UPI-SWIGGY-BANGALORE-987654321,450.00,,110487.00
25-03-2025,RENT-MARCH-TRANSFER,25000.00,,83808.00
28-03-2025,BSE SIP ZERODHA,5000.00,,78808.00
"""

DUPLICATE_CSV = b"""Date,Narration,Withdrawal Amt.,Deposit Amt.,Closing Balance
01-03-2025,UPI-SWIGGY-BANGALORE-987654321,450.00,,48550.00
01-03-2025,UPI-SWIGGY-BANGALORE-987654321,450.00,,48550.00
"""


# ── Parser tests ──────────────────────────────────────────────────────────────

def test_hdfc_parser_row_count():
    result = parse_file("hdfc_sample.csv", HDFC_CSV)
    assert len(result.transactions) == 10
    assert result.warnings == []


def test_hdfc_parser_can_parse():
    parser = HdfcParser()
    assert parser.can_parse("hdfc.csv", HDFC_CSV)
    assert not parser.can_parse("hdfc.pdf", HDFC_CSV)
    assert not parser.can_parse("random.csv", b"col1,col2\n1,2\n")


def test_registry_unsupported_format():
    result = parse_file("statement.txt", b"some data")
    assert len(result.transactions) == 0
    assert any("Unsupported" in w for w in result.warnings)


# ── Date normalisation tests ──────────────────────────────────────────────────

@pytest.mark.parametrize("raw,expected", [
    ("01-03-2025", "2025-03-01"),
    ("01/03/2025", "2025-03-01"),
    ("01-03-25",   "2025-03-01"),
    ("01-Jun-2025","2025-06-01"),
    ("2025-03-01", "2025-03-01"),
])
def test_date_normalisation(raw, expected):
    assert _parse_date(raw) == expected


def test_date_invalid_returns_none():
    assert _parse_date("32-13-2025") is None
    assert _parse_date("not-a-date") is None


# ── Cleaning tests ─────────────────────────────────────────────────────────────

def test_deduplication():
    result = parse_file("hdfc.csv", DUPLICATE_CSV)
    cleaned = clean(result.transactions)
    assert len(cleaned.transactions) == 1
    assert any("duplicate" in w.lower() for w in cleaned.warnings)


def test_upi_prefix_stripped():
    result = parse_file("hdfc.csv", HDFC_CSV)
    cleaned = clean(result.transactions)
    swiggy_txns = [t for t in cleaned.transactions if "Swiggy" in (t.merchant or "")]
    assert len(swiggy_txns) >= 1
    # Raw description preserved, clean has noise stripped
    raw = swiggy_txns[0].description_raw
    clean_desc = swiggy_txns[0].description_clean
    assert clean_desc != raw or "UPI" not in clean_desc


def test_debits_are_negative():
    result = parse_file("hdfc.csv", HDFC_CSV)
    cleaned = clean(result.transactions)
    for t in cleaned.transactions:
        if t.txn_type == "debit":
            assert t.amount < 0
        else:
            assert t.amount > 0


# ── Categorisation tests ──────────────────────────────────────────────────────

def test_categorisation_known_merchants():
    result = parse_file("hdfc.csv", HDFC_CSV)
    cleaned = clean(result.transactions)
    txns, _ = categorize(cleaned.transactions)
    cats = {t.description_clean.upper(): getattr(t, "category") for t in txns}

    swiggy = next(t for t in txns if "Swiggy" in (t.merchant or ""))
    assert getattr(swiggy, "category") == "Food"

    netflix = next(t for t in txns if "Netflix" in (t.merchant or "") or "NETFLIX" in t.description_clean.upper())
    assert getattr(netflix, "category") == "Subscriptions"

    salary = next(t for t in txns if t.txn_type == "credit")
    assert getattr(salary, "category") == "Salary"


def test_categorisation_emi():
    result = parse_file("hdfc.csv", HDFC_CSV)
    cleaned = clean(result.transactions)
    txns, _ = categorize(cleaned.transactions)
    emi = next((t for t in txns if "LOAN" in t.description_raw.upper() or "NACH" in t.description_raw.upper()), None)
    assert emi is not None
    assert getattr(emi, "category") == "EMI"


# ── Metrics tests ─────────────────────────────────────────────────────────────

def test_metrics_sum_correctly():
    result = parse_file("hdfc.csv", HDFC_CSV)
    cleaned = clean(result.transactions)
    txns, llm_count = categorize(cleaned.transactions)
    m = compute(txns)

    assert m.total_income == pytest.approx(75000.0)
    total_debits = sum(abs(t.amount) for t in cleaned.transactions if t.txn_type == "debit")
    assert m.total_spend == pytest.approx(total_debits)
    assert m.savings == pytest.approx(m.total_income - m.total_spend)


def test_metrics_have_top_category():
    result = parse_file("hdfc.csv", HDFC_CSV)
    cleaned = clean(result.transactions)
    txns, _ = categorize(cleaned.transactions)
    m = compute(txns)
    assert len(m.top_categories) > 0
    # sorted descending
    for i in range(len(m.top_categories) - 1):
        assert m.top_categories[i].total >= m.top_categories[i + 1].total


# ── Insights tests ────────────────────────────────────────────────────────────

def test_insights_minimum_three():
    result = parse_file("hdfc.csv", HDFC_CSV)
    cleaned = clean(result.transactions)
    txns, _ = categorize(cleaned.transactions)
    m = compute(txns)
    insights = generate(m)
    assert len(insights) >= 3


def test_insights_contain_amounts():
    result = parse_file("hdfc.csv", HDFC_CSV)
    cleaned = clean(result.transactions)
    txns, _ = categorize(cleaned.transactions)
    m = compute(txns)
    insights = generate(m)
    combined = " ".join(insights)
    assert "₹" in combined
