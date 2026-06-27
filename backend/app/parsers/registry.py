"""Parser registry — selects the right parser for a given file."""

from __future__ import annotations

from typing import Optional

from app.parsers.base import ParseResult, StatementParser
from app.parsers.hdfc import HdfcParser
from app.parsers.icici import IciciParser
from app.parsers.generic import GenericCsvParser

_PARSERS: list[StatementParser] = [
    HdfcParser(),
    IciciParser(),
    GenericCsvParser(),
]


def get_parser(filename: str, content: bytes) -> Optional[StatementParser]:
    for parser in _PARSERS:
        if parser.can_parse(filename, content):
            return parser
    return None


def parse_file(filename: str, content: bytes) -> ParseResult:
    parser = get_parser(filename, content)
    if parser is None:
        return ParseResult(
            [],
            [f"Unsupported file format: '{filename}'. Try a CSV export from your bank."],
        )
    return parser.parse(content)
