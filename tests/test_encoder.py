"""encoder.py — serialise, CRC-15, Layer2."""

from decimal import Decimal

import pytest

from bitledger.encoder import (
    crc15_verify_layer1,
    decompose,
    encode_layer1_bytes,
    encode_layer2_bytes,
    layer2_matches_short_form_defaults,
    serialise,
)
from bitledger.errors import EncoderError
from bitledger.models import Layer1Config, Layer2Config, TransactionRecord


def test_serialise_simple():
    l1 = Layer1Config()
    l2 = Layer2Config()
    rec = TransactionRecord(
        multiplicand=1,
        multiplier=197,
        account_pair=4,
        direction=0,
        status=0,
        debit_credit=0,
        completeness=0,
    )
    n = serialise(rec, 8, l1, l2)
    assert n > 0


def test_crc15_layer1_roundtrip():
    l1 = Layer1Config(sender_id=0x12345678, sub_entity_id=3)
    b = encode_layer1_bytes(l1)
    w = int.from_bytes(b, "big")
    assert crc15_verify_layer1(w)


def test_crc15_single_bit_flip():
    l1 = Layer1Config(sender_id=0xABCDEF01)
    b = encode_layer1_bytes(l1)
    w0 = int.from_bytes(b, "big")
    assert crc15_verify_layer1(w0)
    for spec_bit in range(1, 50):  # bits 1–49 protected
        w1 = w0 ^ (1 << (64 - spec_bit))
        assert not crc15_verify_layer1(w1), f"flip spec bit {spec_bit} should invalidate"


def test_layer2_short_detection():
    l1 = Layer1Config(sub_entity_id=5)
    l2 = Layer2Config(entity_id=5)
    assert layer2_matches_short_form_defaults(l2, l1)


def test_decompose_s_0_17_edges():
    """TASK-2.05: decompose for S=0 and S=17 at N extremes."""
    assert decompose(0, 0) == (0, 0)
    assert decompose(33_554_431, 17) == (33_554_431 >> 17, 33_554_431 & ((1 << 17) - 1))


def test_1111_requires_compound():
    l1 = Layer1Config(compound_mode_active=False)
    l2 = Layer2Config(compound_prefix=3)
    rec = TransactionRecord(account_pair=0xF, continuation_subtype=0)
    with pytest.raises(EncoderError):
        serialise(rec, 8, l1, l2)
