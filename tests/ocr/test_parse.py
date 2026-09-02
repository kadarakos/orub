from orub.ocr.parse import parse_catno


def test_parse_catno_strips_surrounding_whitespace() -> None:
    assert parse_catno("  XL152  \n") == "XL152"


def test_parse_catno_collapses_internal_whitespace_and_newlines() -> None:
    assert parse_catno("SBTRKT\n002") == "SBTRKT 002"


def test_parse_catno_empty_string_is_none() -> None:
    assert parse_catno("") is None


def test_parse_catno_whitespace_only_is_none() -> None:
    assert parse_catno("   \n\n  ") is None
