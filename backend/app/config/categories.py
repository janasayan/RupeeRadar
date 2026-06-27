"""Rule-based category assignment — Phase 1 deterministic tier."""

from __future__ import annotations

CATEGORIES = [
    "Food",
    "Travel",
    "Shopping",
    "Bills",
    "EMI",
    "Subscriptions",
    "Salary",
    "Rent",
    "Investments",
    "Other",
]

# keyword → (category, merchant_label)
# Rules are checked in order; first match wins.
RULES: list[tuple[list[str], str, str | None]] = [
    # Income
    (["SALARY", "PAYROLL", "NEFT CR-SALARY", "NEFT CR SALARY"], "Salary", None),
    # EMI / Loans
    (["HOME LOAN", "NACH-DR", "NACH DR", "EMI", "LOAN REPAY"], "EMI", None),
    # Rent
    (["RENT"], "Rent", None),
    # Investments
    (["SIP", "ZERODHA", "GROWW", "MUTUAL FUND", "BSE SIP", "NIFTY", "DEMAT"], "Investments", None),
    # Bills
    (["ELECTRICITY", "BESCOM", "BSES", "TATA POWER", "WATER BILL", "GAS BILL", "BILL PAYMENT", "UTILITY"], "Bills", None),
    # Subscriptions
    (["NETFLIX", "SPOTIFY", "AMAZON PRIME", "HOTSTAR", "YOUTUBE PREMIUM", "APPLE", "DISNEY"], "Subscriptions", None),
    # Food
    (["SWIGGY", "ZOMATO", "DOMINOS", "DOMINO", "MCDONALDS", "MCDONALD", "KFC", "BURGER KING",
      "SUBWAY", "PIZZA HUT", "BLINKIT", "ZEPTO", "BIG BAZAAR", "DMART", "GROFERS"], "Food", None),
    # Travel
    (["UBER", "OLA", "RAPIDO", "IRCTC", "MAKEMYTRIP", "GOIBIBO", "CLEARTRIP", "INDIGO",
      "SPICEJET", "AIR INDIA", "IXIGO", "REDBUS", "METRO"], "Travel", None),
    # Shopping
    (["AMAZON", "FLIPKART", "MYNTRA", "AJIO", "MEESHO", "NYKAA", "SHOPIFY"], "Shopping", None),
]

MERCHANT_LABELS: dict[str, str] = {
    "SWIGGY": "Swiggy",
    "ZOMATO": "Zomato",
    "DOMINOS": "Dominos",
    "NETFLIX": "Netflix",
    "SPOTIFY": "Spotify",
    "AMAZON PRIME": "Amazon Prime",
    "AMAZON": "Amazon",
    "UBER": "Uber",
    "OLA": "Ola",
    "IRCTC": "IRCTC",
    "MAKEMYTRIP": "MakeMyTrip",
    "ZERODHA": "Zerodha",
    "GROWW": "Groww",
    "BSE SIP": "BSE SIP",
    "NACH-DR": "Home Loan EMI",
}


def classify(description_clean: str) -> tuple[str, float, str | None]:
    """Return (category, confidence, merchant_label)."""
    upper = description_clean.upper()
    for keywords, category, label in RULES:
        for kw in keywords:
            if kw in upper:
                merchant = label or _extract_merchant(upper)
                return category, 1.0, merchant
    return "Other", 0.0, None


def _extract_merchant(upper: str) -> str | None:
    for key, label in MERCHANT_LABELS.items():
        if key in upper:
            return label
    return None
