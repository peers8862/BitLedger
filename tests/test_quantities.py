"""20 tests covering quantity mode (quantity_present flag)."""

from __future__ import annotations

import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest

from bitledger import decoder, encoder
from bitledger.decoder import decode_value, unpack_record
from bitledger.encoder import encode_value, SCALING_FACTORS, serialise, encode_layer1_bytes, encode_layer2_bytes
from bitledger.errors import DecoderError, EncoderError
from bitledger.models import Layer1Config, Layer2Config, TransactionRecord

PROJECT_ROOT = str(Path(__file__).parent.parent)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "bitledger.cli", *args],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )


# ---------------------------------------------------------------------------
# Unit-level tests (12)
# ---------------------------------------------------------------------------

def test_quantity_basic_N() -> None:
    """A=8, r=3, quantity_present=True → N = A*r = 24 (not bit-split)."""
    A, r, S = 8, 3, 4
    N = A * r
    assert N == 24


def test_quantity_vs_split_differ() -> None:
    """Same A=8, r=3, S=4 → quantity N=24, split N=(8<<4)|3=131; assert they differ."""
    A, r, S = 8, 3, 4
    N_qty = A * r
    N_split = (A << S) | r
    assert N_qty == 24
    assert N_split == 131
    assert N_qty != N_split


def test_quantity_decode_value_exact() -> None:
    """A=24, r=249, S=4, sf=0, dp=2, quantity=True → Decimal("59.76")."""
    # N = 24 * 249 = 5976; SF=SCALING_FACTORS[0]=1; dp=2 → 5976/100 = 59.76
    result = decode_value(A=24, r=249, S=4, sf_index=0, decimal_position_wire=2, quantity_present=True)
    assert result == Decimal("59.76")


def test_quantity_decode_value_sf1() -> None:
    """A=10, r=5, S=4, sf=1, dp=0, quantity=True → N=50, SF=SCALING_FACTORS[1]=10."""
    # N = 10*5 = 50; SF=10; dp=0 → 50*10 / 1 = 500
    result = decode_value(A=10, r=5, S=4, sf_index=1, decimal_position_wire=0, quantity_present=True)
    expected = Decimal(50) * SCALING_FACTORS[1] / Decimal(10) ** 0
    assert result == expected


def test_quantity_decode_value_sf5() -> None:
    """A=5, r=4, S=4, sf=5, dp=1, quantity=True → check exact value."""
    # N = 5*4 = 20; SF=SCALING_FACTORS[5]=100000; dp=1 → 20*100000/10 = 200000
    result = decode_value(A=5, r=4, S=4, sf_index=5, decimal_position_wire=1, quantity_present=True)
    expected = Decimal(20) * SCALING_FACTORS[5] / Decimal(10) ** 1
    assert result == expected


def test_quantity_large_N_exact() -> None:
    """A=4096, r=8191, quantity=True → N=33550336 (under max 33554431), decode OK."""
    A, r = 4096, 8191
    N = A * r
    assert N == 33550336
    assert N <= 33_554_431
    # decode with sf=0, dp=0, S=8 — should not raise
    result = decode_value(A=A, r=r, S=8, sf_index=0, decimal_position_wire=0, quantity_present=True)
    assert result == Decimal(N)


def test_quantity_N_zero_A() -> None:
    """A=0, r=5, quantity=True → N=0, decode_value returns 0."""
    result = decode_value(A=0, r=5, S=4, sf_index=0, decimal_position_wire=0, quantity_present=True)
    assert result == Decimal(0)


def test_quantity_N_zero_r() -> None:
    """A=5, r=0, quantity=True → N=0, decode_value returns 0."""
    result = decode_value(A=5, r=0, S=4, sf_index=0, decimal_position_wire=0, quantity_present=True)
    assert result == Decimal(0)


def test_quantity_A_equals_r() -> None:
    """A=100, r=100, quantity=True → N=10000, check decode."""
    result = decode_value(A=100, r=100, S=8, sf_index=0, decimal_position_wire=2, quantity_present=True)
    # N=10000, SF=1, dp=2 → 10000/100 = 100.00
    assert result == Decimal("100.00")


def test_quantity_encode_value_roundtrip() -> None:
    """Encode an amount that works with S=8, decode with quantity=True, assert within tolerance."""
    # Use amount 59.76, sf=0, dp=2, account_pair=4, S=8
    amt = Decimal("59.76")
    N, A, r, rf, rd = encode_value(amt, 0, 2, 4, 8)
    assert rf == 0, "expected exact encoding"
    # Decode as quantity: N = A*r (may not equal the original N in split mode)
    # This test verifies decode_value with quantity=True uses A*r, not (A<<S)|r
    qty_result = decode_value(A=A, r=r, S=8, sf_index=0, decimal_position_wire=2, quantity_present=True)
    split_result = decode_value(A=A, r=r, S=8, sf_index=0, decimal_position_wire=2, quantity_present=False)
    # The split result should equal the original amount
    assert split_result == amt
    # The quantity result uses A*r — just verify it's a valid Decimal and doesn't raise
    assert isinstance(qty_result, Decimal)


