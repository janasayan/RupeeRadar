"""Cleaning & normalisation stage.

Converts RawTransaction → structured fields:
- Dates → ISO 8601 (YYYY-MM-DD)
- Amounts → signed float (debits negative)
- Descriptions → stripped UPI noise, merchant extracted
- Dedup via (date, amount, description_raw) hash
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime

from app.parsers.base import RawTransaction

# UPI noise patterns to strip
_UPI_PREFIX = re.compile(
    r"^(UPI[/-](?:DR|CR)[/-]\d+[/-]?|UPI[/-]|IMPS[/-]\d+[/-]?|NEFT\s+CR[-\s]|NACH[-\s]DR[-\s])",
    re.IGNORECASE,
)
_UPI_TRAILING_REF = re.compile(r"\d{6,}$")

_DATE_FORMATS = [
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%d-%m-%y",
    "%d/%m/%y",
    "%Y-%m-%d",
    "%d-%b-%Y",   # 01-Jun-2025
    "%d %b %Y",
]


@dataclass
class CleanedTransaction:
    date: str                  # YYYY-MM-DD
    description_raw: str
    description_clean: str
    amount: float              # negative = debit
    txn_type: str              # debit | credit
    balance: float | None
    merchant: str | None
    _hash: str = field(default="", repr=False)


@dataclass
class CleanResult:
    transactions: list[CleanedTransaction]
    warnings: list[str] = field(default_factory=list)


def clean(raw_txns: list[RawTransaction]) -> CleanResult:
    warnings: list[str] = []
    seen_hashes: set[str] = set()
    result: list[CleanedTransaction] = []
    dupe_count = 0

    for raw in raw_txns:
        # --- Date ---
        iso_date = _parse_date(raw.date_raw)
        if iso_date is None:
            warnings.append(f"Invalid date '{raw.date_raw}' — row skipped")
            continue

        # --- Amount & type ---
        if raw.debit is not None and raw.debit > 0:
            amount = -abs(raw.debit)
            txn_type = "debit"
        elif raw.credit is not None and raw.credit > 0:
            amount = abs(raw.credit)
            txn_type = "credit"
        else:
            warnings.append(f"Row on {iso_date} has no valid amount — skipped")
            continue

        # --- Clean description ---
        desc_clean, merchant = _clean_description(raw.description_raw)

        # --- Dedup ---
        h = _row_hash(iso_date, amount, raw.description_raw)
        if h in seen_hashes:
            dupe_count += 1
            continue
        seen_hashes.add(h)

        result.append(CleanedTransaction(
            date=iso_date,
            description_raw=raw.description_raw,
            description_clean=desc_clean,
            amount=amount,
            txn_type=txn_type,
            balance=raw.balance,
            merchant=merchant,
            _hash=h,
        ))

    if dupe_count:
        warnings.append(f"Removed {dupe_count} duplicate row(s)")

    return CleanResult(result, warnings)


def _parse_date(raw: str) -> str | None:
    raw = raw.strip()
    for fmt in _DATE_FORMATS:
        try:
            dt = datetime.strptime(raw, fmt)
            # 2-digit year: assume 2000s for 00-49, 1900s for 50-99
            if dt.year < 100:
                dt = dt.replace(year=dt.year + 2000 if dt.year < 50 else dt.year + 1900)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _clean_description(raw: str) -> tuple[str, str | None]:
    """Return (cleaned_description, merchant_label_or_None)."""
    s = raw.strip()

    # Strip UPI/NACH/NEFT prefix
    s = _UPI_PREFIX.sub("", s).strip()
    # Strip trailing numeric reference
    s = _UPI_TRAILING_REF.sub("", s).strip()
    # Normalise whitespace
    s = re.sub(r"\s+", " ", s).strip("-/ ").strip()

    merchant = _extract_merchant(s)
    return s or raw.strip(), merchant


_KNOWN_MERCHANTS: dict[str, str] = {
    "SWIGGY": "Swiggy",
    "ZOMATO": "Zomato",
    "DOMINOS": "Dominos",
    "DOMINO": "Dominos",
    "MCDONALDS": "McDonald's",
    "KFC": "KFC",
    "NETFLIX": "Netflix",
    "SPOTIFY": "Spotify",
    "AMAZON PRIME": "Amazon Prime",
    "AMAZON": "Amazon",
    "FLIPKART": "Flipkart",
    "UBER": "Uber",
    "OLA": "Ola",
    "RAPIDO": "Rapido",
    "IRCTC": "IRCTC",
    "MAKEMYTRIP": "MakeMyTrip",
    "ZERODHA": "Zerodha",
    "GROWW": "Groww",
    "BSE SIP": "BSE SIP",
    "NACH-DR": "Home Loan EMI",
    "HOME LOAN": "Home Loan",
    "BLINKIT": "Blinkit",
    "ZEPTO": "Zepto",
    "BIG BAZAAR": "Big Bazaar",
    "DMART": "D-Mart",
    "PHONEPE": "PhonePe",
    "PAYTM": "Paytm",
    "GPAY": "Google Pay",
    "BESCOM": "BESCOM",
    "ELECTRICITY": "Electricity Bill",
    "RENT": "Rent",
}


def _extract_merchant(s: str) -> str | None:
    upper = s.upper()
    # Longest match first to prefer "AMAZON PRIME" over "AMAZON"
    for key in sorted(_KNOWN_MERCHANTS, key=len, reverse=True):
        if key in upper:
            return _KNOWN_MERCHANTS[key]
    return None


def _row_hash(date: str, amount: float, desc_raw: str) -> str:
    payload = f"{date}|{amount:.2f}|{desc_raw.strip().lower()}"
    return hashlib.md5(payload.encode()).hexdigest()
