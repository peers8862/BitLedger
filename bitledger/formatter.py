"""Human-readable formatters for CLI (TASK-2.09)."""

from __future__ import annotations

from decimal import Decimal

from bitledger import decoder
from bitledger.currencies import lookup_by_index
from bitledger.encoder import to_bit_string, to_hex
from bitledger.models import Layer1Config, Layer2Config, SessionState, TransactionRecord

# spec bits 33–36 account pair (Layer 3 BitLedger block)
_PAIR_NAMES: dict[int, str] = {
    0: "Op Expense / Asset",
    1: "Op Expense / Liability",
    2: "Non-Op Expense / Asset",
    3: "Non-Op Expense / Liability",
    4: "Op Income / Asset",
    5: "Op Income / Liability",
    6: "Non-Op Income / Asset",
    7: "Non-Op Income / Liability",
    8: "Asset / Liability",
    9: "Asset / Equity",
    10: "Liability / Equity",
    11: "Asset / Asset",
    12: "Liability / Liability",
    13: "Equity / Equity",
    14: "Correction / Void",
    15: "Compound continuation (1111)",
}


def format_binary(n: int) -> str:
    """40-bit groups: 17 | 8 | 7 | 4 | 1 | 1 | 1 | 1 (TASK-2.09 pipe separators)."""
    return to_bit_string(n & ((1 << 40) - 1)).replace(" ", " | ")


def format_hex(n: int) -> str:
    """Uppercase hex with 0x prefix (10 hex digits = 5 bytes)."""
    h = to_hex(n & ((1 << 40) - 1))
    return "0x" + h


def account_pair_label(code: int) -> str:
    return _PAIR_NAMES.get(code & 0xF, f"unknown pair {code}")


def _pair_leg_labels(code: int) -> tuple[str, str]:
    """Two account names for double-entry lines (split on ' / ')."""
    label = account_pair_label(code & 0xF)
    if " / " in label:
        a, b = label.split(" / ", 1)
        return a.strip(), b.strip()
    return label, "Counterparty"


def format_layer1_header(cfg: Layer1Config) -> str:
    lines = [
        "────────────────────────────────────────",
        "LAYER 1 — Session",
        f"  protocol_version={cfg.protocol_version}",
        f"  permissions R/W/C/R = {cfg.perm_read}/{cfg.perm_write}/{cfg.perm_correct}/{cfg.perm_represent}",
        f"  split_order_default={cfg.default_split_order}  opposing_explicit={cfg.opposing_account_explicit}",
        f"  compound_mode_active={cfg.compound_mode_active}  bitledger_optional={cfg.bitledger_optional}",
        f"  sender_id=0x{cfg.sender_id:08X}  sub_entity_id={cfg.sub_entity_id}",
        "────────────────────────────────────────",
    ]
    return "\n".join(lines) + "\n"


def format_layer2_header(cfg: Layer2Config) -> str:
    ccy = lookup_by_index(cfg.currency_code & 0x3F)
    sym = str(ccy["symbol"] or ccy["code"] or "?")
    lines = [
        "────────────────────────────────────────",
        "LAYER 2 — Batch",
        f"  transmission_type={cfg.transmission_type}  SF_index={cfg.scaling_factor_index}",
        f"  optimal_split={cfg.optimal_split}  decimal_position_wire={cfg.decimal_position}",
        f"  currency_index={cfg.currency_code} ({sym})  compound_prefix={cfg.compound_prefix}",
        f"  group_sep={cfg.group_sep}  record_sep={cfg.record_sep}  file_sep={cfg.file_sep}",
        f"  entity_id={cfg.entity_id}  rounding_balance={cfg.rounding_balance}",
        "────────────────────────────────────────",
    ]
    return "\n".join(lines) + "\n"


