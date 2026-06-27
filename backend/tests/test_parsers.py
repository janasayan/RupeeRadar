"""Tests for ICICI/generic parsers and Phase 3 API endpoints (report, delete)."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.parsers.icici import IciciParser
from app.parsers.generic import GenericCsvParser
from app.parsers.registry import parse_file

client = TestClient(app)

# ── ICICI fixtures ────────────────────────────────────────────────────────────

ICICI_CSV = b"""S No.,Value Date,Transaction Remarks,Withdrawal Amount (INR ),Deposit Amount (INR ),Balance (INR )
1,01/03/2025,UPI/P2M/SWIGGY FOOD ORDER,450.00,,48550.00
2,03/03/2025,NEFT/SALARY ACME CORP,,75000.00,123550.00
3,05/03/2025,BILLPAY/NETFLIX SUBSCRIPTION,649.00,,122901.00
4,10/03/2025,UPI/DR/UBER TRIP MUMBAI,285.00,,122616.00
5,12/03/2025,NACH/DR/HOME LOAN EMI,8500.00,,114116.00
"""

ICICI_CSV_SHORT = b"""Value Date,Transaction Remarks,Withdrawal Amount (INR ),Deposit Amount (INR ),Balance (INR )
01-03-2025,UPI SWIGGY,500.00,,9500.00
"""

# ── Generic CSV fixture ───────────────────────────────────────────────────────

GENERIC_CSV = b"""Date,Narration,Debit,Credit,Balance
2025-03-01,SWIGGY ORDER,450.00,,48550.00
2025-03-03,SALARY CREDIT,,75000.00,123550.00
"""

GENERIC_CSV_UNRECOGNIZED = b"""col1,col2,col3
foo,bar,baz
"""


# ── ICICI parser tests ────────────────────────────────────────────────────────

def test_icici_can_parse():
    parser = IciciParser()
    assert parser.can_parse("icici_statement.csv", ICICI_CSV)
    assert not parser.can_parse("icici_statement.pdf", ICICI_CSV)
    assert not parser.can_parse("hdfc.csv", b"Date,Narration,Withdrawal Amt.,Deposit Amt.,Closing Balance\n")


def test_icici_parser_row_count():
    parser = IciciParser()
    result = parser.parse(ICICI_CSV)
    assert len(result.transactions) == 5
    assert result.warnings == []


def test_icici_parser_amounts():
    parser = IciciParser()
    result = parser.parse(ICICI_CSV)
    salary = next(t for t in result.transactions if t.credit and t.credit > 0)
    assert salary.credit == pytest.approx(75000.0)
    swiggy = result.transactions[0]
    assert swiggy.debit == pytest.approx(450.0)


def test_icici_via_registry():
    result = parse_file("icici_statement.csv", ICICI_CSV)
    assert len(result.transactions) == 5
    assert not any("Unsupported" in w for w in result.warnings)


# ── Generic parser tests ──────────────────────────────────────────────────────

def test_generic_can_parse_csv():
    parser = GenericCsvParser()
    assert parser.can_parse("unknown_bank.csv", GENERIC_CSV)
    assert parser.can_parse("statement.xlsx", b"PK\x03\x04fakexlsxcontent")


def test_generic_parser_row_count():
    parser = GenericCsvParser()
    result = parser.parse(GENERIC_CSV)
    assert len(result.transactions) == 2


def test_generic_parser_warns_on_unrecognized_columns():
    parser = GenericCsvParser()
    result = parser.parse(GENERIC_CSV_UNRECOGNIZED)
    assert len(result.transactions) == 0
    assert any("auto-detect" in w.lower() or "date column" in w.lower() for w in result.warnings)


def test_generic_via_registry_fallback():
    result = parse_file("mystery_bank.csv", GENERIC_CSV)
    assert len(result.transactions) == 2
    assert not any("Unsupported" in w for w in result.warnings)


# ── Report endpoint tests ─────────────────────────────────────────────────────

def test_report_unknown_session_returns_404():
    response = client.get("/api/v1/sessions/nonexistent-session-id/report")
    assert response.status_code == 404


def test_report_returns_html_for_valid_session():
    """Upload a statement, then fetch the report and check it's valid HTML."""
    HDFC_CSV = (
        b"Date,Narration,Withdrawal Amt.,Deposit Amt.,Closing Balance\n"
        b"01-03-2025,UPI-SWIGGY,450.00,,48550.00\n"
        b"03-03-2025,NEFT CR-SALARY,,75000.00,123550.00\n"
    )

    upload_resp = client.post(
        "/api/v1/upload",
        files={"file": ("hdfc_test.csv", HDFC_CSV, "text/csv")},
    )
    assert upload_resp.status_code == 200
    session_id = upload_resp.json()["session_id"]

    report_resp = client.get(f"/api/v1/sessions/{session_id}/report")
    assert report_resp.status_code == 200
    assert "text/html" in report_resp.headers["content-type"]
    body = report_resp.text
    assert "RupeeRadar" in body
    assert "₹" in body


# ── DELETE session tests ──────────────────────────────────────────────────────

def test_delete_unknown_session_returns_404():
    response = client.delete("/api/v1/sessions/nonexistent-id")
    assert response.status_code == 404


def test_delete_session_removes_data():
    HDFC_CSV = (
        b"Date,Narration,Withdrawal Amt.,Deposit Amt.,Closing Balance\n"
        b"01-03-2025,UPI-SWIGGY,450.00,,48550.00\n"
        b"03-03-2025,NEFT CR-SALARY,,75000.00,123550.00\n"
    )

    upload_resp = client.post(
        "/api/v1/upload",
        files={"file": ("hdfc_del_test.csv", HDFC_CSV, "text/csv")},
    )
    assert upload_resp.status_code == 200
    session_id = upload_resp.json()["session_id"]

    # Confirm it exists
    assert client.get(f"/api/v1/sessions/{session_id}").status_code == 200

    # Delete it
    delete_resp = client.delete(f"/api/v1/sessions/{session_id}")
    assert delete_resp.status_code == 204

    # Confirm it's gone
    assert client.get(f"/api/v1/sessions/{session_id}").status_code == 404
