"""Encode → decode smoke loop for regression testing."""

from __future__ import annotations

from bitledger import decoder, encoder
from bitledger.models import Layer1Config, Layer2Config, TransactionRecord


def simulate_record_roundtrip(
    rec: TransactionRecord,
    S: int,
    l1: Layer1Config,
    l2: Layer2Config,
) -> TransactionRecord:
    n = encoder.serialise(rec, S, l1, l2)
    out = decoder.unpack_record(n, S)
    decoder.validate_compound_context(out, l1, l2)
    return out
