"""Typed exceptions for BitLedger."""


class ProtocolError(Exception):
    """Protocol-level violation (invalid bit state, rule breach)."""


class EncoderError(Exception):
    """Encoding failed (overflow, invalid field combination)."""


class DecoderError(Exception):
    """Decoding or validation failed."""


class ProfileError(Exception):
    """Profile / currency lookup error."""