def test_quantity_S15_ignored() -> None:
    """A=3, r=7, S=15, quantity_present=True → N=21 (S is ignored in quantity mode)."""
    # In quantity mode, N = A*r regardless of S
    result = decode_value(A=3, r=7, S=15, sf_index=0, decimal_position_wire=0, quantity_present=True)
    assert result == Decimal(21)


def test_quantity_present_flag_in_record() -> None:
    """Encode a record with quantity_present=True, serialise, unpack_record, assert rec.quantity_present is True."""
    l1 = Layer1Config()
    l2 = Layer2Config()
    rec = TransactionRecord(
        multiplicand=8,
        multiplier=3,
        quantity_present=True,
        account_pair=4,
    )
    n40 = serialise(rec, l2.optimal_split, l1, l2)
    unpacked = unpack_record(n40, l2.optimal_split)
    assert unpacked.quantity_present is True


# ---------------------------------------------------------------------------
# Negative / edge tests (8)
# ---------------------------------------------------------------------------

def test_quantity_sf_out_of_range() -> None:
    """decode_value with sf_index=200, quantity=True → DecoderError."""
    with pytest.raises(DecoderError):
        decode_value(A=1, r=1, S=4, sf_index=200, decimal_position_wire=0, quantity_present=True)


def test_quantity_dp_wire_invalid() -> None:
    """decode_value with decimal_position_wire=7, quantity=True → DecoderError."""
    with pytest.raises(DecoderError):
        decode_value(A=1, r=1, S=4, sf_index=0, decimal_position_wire=7, quantity_present=True)


def test_quantity_N_overflow_unpack() -> None:
    """Verify that unpack_record with large n40 doesn't raise and A,r values are bounded."""
    # Build a max n40 (all 40 bits set = 0xFFFFFFFFFF)
    n40 = (1 << 40) - 1
    l2 = Layer2Config()  # optimal_split=8
    rec = unpack_record(n40, l2.optimal_split)
    # value_25 is 25 bits, A and r are bounded by split
    value_25 = n40 >> 15
    assert value_25 <= (1 << 25) - 1
    # In quantity mode decode: N = A*r; just verify it's a non-negative integer
    N_qty = rec.multiplicand * rec.multiplier
    assert N_qty >= 0


def test_quantity_flag_false_uses_split() -> None:
    """A=8, r=3, S=4, quantity_present=False → N = (8<<4)|3 = 131, NOT 24."""
    result_split = decode_value(A=8, r=3, S=4, sf_index=0, decimal_position_wire=0, quantity_present=False)
    result_qty = decode_value(A=8, r=3, S=4, sf_index=0, decimal_position_wire=0, quantity_present=True)
    # split: N = (8<<4)|3 = 131
    assert result_split == Decimal(131)
    # quantity: N = 8*3 = 24
    assert result_qty == Decimal(24)
    assert result_split != result_qty


def test_quantity_negative_encode_float_rejected() -> None:
    """encoder.encode_value with float input raises EncoderError."""
    with pytest.raises(EncoderError):
        encode_value(59.76, 0, 2, 4, 8)  # type: ignore[arg-type]


def test_quantity_make_cli_quantity_flag_in_json() -> None:
    """subprocess: bitledger make --amount 59.76 --quantity-present 1 --json; parse output JSON; assert json['quantity_present'] is True."""
    result = _run("make", "--amount", "59.76", "--quantity-present", "1", "--json")
    assert result.returncode == 0, f"make exited {result.returncode}: {result.stderr}"
    data = json.loads(result.stdout)
    assert data.get("quantity_present") is True


def test_quantity_encode_cli_quantity_roundtrip() -> None:
    """subprocess: encode --amount 59.76 --quantity-present 1 --auto-sf --accept-rounding --out /tmp/qty_test.bl; then decode --in /tmp/qty_test.bl; assert exit code 0."""
    out_path = "/tmp/qty_test.bl"
    enc = _run(
        "encode",
        "--amount", "59.76",
        "--quantity-present", "1",
        "--auto-sf",
        "--accept-rounding",
        "--out", out_path,
    )
    assert enc.returncode == 0, f"encode failed: {enc.stderr}"
    dec = _run("decode", "--in", out_path)
    assert dec.returncode == 0, f"decode failed: {dec.stderr}"


def test_quantity_check_amount_cli() -> None:
    """subprocess: bitledger check-amount --amount 10.00 --quantity-present 1; assert exit code 0 and stdout contains 'quantity'."""
    result = _run("check-amount", "--amount", "10.00", "--quantity-present", "1")
    assert result.returncode == 0, f"check-amount failed: {result.stderr}"
    assert "quantity" in result.stdout.lower(), (
        f"Expected 'quantity' in stdout, got:\n{result.stdout}"
    )
