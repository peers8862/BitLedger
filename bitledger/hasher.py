"""Hash computation for BitLedger record identity.

Three IDs, three purposes:
    wire_id      blake2b(wire_bytes)                  Shared between sender and receiver. Same blob = same ID.
    semantic_id  blake2b(decoded fields canonical)    Same transaction regardless of encoding = same ID.
    session_id   blake2b(L1_bytes)[:8]               Stable session anchor (if sender_id != 0).
    template_id  blake2b(name|amount|pair|dir|ccy)   Stable template identifier.
"""
from __future__ import annotations

import hashlib
from decimal import Decimal


def compute_wire_id(wire_bytes: bytes) -> str:
    """blake2b-16 of raw wire bytes → 32 hex chars. Identical for sender and receiver."""
    return hashlib.blake2b(wire_bytes, digest_size=16).hexdigest()


def compute_semantic_id(
    amount: Decimal,
    account_pair: int,
    tx_direction: int,
    tx_status: int,
    currency: int,
    sender_id: int = 0,
) -> str:
    """blake2b-16 of canonical decoded fields → 32 hex chars.
    Same transaction content = same ID regardless of wire encoding choices.
    """
    canonical = (
        str(amount).encode("ascii")
        + b"|"
        + account_pair.to_bytes(1, "big")
        + tx_direction.to_bytes(1, "big")
        + tx_status.to_bytes(1, "big")
        + currency.to_bytes(1, "big")
        + sender_id.to_bytes(4, "big")
    )
    return hashlib.blake2b(canonical, digest_size=16).hexdigest()


def compute_session_id(l1_bytes: bytes) -> str:
    """blake2b-8 of Layer 1 bytes → 16 hex chars.
    Stable for a session; unique only when sender_id != 0x00000000.
    """
    return hashlib.blake2b(l1_bytes, digest_size=8).hexdigest()


def compute_template_id(
    name: str, amount: str, account_pair: int, direction: int, currency: int
) -> str:
    """blake2b-8 of defining template parameters → 16 hex chars. Stable across renames."""
    canonical = (
        name.encode("utf-8")
        + b"|"
        + amount.encode("ascii")
        + b"|"
        + account_pair.to_bytes(1, "big")
        + direction.to_bytes(1, "big")
        + currency.to_bytes(1, "big")
    )
    return hashlib.blake2b(canonical, digest_size=8).hexdigest()
