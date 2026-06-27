"""ICICI Bank CSV parser.

Handles standard ICICI bank statement CSV exports:
  S No., Value Date, Transaction Remarks, Withdrawal Amount (INR ), Deposit Amount (INR ), Balance (INR )
"""

from __future__ import annotations

import io

import pandas as pd

from app.parsers.base import ParseResult, RawTransaction
from app.parsers.hdfc import _read_csv_with_preamble, _to_float, _match

_DATE_COLS = {"value date", "date", "txn date", "transaction date"}
_DESC_COLS = {"transaction remarks", "remarks", "narration", "description", "particulars"}
_DEBIT_COLS = {"withdrawal amount (inr )", "withdrawal amount (inr)", "withdrawal amt.", "withdrawal", "debit", "dr"}
_CREDIT_COLS = {"deposit amount (inr )", "deposit amount (inr)", "deposit amt.", "deposit", "credit", "cr"}
_BAL_COLS = {"balance (inr )", "balance (inr)", "closing balance", "balance", "running balance"}


class IciciParser:
    def can_parse(self, filename: str, content: bytes) -> bool:
        if not filename.lower().endswith(".csv"):
            return False
        sample = content[:1024].decode("utf-8", errors="ignore").lower()
        return "transaction remarks" in sample and (
            "withdrawal amount (inr" in sample or "deposit amount (inr" in sample
        )

    def parse(self, content: bytes) -> ParseResult:
        warnings: list[str] = []

        df = _read_csv_with_preamble(content, warnings)
        if df is None or df.empty:
            return ParseResult([], warnings + ["No rows found in file"])

        cols = list(df.columns)
        date_col = _match(cols, _DATE_COLS)
        desc_col = _match(cols, _DESC_COLS)
        debit_col = _match(cols, _DEBIT_COLS)
        credit_col = _match(cols, _CREDIT_COLS)
        bal_col = _match(cols, _BAL_COLS)

        if not date_col:
            return ParseResult([], warnings + ["Could not detect date column"])
        if not desc_col:
            return ParseResult([], warnings + ["Could not detect description/remarks column"])
        if not debit_col and not credit_col:
            return ParseResult([], warnings + ["Could not detect debit or credit columns"])

        txns: list[RawTransaction] = []
        skipped = 0

        for _, row in df.iterrows():
            raw_date = str(row[date_col]).strip() if date_col else ""
            raw_desc = str(row[desc_col]).strip() if desc_col else ""
            debit = _to_float(row[debit_col]) if debit_col else None
            credit = _to_float(row[credit_col]) if credit_col else None
            balance = _to_float(row[bal_col]) if bal_col else None

            if not raw_date or raw_date in ("nan", "NaT"):
                skipped += 1
                continue
            if debit is None and credit is None:
                skipped += 1
                continue

            txns.append(RawTransaction(
                date_raw=raw_date,
                description_raw=raw_desc,
                debit=debit,
                credit=credit,
                balance=balance,
            ))

        if skipped:
            warnings.append(f"Skipped {skipped} rows (missing date or amount)")

        return ParseResult(txns, warnings)
