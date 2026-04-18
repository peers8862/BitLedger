"""8-bit control records — leading 0 distinguishes from transaction data."""

from __future__ import annotations

from bitledger.errors import DecoderError


def encode_control(type_bits: int, payload: int) -> int:
    """Pack type (3 bits) and payload (4 bits); result 0..127."""
    if type_bits & ~0x7:
        raise ValueError("type_bits must be 0..7")
    if payload & ~0xF:
        raise ValueError("payload must be 0..15")
    return (type_bits << 4) | payload


def decode_control(byte: int) -> tuple[int, int]:
    if byte & 0x80:
        raise DecoderError("Not a control record: high bit is set")
    return (byte >> 4) & 0x7, byte & 0xF
