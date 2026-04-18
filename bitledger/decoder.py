"""Decode Layer 1–3 and validate cross-layer rules (CONFLICT-005: suspend 1–2 for 1111)."""

from __future__ import annotations

from decimal import Decimal

from bitledger.encoder import SCALING_FACTORS, crc15_verify_layer1
from bitledger.errors import DecoderError
from bitledger.models import Layer1Config, Layer2Config, TransactionRecord


def unpack_layer1(data: bytes) -> Layer1Config:
    if len(data) != 8:
        raise DecoderError("Layer 1 must be 8 bytes")
    w = int.from_bytes(data, "big")
    if not crc15_verify_layer1(w):
        raise DecoderError("Layer 1 CRC-15 verification failed")
    p = (w >> 15) & ((1 << 49) - 1)
    if ((p >> 48) & 1) != 1:
        raise DecoderError("SOH marker missing")
    pv = (p >> 45) & 7
    perms = (p >> 41) & 0xF
    sess = (p >> 37) & 0xF
    sender = (p >> 5) & 0xFFFFFFFF
    sub = p & 0x1F
    l1 = Layer1Config()
    l1.protocol_version = pv
    l1.perm_read = bool((perms >> 3) & 1)
    l1.perm_write = bool((perms >> 2) & 1)
    l1.perm_correct = bool((perms >> 1) & 1)
    l1.perm_represent = bool(perms & 1)
    l1.default_split_order = (sess >> 3) & 1
    l1.opposing_account_explicit = bool((sess >> 2) & 1)
    l1.compound_mode_active = bool((sess >> 1) & 1)
    l1.bitledger_optional = bool(sess & 1)
    l1.sender_id = sender
    l1.sub_entity_id = sub
    return l1


def unpack_layer2(data: bytes) -> Layer2Config:
    if len(data) == 1 and data[0] == 0x6F:
        return Layer2Config()  # defaults
    if len(data) != 6:
        raise DecoderError("Layer 2 must be 6 bytes or short-form 0x6F")
    v = int.from_bytes(data, "big")
    l2 = Layer2Config()
    b = format(v, "048b")
    i = 0

    def read(n: int) -> int:
        nonlocal i
        s = b[i : i + n]
        i += n
        return int(s, 2)

    l2.transmission_type = read(2)
    l2.scaling_factor_index = read(7)
    l2.optimal_split = read(4)
    l2.decimal_position = read(3)
    bells = read(2)
    l2.enquiry_bell = bool(bells >> 1)
    l2.acknowledge_bell = bool(bells & 1)
    l2.group_sep = read(4)
    l2.record_sep = read(5)
    l2.file_sep = read(3)
    l2.entity_id = read(5)
    l2.currency_code = read(6)
    l2.rounding_balance = read(4)
    l2.compound_prefix = read(2)
    l2.reserved = read(1)
    if l2.transmission_type == 0:
        raise DecoderError("invalid transmission type 00")
    return l2


def unpack_record(n: int, S: int) -> TransactionRecord:
    n &= (1 << 40) - 1
    bl = n & 0xFF
    flags = (n >> 8) & 0x7F
    value_25 = n >> 15
    A = value_25 >> S
    r = value_25 & ((1 << S) - 1)
    rec = TransactionRecord()
    rec.multiplicand = A
    rec.multiplier = r
    rec.rounding_flag = bool((flags >> 6) & 1)
    rec.rounding_dir = (flags >> 5) & 1
    rec.split_order = (flags >> 4) & 1
    rec.direction = (flags >> 3) & 1
    rec.status = (flags >> 2) & 1
    rec.debit_credit = (flags >> 1) & 1
    rec.quantity_present = bool(flags & 1)
    rec.account_pair = (bl >> 4) & 0xF
    b37 = (bl >> 3) & 1
    b38 = (bl >> 2) & 1
    rec.completeness = (bl >> 1) & 1
    rec.extension_flag = bool(bl & 1)
    if rec.account_pair == 0xF:
        rec.continuation_subtype = (b37 << 1) | b38
        rec.bl_direction = b37
        rec.bl_status = b38
    else:
        rec.bl_direction = b37
        rec.bl_status = b38
        if b37 != rec.direction:
            raise DecoderError("Rule 1 violation: direction mirror mismatch")
        if b38 != rec.status:
            raise DecoderError("Rule 2 violation: status mirror mismatch")
    if not rec.rounding_flag and rec.rounding_dir:
        raise DecoderError("Rule 3 violation: invalid rounding state bit26=0 bit27=1")
    return rec


def validate_batch_integrity(expected_record_count: int, received_count: int) -> None:
    """Rule 5 (batch): published close count must match records received (TECHNICAL_OVERVIEW)."""
    if expected_record_count < 0 or received_count < 0:
        raise DecoderError("batch counts must be non-negative")
    if received_count != expected_record_count:
        raise DecoderError(
            f"Rule 5 violation: batch integrity expected {expected_record_count} records, "
            f"received {received_count}"
        )


def validate_compound_context(rec: TransactionRecord, l1: Layer1Config, l2: Layer2Config) -> None:
    """Rule 6 (compound): 1111 only when session compound is on and batch compound_prefix != 00."""
    if rec.account_pair != 0xF:
        return
    if not l1.compound_mode_active:
        raise DecoderError(
            "Rule 6 violation: account pair 1111 requires compound_mode_active in Layer 1"
        )
    if (l2.compound_prefix & 0x3) == 0:
        raise DecoderError(
            "Rule 6 violation: account pair 1111 requires compound_prefix != 00 in Layer 2"
        )


def decode_value(
    A: int,
    r: int,
    S: int,
    sf_index: int,
    decimal_position_wire: int,
    quantity_present: bool = False,
) -> Decimal:
    if sf_index < 0 or sf_index >= len(SCALING_FACTORS):
        raise DecoderError("sf_index out of range")
    if decimal_position_wire > 6:
        raise DecoderError("unsupported decimal position code")
    SF = SCALING_FACTORS[sf_index]
    D = decimal_position_wire
    if quantity_present:
        N = A * r
    else:
        N = (A << S) | r
    num = Decimal(N) * SF
    den = Decimal(10) ** D
    return num / den


def check_short_form_mismatch(profile_l2: Layer2Config) -> list[str]:
    """Return list of Layer2Config field names where profile_l2 differs from 0x6F defaults.

    Call this when 0x6F is decoded and a profile was loaded. A non-empty list means
    the wire short-form implies different session settings than the loaded profile,
    which may cause silent semantic errors in value decoding.
    """
    defaults = Layer2Config()
    mismatched: list[str] = []
    for fname in (
        "scaling_factor_index",
        "optimal_split",
        "decimal_position",
        "transmission_type",
        "currency_code",
        "compound_prefix",
    ):
        if getattr(profile_l2, fname) != getattr(defaults, fname):
            mismatched.append(fname)
    return mismatched