def format_journal(
    record: TransactionRecord,
    session: SessionState,
    *,
    n40: int | None = None,
    description: str = "",
) -> str:
    """
    README-style journal block (Human-Readable Output). Amounts use Decimal via decode_value.
    Optional n40 adds Binary/Hex lines like the README mock; optional description fills the narrative line.
    """
    bar = "─" * 65
    l1 = session.layer1
    l2 = session.layer2
    S = session.current_split
    sf_i = l2.scaling_factor_index & 0x7F
    dp = l2.decimal_position & 7
    amt = decoder.decode_value(
        record.multiplicand,
        record.multiplier,
        S,
        sf_i,
        dp,
        record.quantity_present,
    )
    ccy = lookup_by_index(l2.currency_code & 0x3F)
    sym = str(ccy["symbol"] or ccy["code"] or "$")
    code = ccy.get("code") or ""
    ccy_disp = str(code) if code else f"index {l2.currency_code}"
    q = Decimal("0.01")
    if amt == amt.to_integral_value():
        amt_s = format(amt.quantize(Decimal("1")), "f").rstrip("0").rstrip(".") or "0"
    else:
        amt_s = format(amt.quantize(q), "f")

    leg1, leg2 = _pair_leg_labels(record.account_pair)
    # Primary posting follows debit_credit (1 = debit-like first line per README expense/AP example).
    if record.debit_credit:
        line_debit = f"DEBIT    {leg1:<26} {ccy_disp:<4} {amt_s:>12}"
        line_credit = f"CREDIT   {leg2:<26} {ccy_disp:<4} {amt_s:>12}"
    else:
        line_credit = f"CREDIT   {leg1:<26} {ccy_disp:<4} {amt_s:>12}"
        line_debit = f"DEBIT    {leg2:<26} {ccy_disp:<4} {amt_s:>12}"

    sub = l1.sub_entity_id & 0x1F
    sess_line = f"Session : sender 0x{l1.sender_id:08X}  /  sub-entity {sub:02d}"
    grp = l2.group_sep & 0xF
    recn = l2.record_sep & 0x1F
    batch_line = f"Batch   : Group {grp:02d}  /  Record {recn:03d}  /  Currency: {ccy_disp}"

    st = "Accrued — not yet settled" if record.status else "Settled — past"
    prec = "Rounded" if record.rounding_flag else "Exact"
    desc = description.strip() or "(no description)"

    lines = [
        bar,
        "BITLEDGER JOURNAL ENTRY",
        sess_line,
        batch_line,
        bar,
        line_debit,
        line_credit,
        bar,
        f"Description : {desc}",
        f"Status      : {st}",
        f"Precision   : {prec}",
    ]
    if record.account_pair == 0xF and record.continuation_subtype is not None:
        stypes = ("Standard", "Correcting", "Reversal", "Cross-batch")
        lines.append(f"Continuation: {stypes[record.continuation_subtype]}")
    lines.append(bar)
    if n40 is not None:
        lines.append(f"Binary  : {to_bit_string(n40 & ((1 << 40) - 1))}")
        hx = to_hex(n40 & ((1 << 40) - 1))
        spaced = " ".join(hx[i : i + 2] for i in range(0, 10, 2))
        lines.append(f"Hex     : {spaced}")
        lines.append(bar)
    return "\n".join(lines) + "\n"


def format_record_summary(rec: TransactionRecord, n40: int) -> str:
    """Compact block for CLI (headers omitted)."""
    lines = [
        "BITLEDGER RECORD",
        f"  account_pair={rec.account_pair:#04b}  dir={rec.direction}  status={rec.status}",
        f"  completeness={rec.completeness}  qty_present={rec.quantity_present}",
        f"  A={rec.multiplicand}  r={rec.multiplier}",
    ]
    if rec.continuation_subtype is not None:
        lines.append(f"  continuation_subtype={rec.continuation_subtype}")
    lines.append(f"Binary : {format_binary(n40)}")
    hx = to_hex(n40 & ((1 << 40) - 1))
    lines.append(f"Hex    : {' '.join(hx[i : i + 2] for i in range(0, 10, 2))}  ({format_hex(n40)})")
    return "\n".join(lines) + "\n"
