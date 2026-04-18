"""decoder.py — unpack and rules."""

import pytest

from bitledger import decoder, encoder
from bitledger.errors import DecoderError, EncoderError
from bitledger.models import Layer1Config, Layer2Config, TransactionRecord


def test_layer1_roundtrip():
    l1 = Layer1Config(sender_id=0xDEADBEEF, sub_entity_id=11, compound_mode_active=True)
    b = encoder.encode_layer1_bytes(l1)
    l1b = decoder.unpack_layer1(b)
    assert l1b.sender_id == 0xDEADBEEF
    assert l1b.sub_entity_id == 11
    assert l1b.compound_mode_active is True


def test_layer2_roundtrip():
    l2 = Layer2Config(
        transmission_type=1,
        scaling_factor_index=3,
        record_sep=7,
        currency_code=1,
        compound_prefix=2,
    )
    b = encoder.encode_layer2_bytes(l2)
    l2b = decoder.unpack_layer2(b)
    assert l2b.scaling_factor_index == 3
    assert l2b.record_sep == 7
    assert l2b.currency_code == 1


def test_record_mirror_violation():
    l1 = Layer1Config()
    l2 = Layer2Config()
    n = encoder.serialise(
        TransactionRecord(
            multiplicand=1,
            multiplier=0,
            direction=0,
            status=0,
            account_pair=4,
            completeness=0,
        ),
        8,
        l1,
        l2,
    )
    # Corrupt spec bit 37 (direction mirror) — bit index 3 from LSB in 40-bit word
    bad = n ^ (1 << 3)
    with pytest.raises(DecoderError):
        decoder.unpack_record(bad, 8)


def test_1111_no_mirror_check():
    l1 = Layer1Config(compound_mode_active=True)
    l2 = Layer2Config(compound_prefix=3)
    rec = TransactionRecord(
        multiplicand=0,
        multiplier=0,
        direction=1,
        status=1,
        account_pair=0xF,
        continuation_subtype=2,
        completeness=0,
    )
    n = encoder.serialise(rec, 8, l1, l2)
    out = decoder.unpack_record(n, 8)
    assert out.account_pair == 0xF
    assert out.continuation_subtype == 2


def test_rule3_invalid_rounding_state():
    l1, l2 = Layer1Config(), Layer2Config()
    rec = TransactionRecord(
        multiplicand=1,
        multiplier=0,
        rounding_flag=False,
        rounding_dir=1,
        direction=0,
        status=0,
        account_pair=4,
        completeness=0,
    )
    with pytest.raises(EncoderError):
        encoder.serialise(rec, 8, l1, l2)


def test_rule3_unpack_rejects():
    l1, l2 = Layer1Config(), Layer2Config()
    rec = TransactionRecord(
        multiplicand=1,
        multiplier=0,
        rounding_flag=True,
        rounding_dir=0,
        direction=0,
        status=0,
        account_pair=4,
        completeness=0,
    )
    n = encoder.serialise(rec, 8, l1, l2)
    bad = n & ~(1 << 14)  # clear rounding_flag (bit 26 in 40-bit field)
    bad |= 1 << 13  # set rounding_dir without flag
    with pytest.raises(DecoderError, match="Rule 3"):
        decoder.unpack_record(bad, 8)


def test_rule4_crc_layer1_failure():
    l1 = Layer1Config(sender_id=0x11111111)
    b = bytearray(encoder.encode_layer1_bytes(l1))
    b[-1] ^= 0x01
    with pytest.raises(DecoderError, match="CRC"):
        decoder.unpack_layer1(bytes(b))


def test_rule5_batch_integrity():
    with pytest.raises(DecoderError, match="Rule 5"):
        decoder.validate_batch_integrity(3, 2)
    decoder.validate_batch_integrity(0, 0)


def test_rule6_compound_context_violation():
    l1 = Layer1Config(compound_mode_active=False)
    l2 = Layer2Config(compound_prefix=0)
    rec = TransactionRecord(account_pair=0xF, continuation_subtype=0, completeness=0)
    with pytest.raises(DecoderError, match="Rule 6"):
        decoder.validate_compound_context(rec, l1, l2)


def test_rule6_compound_prefix_zero():
    l1 = Layer1Config(compound_mode_active=True)
    l2 = Layer2Config(compound_prefix=0)
    rec = TransactionRecord(account_pair=0xF, continuation_subtype=0, completeness=0)
    with pytest.raises(DecoderError, match="Rule 6"):
        decoder.validate_compound_context(rec, l1, l2)


def test_rule2_status_mirror_violation():
    l1, l2 = Layer1Config(), Layer2Config()
    n = encoder.serialise(
        TransactionRecord(
            multiplicand=1,
            multiplier=0,
            direction=0,
            status=0,
            account_pair=4,
            completeness=0,
        ),
        8,
        l1,
        l2,
    )
    bad = n ^ (1 << 2)
    with pytest.raises(DecoderError, match="Rule 2"):
        decoder.unpack_record(bad, 8)
