"""Generic CSV/XLSX parser — last-resort fallback for unrecognized bank formats.

Attempts to auto-detect standard column names (date, description, debit/credit, balance).
Supports both .csv and .xlsx files.
"""

from __future__ import annotations

import io

import pandas as pd

from app.parsers.base import ParseResult, RawTransaction
from app.parsers.hdfc import _read_csv_with_preamble, _to_float, _match

_DATE_COLS = {"date", "txn date", "transaction date", "value date", "posting date"}
_DESC_COLS = {"narration", "description", "particulars", "details", "remarks", "transaction remarks", "reference"}
_DEBIT_COLS = {"withdrawal amt.", "withdrawal amount (inr )", "withdrawal amount (inr)", "withdrawal", "debit", "dr", "debit amount", "debit amt"}
_CREDIT_COLS = {"deposit amt.", "deposit amount (inr )", "deposit amount (inr)", "deposit", "credit", "cr", "credit amount", "credit amt"}
_BAL_COLS = {"closing balance", "balance (inr )", "balance (inr)", "balance", "running balance", "available balance"}


class GenericCsvParser:
    """Fallback parser for any CSV or XLSX with recognizable column headers."""

    def can_parse(self, filename: str, content: bytes) -> bool:
        name = filename.lower()
        return name.endswith(".csv") or name.endswith(".xlsx")

    def parse(self, content: bytes) -> ParseResult:
        warnings: list[str] = []

        filename_hint = getattr(content, "_filename", "")
        is_xlsx = isinstance(content, (bytes,)) and content[:4] == b"PK\x03\x04"

        if is_xlsx:
            df = self._read_xlsx(content, warnings)
        else:
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
            return ParseResult([], warnings + [
                "Could not auto-detect date column. "
                "Please use an HDFC or ICICI CSV export, or rename your columns to standard names (Date, Narration, Withdrawal Amt., Deposit Amt., Closing Balance)."
            ])
        if not desc_col:
            return ParseResult([], warnings + ["Could not auto-detect description column"])
        if not debit_col and not credit_col:
            return ParseResult([], warnings + ["Could not auto-detect debit or credit columns"])

        warnings.append("Parsed using generic column detection — verify categories look correct")

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

    def _read_xlsx(self, content: bytes, warnings: list[str]) -> pd.DataFrame | None:
        try:
            return pd.read_excel(io.BytesIO(content))
        except Exception as e:
            warnings.append(f"Excel parse error: {e}")
            return None
