"""Structured rounding observations and human-readable aggregates (CLI)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from bitledger import decoder


@dataclass(frozen=True)
class RoundingObservation:
    """One encode/decode event at a known scale (SF index and decimal wire code)."""

    true_value: Decimal | None  # None when only the wire is known (decode without compare)
    wire_value: Decimal
    delta: Decimal | None  # true_value − wire_value when comparable; else None
    sf_index: int
    decimal_position_wire: int
    rounding_flag: bool
    rounding_dir: int
    account_pair: int
    quantity_present: bool


def decode_wire_value(
    rec_multiplicand: int,
    rec_multiplier: int,
    S: int,
    sf_index: int,
    dp_wire: int,
    quantity_present: bool,
) -> Decimal:
    return decoder.decode_value(
        rec_multiplicand,
        rec_multiplier,
        S,
        sf_index & 0x7F,
        dp_wire & 7,
        quantity_present,
    )


def observation_from_encode_amount(
    true_value: Decimal,
    *,
    A: int,
    r: int,
    S: int,
    sf_index: int,
    dp_wire: int,
    rf: int,
    rd: int,
    account_pair: int,
    quantity_present: bool,
) -> RoundingObservation:
    wire = decode_wire_value(A, r, S, sf_index, dp_wire, quantity_present)
    delta = true_value - wire
    return RoundingObservation(
        true_value=true_value,
        wire_value=wire,
        delta=delta,
        sf_index=sf_index & 0x7F,
        decimal_position_wire=dp_wire & 7,
        rounding_flag=bool(rf),
        rounding_dir=rd & 1,
        account_pair=account_pair & 0xF,
        quantity_present=quantity_present,
    )


def observation_from_decode(
    *,
    compare_value: Decimal | None,
    A: int,
    r: int,
    S: int,
    sf_index: int,
    dp_wire: int,
    rf: bool,
    rd: int,
    account_pair: int,
    quantity_present: bool,
) -> RoundingObservation:
    wire = decode_wire_value(A, r, S, sf_index, dp_wire, quantity_present)
    if compare_value is None:
        return RoundingObservation(
            true_value=None,
            wire_value=wire,
            delta=None,
            sf_index=sf_index & 0x7F,
            decimal_position_wire=dp_wire & 7,
            rounding_flag=bool(rf),
            rounding_dir=rd & 1,
            account_pair=account_pair & 0xF,
            quantity_present=quantity_present,
        )
    delta = compare_value - wire
    return RoundingObservation(
        true_value=compare_value,
        wire_value=wire,
        delta=delta,
        sf_index=sf_index & 0x7F,
        decimal_position_wire=dp_wire & 7,
        rounding_flag=bool(rf),
        rounding_dir=rd & 1,
        account_pair=account_pair & 0xF,
        quantity_present=quantity_present,
    )


def observation_to_jsondict(o: RoundingObservation) -> dict[str, object]:
    """Machine-readable row for `make --json` (Decimal → str)."""
    return {
        "true_value": None if o.true_value is None else str(o.true_value),
        "wire_value": str(o.wire_value),
        "delta_typed_minus_wire": None if o.delta is None else str(o.delta),
        "sf_index": o.sf_index,
        "decimal_position_wire": o.decimal_position_wire,
        "rounding_flag": o.rounding_flag,
        "rounding_dir": o.rounding_dir,
        "account_pair": o.account_pair,
        "quantity_present": o.quantity_present,
    }


def format_aggregate(observations: list[RoundingObservation]) -> str:
    """Table plus totals: signed residual (typed − wire), counts, means where delta known."""
    lines: list[str] = [
        "── Rounding report (typed − wire) ──",
        "  Scale: SF_index = k (×10^k); dp = decimal_position wire (divide decode by 10^dp); "
        "qty=quantity_present (1 → N=A×r at decode).",
    ]
    if not observations:
        lines.append("  (no observations)")
        return "\n".join(lines) + "\n"

    with_delta = [o for o in observations if o.delta is not None]
    n = len(observations)
    n_exact = sum(1 for o in observations if not o.rounding_flag)
    n_round = n - n_exact

    for i, o in enumerate(observations, start=1):
        tv = "—" if o.true_value is None else str(o.true_value)
        dv = "—" if o.delta is None else str(o.delta)
        lines.append(
            f"  #{i}  k={o.sf_index}  dp={o.decimal_position_wire}  pair={o.account_pair:#04b}  "
            f"qty={int(o.quantity_present)}  rf={int(o.rounding_flag)} rd={o.rounding_dir}"
        )
        lines.append(f"       typed={tv}  wire={o.wire_value}  Δ={dv}")

    lines.append(f"  Count: {n} total  ({n_exact} exact, {n_round} non-exact on wire)")

    if with_delta:
        deltas: list[Decimal] = [o.delta for o in with_delta if o.delta is not None]
        total = sum(deltas, Decimal(0))
        mean = total / len(deltas)
        pos = sum(1 for d in deltas if d > 0)
        neg = sum(1 for d in deltas if d < 0)
        zero = sum(1 for d in deltas if d == 0)
        lines.append(
            f"  Δ sum (typed−wire): {total}   mean: {mean}   "
            f"(Δ>0: {pos},  Δ<0: {neg},  Δ=0: {zero})"
        )
    else:
        lines.append(
            "  Δ sum / mean: N/A (pass a typed amount, e.g. encode with --amount or "
            "decode with --compare-amount DECIMAL)."
        )

    return "\n".join(lines) + "\n"
