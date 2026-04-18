"""Encode Layer 1–3, value decomposition, CRC-15, serialise 40-bit records."""

from __future__ import annotations

from decimal import ROUND_DOWN, ROUND_HALF_UP, ROUND_UP, Decimal

from bitledger.errors import EncoderError
from bitledger.models import Layer1Config, Layer2Config, TransactionRecord

CRC15_POLY = 0x8003

ROUND_UP_PAIRS = {0b0001, 0b0011, 0b0101, 0b0111, 0b1000, 0b1100}
ROUND_DOWN_PAIRS = {0b0100, 0b0110, 0b1001, 0b1011}

# SF index 0..127: ×10^index (matches 7-bit Layer 2 scaling_factor_index wire field).
SCALING_FACTORS: tuple[Decimal, ...] = tuple(Decimal(10**i) for i in range(128))


def decompose(N: int, S: int) -> tuple[int, int]:
    if N < 0 or N > 33_554_431:
        raise EncoderError(f"N out of range: {N}")
    if S < 0 or S > 17:
        raise EncoderError(f"S out of range: {S}")
    return N >> S, N & ((1 << S) - 1)


def rounding_mode(account_pair: int) -> str:
    if account_pair in ROUND_UP_PAIRS:
        return "up"
    if account_pair in ROUND_DOWN_PAIRS:
        return "down"
    return "nearest"


def encode_value(
    true_value: Decimal,
    sf_index: int,
    decimal_position_wire: int,
    account_pair: int,
    S: int,
) -> tuple[int, int, int, int, int]:
    """
    Returns (N, A, r, rounding_flag, rounding_dir).
    decimal_position_wire: 3-bit Layer2 code (010 = two decimal places).
    """
    if isinstance(true_value, float):
        raise EncoderError("float not allowed; use Decimal")
    if sf_index < 0 or sf_index >= len(SCALING_FACTORS):
        raise EncoderError(f"sf_index out of range: {sf_index}")
    SF = SCALING_FACTORS[sf_index]
    D = _wire_dp_to_d(decimal_position_wire)
    R = true_value * (Decimal(10) ** D) / SF
    if R != R.to_integral_value():
        mode = rounding_mode(account_pair)
        if mode == "up":
            N = int(R.to_integral_value(rounding=ROUND_UP))
            rd = 1
        elif mode == "down":
            N = int(R.to_integral_value(rounding=ROUND_DOWN))
            rd = 0
        else:
            N = int(R.to_integral_value(rounding=ROUND_HALF_UP))
            rd = 1 if N > R else 0
        rf = 1
    else:
        N = int(R)
        rf = 0
        rd = 0
    if N > 33_554_431:
        raise EncoderError("overflow: N > 33,554,431")
    A, r = decompose(N, S)
    return N, A, r, rf, rd


def _wire_dp_to_d(wire: int) -> int:
    if wire in (0, 1, 2, 3, 4, 5, 6):
        return wire
    raise EncoderError("decimal position 111 requires extension (not implemented)")


def crc15_remainder_payload49(payload49: int) -> int:
    """CRC remainder for bits 1–49 (MSB-first int), to place in bits 50–64."""
    num_bits = 49
    reg = (payload49 << 15) & ((1 << (num_bits + 15)) - 1)
    poly = CRC15_POLY << (num_bits - 1)
    for i in range(num_bits):
        if reg & (1 << (num_bits + 14 - i)):
            reg ^= poly
        poly >>= 1
    return reg & 0x7FFF


def crc15_verify_layer1(codeword64: int) -> bool:
    """True if bits 50–64 match CRC-15 of bits 1–49 (same remainder as encoder)."""
    p49 = (codeword64 >> 15) & ((1 << 49) - 1)
    rx = codeword64 & 0x7FFF
    return crc15_remainder_payload49(p49) == rx


def pack_layer1_payload49(l1: Layer1Config) -> int:
    """Bits 1–49 MSB-first as integer (bit1 = MSB of 49-bit number)."""
    perms = (
        (int(l1.perm_read) << 3)
        | (int(l1.perm_write) << 2)
        | (int(l1.perm_correct) << 1)
        | int(l1.perm_represent)
    )
    sess = (
        (int(l1.default_split_order) << 3)
        | (int(l1.opposing_account_explicit) << 2)
        | (int(l1.compound_mode_active) << 1)
        | int(l1.bitledger_optional)
    )
    w = 0
    bits: list[int] = []
    bits.append(1)  # SOH
    for i in range(3):
        bits.append((l1.protocol_version >> (2 - i)) & 1)
    for i in range(4):
        bits.append((perms >> (3 - i)) & 1)
    for i in range(4):
        bits.append((sess >> (3 - i)) & 1)
    for i in range(32):
        bits.append((l1.sender_id >> (31 - i)) & 1)
    for i in range(5):
        bits.append((l1.sub_entity_id >> (4 - i)) & 1)
    for b in bits:
        w = (w << 1) | b
    return w


def encode_layer1_bytes(l1: Layer1Config) -> bytes:
    p49 = pack_layer1_payload49(l1)
    crc = crc15_remainder_payload49(p49)
    full = (p49 << 15) | crc
    return full.to_bytes(8, "big")


