"""Needs vs wants classification for the 10 RupeeRadar categories."""

from __future__ import annotations

# Category → "need" | "want" | "income" | "neutral"
CATEGORY_TYPE: dict[str, str] = {
    "Salary":      "income",
    "EMI":         "need",
    "Rent":        "need",
    "Bills":       "need",
    "Investments": "need",     # treated as need — disciplined saving
    "Food":        "want",     # default; grocery merchants override to need below
    "Travel":      "want",
    "Shopping":    "want",
    "Subscriptions": "want",
    "Other":       "want",
}

# Merchants whose description_clean contains these keywords → Food but classified as NEED (grocery)
GROCERY_KEYWORDS = [
    "BLINKIT", "ZEPTO", "GROFERS", "BIG BAZAAR", "DMART", "BIGBASKET",
    "NATURE'S BASKET", "RELIANCE FRESH", "MORE SUPERMARKET", "SPENCERS",
]

# Merchants that are Food but remain WANT (food delivery)
DELIVERY_KEYWORDS = [
    "SWIGGY", "ZOMATO", "DOMINOS", "DOMINO", "MCDONALDS", "KFC",
    "BURGER KING", "SUBWAY", "PIZZA HUT",
]


def classify_needs_wants(category: str, description_clean: str) -> str:
    """Return 'need', 'want', or 'income' for a transaction."""
    upper = description_clean.upper()

    if category == "Food":
        for kw in GROCERY_KEYWORDS:
            if kw in upper:
                return "need"
        return "want"

    return CATEGORY_TYPE.get(category, "want")
