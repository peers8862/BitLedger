"""bitledger make / suggest-sf."""

from decimal import Decimal

import pytest

from bitledger.cli import main
from bitledger.cli_make import find_smallest_sf, parse_amount_string


def test_parse_amount_grouping():
    assert parse_amount_string("24,456,346,932") == Decimal("24456346932")
    assert parse_amount_string("1_000.50") == Decimal("1000.50")


def test_find_smallest_sf_billion_class():
    amt = Decimal("2500000000")
    found = find_smallest_sf(amt, 2, 4, 8, 0, 127)
    assert found is not None
    sf, (N, A, r, rf, rd) = found
    # Smallest SF with integral R in range: ×10^4 fits (×10^3 would need R=250M > 33.5M).
    assert sf == 4
    assert N == 25_000_000
    assert rf == 0


def test_find_smallest_sf_very_large_exact():
    """Breadth: amounts needing SF beyond the old 0–17 table still resolve."""
    amt = Decimal(10) ** 98
    found = find_smallest_sf(amt, 2, 4, 8, 0, 127)
    assert found is not None
    sf, (N, A, r, rf, rd) = found
    assert sf == 93
    assert rf == 0
    assert N == 10_000_000


def test_make_cli_stdout(capsys):
    code = main(["make", "--amount", "4.53", "--dp", "2", "--account-pair", "4"])
    assert code == 0
    out = capsys.readouterr().out
    assert "SF index = 0" in out
    assert "4.53" in out
    assert "make (plan → record)" in out
    assert "Suggested encode" in out
    assert "bitledger encode" in out


def test_check_amount_cli_stdout(capsys):
    code = main(["check-amount", "--amount", "4.53", "--dp", "2", "--account-pair", "4"])
    assert code == 0
    out = capsys.readouterr().out
    assert "check-amount (verification)" in out
    assert "STATUS:" in out
    assert "EXACT" in out or "ROUNDING" in out
    assert "bitledger encode" not in out
    assert "bitledger make" in out


def test_suggest_sf_alias(capsys):
    code = main(["suggest-sf", "--amount", "100", "--dp", "2", "--account-pair", "4"])
    assert code == 0
    assert "make (plan → record)" in capsys.readouterr().out
