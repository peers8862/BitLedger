"""encode_value TASK-2.05 vectors."""

from decimal import Decimal

import pytest

from bitledger import decoder
from bitledger.encoder import encode_value, serialise
from bitledger.errors import EncoderError
from bitledger.models import Layer1Config, Layer2Config, TransactionRecord


def test_decompose_vectors():
    # $4.53 SF×1 D=2 → N=453 A=1 r=197 S=8
    N, A, r, rf, rd = encode_value(Decimal("4.53"), 0, 2, 4, 8)
    assert N == 453 and A == 1 and r == 197 and rf == 0

    N, A, r, rf, rd = encode_value(Decimal("98765.43"), 0, 2, 4, 8)
    assert N == 9_876_543 and A == 38_580 and r == 63

    # 24 × $2.49 → N=5,976 (quantity semantics at value layer)
    N, A, r, rf, rd = encode_value(Decimal("59.76"), 0, 2, 4, 8)
    assert N == 5976


def test_sf100():
    # Stored integer N=24,500 at SF index 2 (×100), D=2 → $24,500.00 wire-space
    N, A, r, rf, rd = encode_value(Decimal("24500"), 2, 2, 4, 8)
    assert N == 24_500 and A == 95 and r == 180


def test_overflow():
    with pytest.raises(EncoderError):
        encode_value(Decimal("1e15"), 0, 2, 4, 8)


def test_float_rejected():
    with pytest.raises(EncoderError):
        encode_value(4.53, 0, 2, 4, 8)  # type: ignore[arg-type]


def test_currencies_lookup():
    from bitledger.currencies import lookup_by_code, lookup_by_index
    from bitledger.errors import ProfileError

    assert lookup_by_index(0)["code"] == ""
    assert lookup_by_code("USD") == 1
    with pytest.raises(ProfileError):
        lookup_by_index(99)


def test_task_205_spec_vectors_exact_decimal():
    """TASK-2.05 four normative vectors (TASK-2.13 criterion 1)."""
    # $4.53, SF×1, D=2 → N=453, A=1, r=197
    N, A, r, rf, rd = encode_value(Decimal("4.53"), 0, 2, 4, 8)
    assert (N, A, r, rf, rd) == (453, 1, 197, 0, 0)

    # $98,765.43 → N=9,876,543, A=38,580, r=63
    N, A, r, rf, rd = encode_value(Decimal("98765.43"), 0, 2, 4, 8)
    assert (N, A, r, rf, rd) == (9_876_543, 38_580, 63, 0, 0)

    # 24 × $2.49 quantity semantics: N = A*r = 5,976; wire uses quantity_present at decode
    l1, l2 = Layer1Config(), Layer2Config()
    rec = TransactionRecord(
        multiplicand=249,
        multiplier=24,
        account_pair=4,
        direction=0,
        status=0,
        debit_credit=0,
        completeness=0,
        quantity_present=True,
    )
    n = serialise(rec, 8, l1, l2)
    out = decoder.unpack_record(n, 8)
    v = decoder.decode_value(
        out.multiplicand, out.multiplier, 8, 0, 2, quantity_present=True
    )
    assert v == Decimal("59.76")

    # $24,500.00 at SF×100 (index 2), D=2 → N=24,500, A=95, r=180
    N, A, r, rf, rd = encode_value(Decimal("24500"), 2, 2, 4, 8)
    assert (N, A, r, rf, rd) == (24_500, 95, 180, 0, 0)


def test_scaling_factor_indices_match_layer2_wire():
    from bitledger.encoder import SCALING_FACTORS

    assert len(SCALING_FACTORS) == 128
    assert SCALING_FACTORS[17] == Decimal(10**17)
    assert SCALING_FACTORS[127] == Decimal(10**127)
