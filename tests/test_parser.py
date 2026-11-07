import pytest

from app.parser import ParseError, parse_line, LOG_RE, TS_RE, RID_RE

VALID = "2026-10-20T12:34:56Z INFO auth 192.0.2.10 POST /api/login 200 43ms rid=ab12cd3400000001"


def test_valid_line_ok():
    ev = parse_line(VALID)
    assert ev["level"] == "INFO"
    assert ev["status"] == 200
    assert ev["duration_ms"] == 43


def test_three_separate_regexes():
    assert LOG_RE.fullmatch(VALID)
    assert TS_RE.fullmatch("2026-10-20T12:34:56Z")
    assert RID_RE.fullmatch("ab12cd3400000001")


def test_broken_timestamp():
    bad = VALID.replace("2026-10-20T12:34:56Z", "2026-13-40T99:99:99Z")
    with pytest.raises(ParseError):
        parse_line(bad)


def test_wrong_ipv4():
    bad = VALID.replace("192.0.2.10", "999.1.1.1")
    with pytest.raises(ParseError):
        parse_line(bad)


def test_unsupported_level():
    bad = VALID.replace(" INFO ", " TRACE ")
    with pytest.raises(ParseError):
        parse_line(bad)


def test_bad_status():
    bad = VALID.replace(" 200 ", " 700 ")
    with pytest.raises(ParseError):
        parse_line(bad)


def test_negative_duration_rejected():
    bad = VALID.replace("43ms", "-5ms")
    with pytest.raises(ParseError):
        parse_line(bad)


def test_wrong_rid():
    bad = VALID.replace("ab12cd3400000001", "ZZZZ")
    with pytest.raises(ParseError):
        parse_line(bad)