def pack_layer2_48(l2: Layer2Config) -> int:
    """48-bit batch header MSB first (spec bit 1 = MSB)."""
    tt = l2.transmission_type & 0x3
    if tt == 0:
        raise EncoderError("transmission_type 00 is invalid")
    sf = l2.scaling_factor_index & 0x7F
    ospl = l2.optimal_split & 0xF
    d = l2.decimal_position & 0x7
    bells = (int(l2.enquiry_bell) << 1) | int(l2.acknowledge_bell)
    g = l2.group_sep & 0xF
    rsep = l2.record_sep & 0x1F
    fsep = l2.file_sep & 0x7
    ent = l2.entity_id & 0x1F
    ccy = l2.currency_code & 0x3F
    rb = l2.rounding_balance & 0xF
    cp = l2.compound_prefix & 0x3
    res = l2.reserved & 1

    bits: list[int] = []
    for i in range(2):
        bits.append((tt >> (1 - i)) & 1)
    for i in range(7):
        bits.append((sf >> (6 - i)) & 1)
    for i in range(4):
        bits.append((ospl >> (3 - i)) & 1)
    for i in range(3):
        bits.append((d >> (2 - i)) & 1)
    bits.append(bells >> 1)
    bits.append(bells & 1)
    for i in range(4):
        bits.append((g >> (3 - i)) & 1)
    for i in range(5):
        bits.append((rsep >> (4 - i)) & 1)
    for i in range(3):
        bits.append((fsep >> (2 - i)) & 1)
    for i in range(5):
        bits.append((ent >> (4 - i)) & 1)
    for i in range(6):
        bits.append((ccy >> (5 - i)) & 1)
    for i in range(4):
        bits.append((rb >> (3 - i)) & 1)
    for i in range(2):
        bits.append((cp >> (1 - i)) & 1)
    bits.append(res)
    w = 0
    for b in bits:
        w = (w << 1) | b
    return w


def encode_layer2_bytes(l2: Layer2Config) -> bytes:
    v = pack_layer2_48(l2)
    return v.to_bytes(6, "big")


LAYER2_SHORT_FORM = 0x6F  # 0b01101111 control-emitted short header


def layer2_matches_short_form_defaults(l2: Layer2Config, l1: Layer1Config) -> bool:
    """True if full Layer2 equals session defaults (emit 0x6F)."""
    d = Layer2Config()
    d.transmission_type = 1
    d.optimal_split = 8
    d.decimal_position = 2
    d.reserved = 1
    d.compound_prefix = l2.compound_prefix  # must match for short?
    # Session defaults: compare all fields except compound_prefix from batch intent
    return (
        l2.transmission_type == 1
        and l2.optimal_split == 8
        and l2.decimal_position == 2
        and l2.reserved == 1
        and not l2.enquiry_bell
        and not l2.acknowledge_bell
        and l2.group_sep == 0
        and l2.record_sep == 0
        and l2.file_sep == 0
        and (l2.entity_id & 0x1F) == (l1.sub_entity_id & 0x1F)
        and l2.currency_code == 0
        and l2.rounding_balance == 0
        and l2.scaling_factor_index == 0
    )


def serialise(record: TransactionRecord, S: int, l1: Layer1Config, l2: Layer2Config) -> int:
    """Pack TransactionRecord to 40-bit integer (MSB = spec bit 1)."""
    if record.account_pair == 0xF:
        if not l1.compound_mode_active:
            raise EncoderError("account_pair 1111 requires compound_mode_active in session")
        if (l2.compound_prefix & 0x3) == 0:
            raise EncoderError("account_pair 1111 requires compound_prefix != 00 in batch")
        st = record.continuation_subtype if record.continuation_subtype is not None else 0
        if st & ~0x3:
            raise EncoderError("continuation_subtype must be 0..3")
        bl = (
            (0xF << 4)
            | ((st >> 1) << 3)
            | ((st & 1) << 2)
            | ((record.completeness & 1) << 1)
            | int(record.extension_flag)
        )
    else:
        bl = (
            ((record.account_pair & 0xF) << 4)
            | ((record.direction & 1) << 3)
            | ((record.status & 1) << 2)
            | ((record.completeness & 1) << 1)
            | int(record.extension_flag)
        )
    A = record.multiplicand & ((1 << (25 - S)) - 1)
    r = record.multiplier & ((1 << S) - 1)
    value_25 = (A << S) | r
    if not record.rounding_flag and record.rounding_dir:
        raise EncoderError("invalid rounding state: bit26=0 bit27=1")
    flags = (
        (int(record.rounding_flag) << 6)
        | ((record.rounding_dir & 1) << 5)
        | ((record.split_order & 1) << 4)
        | ((record.direction & 1) << 3)
        | ((record.status & 1) << 2)
        | ((record.debit_credit & 1) << 1)
        | int(record.quantity_present)
    )
    return (value_25 << 15) | (flags << 8) | bl


def to_bit_string(n: int) -> str:
    b = format(n & ((1 << 40) - 1), "040b")
    return f"{b[0:17]} {b[17:25]} {b[25:32]} {b[32:36]} {b[36]} {b[37]} {b[38]} {b[39]}"


def to_hex(n: int) -> str:
    return (n & ((1 << 40) - 1)).to_bytes(5, "big").hex().upper()
