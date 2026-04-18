"""control.py round-trip."""

import pytest

from bitledger.control import decode_control, encode_control
from bitledger.errors import DecoderError


def test_encode_decode_roundtrip():
    for t in range(8):
        for p in range(16):
            b = encode_control(t, p)
            assert b < 128
            assert decode_control(b) == (t, p)


def test_decode_high_bit():
    with pytest.raises(DecoderError):
        decode_control(0x80)


def test_type_011_ack_nack_payload_discrimination():
    """Type 011: payload low bit distinguishes ACK (0) vs NACK (1) in 4-bit field."""
    ack = encode_control(0b011, 0)
    nack = encode_control(0b011, 1)
    assert decode_control(ack) == (0b011, 0)
    assert decode_control(nack) == (0b011, 1)


def test_escape_like_payload_1111_roundtrips():
    """Payload nibble 0b1111 is legal on the wire for control types (stream escape is framing-level)."""
    for t in (0b000, 0b001, 0b010):
        b = encode_control(t, 0b1111)
        assert decode_control(b) == (t, 0b1111)
