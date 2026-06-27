"""HDFC CSV parser.

Handles standard HDFC bank statement CSV exports:
  Date, Narration, Withdrawal Amt., Deposit Amt., Closing Balance
"""

from __future__ import annotations

import io

import pandas as pd

from app.parsers.base import ParseResult, RawTransaction

# Possible column name variants (normalised to lower-strip)
_DATE_COLS = {"date", "txn date", "transaction date", "value date"}
_DESC_COLS = {"narration", "description", "particulars", "details", "remarks"}
_DEBIT_COLS = {"withdrawal amt.", "withdrawal", "debit", "dr", "debit amount", "debit amt"}
_CREDIT_COLS = {"deposit amt.", "deposit", "credit", "cr", "credit amount", "credit amt"}
_BAL_COLS = {"closing balance", "balance", "running balance"}


def _match(cols: list[str], targets: set[str]) -> str | None:
    for c in cols:
        if c.strip().lower() in targets:
            return c
    return None


def _to_float(val) -> float | None:
    if pd.isna(val):
        return None
    s = str(val).strip().replace(",", "").replace("₹", "").replace("Rs.", "").replace("INR", "")
    if not s or s in ("-", ""):
        return None
    try:
        return float(s)
    except ValueError:
        return None


class HdfcParser:
    def can_parse(self, filename: str, content: bytes) -> bool:
        name = filename.lower()
        if not name.endswith(".csv"):
            return False
        sample = content[:512].decode("utf-8", errors="ignore").lower()
        return any(kw in sample for kw in ("narration", "withdrawal amt", "deposit amt", "closing balance"))

    def parse(self, content: bytes) -> ParseResult:
        warnings: list[str] = []

        # Try reading — skip preamble lines before the header
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
            return ParseResult([], warnings + ["Could not detect description/narration column"])
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


def _read_csv_with_preamble(content: bytes, warnings: list[str]) -> pd.DataFrame | None:
    """Try multiple encodings and skip preamble lines before the header row."""
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        warnings.append("Could not decode file encoding")
        return None

    lines = text.splitlines()
    # Find header row by looking for a line containing known column keywords
    header_idx = 0
    for i, line in enumerate(lines):
        lower = line.lower()
        if any(kw in lower for kw in ("date", "narration", "withdrawal", "deposit")):
            header_idx = i
            break

    if header_idx > 0:
        warnings.append(f"Skipped {header_idx} preamble line(s)")

    csv_text = "\n".join(lines[header_idx:])
    try:
        return pd.read_csv(io.StringIO(csv_text))
    except Exception as e:
        warnings.append(f"CSV parse error: {e}")
        return None
