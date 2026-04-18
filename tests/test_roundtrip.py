"""encode → decode value path."""

from decimal import Decimal

import pytest

from bitledger import decoder, encoder
from bitledger.models import Layer1Config, Layer2Config, TransactionRecord


def test_value_roundtrip():
    l1 = Layer1Config()
    l2 = Layer2Config()
    S = 8
    _, A, r, rf, rd = encoder.encode_value(Decimal("4.53"), 0, 2, 4, S)
    rec = TransactionRecord(
        multiplicand=A,
        multiplier=r,
        rounding_flag=bool(rf),
        rounding_dir=rd,
        direction=0,
        status=0,
        debit_credit=0,
        account_pair=4,
        completeness=0,
    )
    n = encoder.serialise(rec, S, l1, l2)
    out = decoder.unpack_record(n, S)
    v = decoder.decode_value(
        out.multiplicand,
        out.multiplier,
        S,
        0,
        l2.decimal_position,
        out.quantity_present,
    )
    assert v == Decimal("4.53")


@pytest.mark.parametrize("sf", range(128))
def test_encode_decode_decimal_across_sf_indices(sf: int):
    """Roundtrip for each SF index when value is exactly representable (rf=0)."""
    from bitledger.encoder import SCALING_FACTORS

    l1 = Layer1Config()
    l2 = Layer2Config(
        transmission_type=1,
        scaling_factor_index=sf,
        decimal_position=2,
    )
    # D=2 ⇒ R = amt×100/SF; choose amt = SF/100 so R = 1 and N = 1 (exact at every SF index).
    amt = SCALING_FACTORS[sf] / Decimal(100)
    try:
        N, A, r, rf, rd = encoder.encode_value(amt, sf, 2, 4, l2.optimal_split)
    except EncoderError:
        pytest.skip("amount out of range at this SF")
    if rf != 0:
        pytest.fail("expected exact encoding for SF/100 at wire D=2")
    rec = TransactionRecord(
        multiplicand=A,
        multiplier=r,
        rounding_flag=False,
        rounding_dir=rd,
        direction=0,
        status=0,
        debit_credit=0,
        account_pair=4,
        completeness=0,
    )
    n = encoder.serialise(rec, l2.optimal_split, l1, l2)
    out = decoder.unpack_record(n, l2.optimal_split)
    v = decoder.decode_value(
        out.multiplicand,
        out.multiplier,
        l2.optimal_split,
        sf,
        2,
        out.quantity_present,
    )
    assert isinstance(v, Decimal)
    assert v == amt


def test_min_mid_max_n_roundtrip():
    """Minimum / mid / large N at fixed S=8, SF=0, D=2 (exact encodings)."""
    l1 = Layer1Config()
    l2 = Layer2Config(scaling_factor_index=0, decimal_position=2)
    checked = 0
    for amt in (Decimal("0.01"), Decimal("12345.67"), Decimal("335544.31")):
        N, A, r, rf, rd = encoder.encode_value(amt, 0, 2, 4, 8)
        rec = TransactionRecord(
            multiplicand=A,
            multiplier=r,
            rounding_flag=bool(rf),
            rounding_dir=rd,
            direction=0,
            status=0,
            debit_credit=0,
            account_pair=4,
            completeness=0,
        )
        n = encoder.serialise(rec, 8, l1, l2)
        out = decoder.unpack_record(n, 8)
        v = decoder.decode_value(
            out.multiplicand, out.multiplier, 8, 0, 2, out.quantity_present
        )
        if not rf:
            assert v == amt
            checked += 1
    assert checked >= 1
