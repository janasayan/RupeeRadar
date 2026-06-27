"""Parser protocol — all bank parsers implement this interface."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol


@dataclass
class RawTransaction:
    date_raw: str
    description_raw: str
    debit: Optional[float]
    credit: Optional[float]
    balance: Optional[float]


@dataclass
class ParseResult:
    transactions: list[RawTransaction]
    warnings: list[str] = field(default_factory=list)


class StatementParser(Protocol):
    def can_parse(self, filename: str, content: bytes) -> bool: ...
    def parse(self, content: bytes) -> ParseResult: ...
