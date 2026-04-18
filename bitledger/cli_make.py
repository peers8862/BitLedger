"""`make` (primary BitLedger plan), `suggest-sf` (alias), `check-amount` (verification printout)."""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Tuple

from bitledger import decoder, encoder
from bitledger.cli_encode import apply_encode_overrides
from bitledger.cli_profile import effective_profile_path
from bitledger.errors import EncoderError, ProfileError
from bitledger.models import Layer1Config, Layer2Config
from bitledger.profiles import load_profile


def parse_amount_string(raw: str) -> Decimal:
    """Strip grouping; parse as Decimal (no float)."""
    s = raw.strip().replace(",", "").replace("_", "")
    if not s:
        raise InvalidOperation("empty amount")
    return Decimal(s)


def _rounding_bits_label(rf: int, rd: int) -> str:
    if not rf and not rd:
        return "00  exact (no rounding)"
    if rf and not rd:
        return "10  rounded down (true amount ≥ decoded wire value)"
    if rf and rd:
        return "11  rounded up (true amount ≤ decoded wire value)"
    return "01  INVALID (rejected by protocol)"


def _try_encode_value(
    amt: Decimal,
    sf: int,
    dp: int,
    pair: int,
    S: int,
) -> tuple[int, int, int, int, int] | None:
    try:
        return encoder.encode_value(amt, sf, dp, pair, S)
    except EncoderError:
        return None


def find_smallest_sf(
    amt: Decimal,
    dp: int,
    pair: int,
    S: int,
    lo: int,
    hi: int,
    *,
    legacy_first_success: bool = False,
) -> tuple[int, tuple[int, int, int, int, int]] | None:
    """
    Pick an SF index in [lo, hi] for which encode_value succeeds.

    By default (legacy_first_success=False): prefer the smallest index that yields
    rounding_flag=0 (exact); if none, the smallest index with any valid encoding.
    When legacy_first_success=True: first ascending index with any valid encoding
    (previous CLI behaviour).
    """
    table_hi = len(encoder.SCALING_FACTORS) - 1
    hi = min(hi, table_hi)
    lo = max(0, lo)
    if legacy_first_success:
        for sf in range(lo, hi + 1):
            got = _try_encode_value(amt, sf, dp, pair, S)
            if got is not None:
                return sf, got
        return None
    for sf in range(lo, hi + 1):
        got = _try_encode_value(amt, sf, dp, pair, S)
        if got is not None and got[3] == 0:
            return sf, got
    for sf in range(lo, hi + 1):
        got = _try_encode_value(amt, sf, dp, pair, S)
        if got is not None:
            return sf, got
    return None


@dataclass(frozen=True)
class EncodingPlan:
    """Resolved numeric plan + CLI context for make / check-amount."""

    amount: Decimal
    sf: int
    dp: int
    pair: int
    S: int
    N: int
    A: int
    r: int
    rf: int
    rd: int
    profile: str | None
    emit_l2: str
    currency: int | None
    direction: int
    status: int
    debit_credit: int
    split_order: int
    sf_banner: str | None  # e.g. line printed before report when SF was searched


def resolve_encoding_plan(
    ns: argparse.Namespace,
) -> Tuple[EncodingPlan, None] | Tuple[None, Tuple[int, str]]:
    """Returns (plan, None) on success, or (None, (exit_code, stderr_message))."""
    l1 = Layer1Config()
    l2 = Layer2Config()
    pp = effective_profile_path(ns)
    profile_for_plan: str | None = None
    if pp:
        try:
            l1, l2 = load_profile(pp)
        except ProfileError as e:
            return None, (2, str(e))
        profile_for_plan = str(pp.resolve())
    try:
        apply_encode_overrides(ns, l1, l2)
    except EncoderError as e:
        return None, (2, str(e))

    try:
        amt = parse_amount_string(ns.amount)
    except (InvalidOperation, ValueError) as e:
        return None, (1, f"Invalid --amount: {e}")

    dp = l2.decimal_position & 7
    S = l2.optimal_split & 0xF
    pair = ns.account_pair & 0xF
    lo = int(ns.min_sf)
    hi = int(ns.max_sf)
    if hi < lo:
        return None, (1, "--max-sf must be >= --min-sf")

    sf_banner: str | None = None
    if ns.sf is not None:
        sf = int(ns.sf) & 0x7F
        got = _try_encode_value(amt, sf, dp, pair, S)
        if got is None:
            return None, (
                2,
                f"No valid encoding at sf={sf} (overflow, unsupported dp, or sf_index out of table).",
            )
        N, A, r, rf, rd = got
    else:
        legacy = bool(getattr(ns, "legacy_sf_search", False))
        found = find_smallest_sf(
            amt, dp, pair, S, lo, hi, legacy_first_success=legacy
        )
        if found is None:
            return None, (
                2,
                f"No SF in {lo}..{min(hi, len(encoder.SCALING_FACTORS) - 1)} yields a valid encoding "
                f"(try raising --max-sf, changing --dp, or reducing precision).",
            )
        sf, (N, A, r, rf, rd) = found
        rmax = min(hi, len(encoder.SCALING_FACTORS) - 1)
        if legacy:
            sf_banner = f"(Smallest SF in range {lo}..{rmax}: {sf})"
        else:
            sf_banner = (
                f"(SF search {lo}..{rmax}: index {sf}; prefer smallest exact encoding, "
                f"else smallest that fits)"
            )

    emit = ns.emit_l2
    cur = l2.currency_code & 0x3F
    cur_arg = cur if cur != 0 else None

    plan = EncodingPlan(
        amount=amt,
        sf=sf,
        dp=dp,
        pair=pair,
        S=S,
        N=N,
        A=A,
        r=r,
        rf=rf,
        rd=rd,
        profile=profile_for_plan,
        emit_l2=emit,
        currency=cur_arg,
        direction=ns.direction,
        status=ns.status,
        debit_credit=ns.debit_credit,
        split_order=ns.split_order,
        sf_banner=sf_banner,
    )
    return plan, None


def _emit_make_report(plan: EncodingPlan) -> None:
    SF = encoder.SCALING_FACTORS[plan.sf]
    R = plan.amount * (Decimal(10) ** plan.dp) / SF
    mode = encoder.rounding_mode(plan.pair)
    decoded = decoder.decode_value(
        plan.A, plan.r, plan.S, plan.sf, plan.dp, quantity_present=False
    )
    delta = plan.amount - decoded

    if plan.sf_banner:
        print(plan.sf_banner + "\n")

    print("── BitLedger make (plan → record) ──")
    print(f"Amount (parsed):     {plan.amount}")
    print(f"Wire scaling:        SF index = {plan.sf}  (×{SF} = 10^{plan.sf})")
    print(f"Decimal position:    dp = {plan.dp}  (divide by 10^{plan.dp} on decode)")
    print(f"Optimal split S:     {plan.S}")
    print(f"Account pair:        {plan.pair:#04b}  rounding_mode = {mode!r}")
    print(f"R = amount×10^dp/SF: {R}")
    print(f"Stored integer N:    {plan.N}  (max wire 33,554,431)")
    print(f"Decomposed:          A = {plan.A}   r = {plan.r}   (N = (A<<S)|r = {(plan.A << plan.S) | plan.r})")
    print(f"Bits 26–27:          {_rounding_bits_label(plan.rf, plan.rd)}")
    if plan.rf:
        print(f"Decoded wire value: {decoded}")
        print(f"Delta (typed − decoded): {delta}")
    else:
        print("Decoded wire value:  matches typed amount (exact).")
    print("── Suggested encode ──")
    parts = ["encode"]
    if plan.profile:
        parts += ["--profile", plan.profile]
    parts += ["--emit-l2", plan.emit_l2, "--amount", str(plan.amount)]
    parts += ["--sf", str(plan.sf), "--dp", str(plan.dp), "--optimal-split", str(plan.S)]
    parts += ["--account-pair", str(plan.pair)]
    parts += ["--direction", str(plan.direction), "--status", str(plan.status)]
    parts += ["--debit-credit", str(plan.debit_credit), "--split-order", str(plan.split_order)]
    if plan.currency is not None:
        parts += ["--currency", str(plan.currency)]
    if plan.rf:
        parts += ["--accept-rounding"]
    line = "bitledger " + " ".join(shlex.quote(p) for p in parts)
    print(line)


def suggested_encode_argv(plan: EncodingPlan) -> list[str]:
    parts = ["encode"]
    if plan.profile:
        parts += ["--profile", plan.profile]
    parts += ["--emit-l2", plan.emit_l2, "--amount", str(plan.amount)]
    parts += ["--sf", str(plan.sf), "--dp", str(plan.dp), "--optimal-split", str(plan.S)]
    parts += ["--account-pair", str(plan.pair)]
    parts += ["--direction", str(plan.direction), "--status", str(plan.status)]
    parts += ["--debit-credit", str(plan.debit_credit), "--split-order", str(plan.split_order)]
    if plan.currency is not None:
        parts += ["--currency", str(plan.currency)]
    if plan.rf:
        parts += ["--accept-rounding"]
    return parts


def plan_as_json_dict(plan: EncodingPlan) -> dict:
    SF = encoder.SCALING_FACTORS[plan.sf]
    R = plan.amount * (Decimal(10) ** plan.dp) / SF
    mode = encoder.rounding_mode(plan.pair)
    decoded = decoder.decode_value(
        plan.A, plan.r, plan.S, plan.sf, plan.dp, quantity_present=False
    )
    return {
        "amount": str(plan.amount),
        "sf_index": plan.sf,
        "scaling_factor": str(SF),
        "dp": plan.dp,
        "optimal_split": plan.S,
        "account_pair": plan.pair,
        "rounding_mode": mode,
        "R": str(R),
        "N": plan.N,
        "A": plan.A,
        "r": plan.r,
        "rounding_flag": bool(plan.rf),
        "rounding_dir": plan.rd,
        "bits_26_27": _rounding_bits_label(plan.rf, plan.rd),
        "decoded_wire_value": str(decoded),
        "delta_typed_minus_decoded": str(plan.amount - decoded),
        "sf_search_banner": plan.sf_banner,
        "suggested_encode_argv": suggested_encode_argv(plan),
    }


def _emit_check_amount_report(plan: EncodingPlan) -> None:
    """Verification-first printout (no copy-paste encode block)."""
    SF = encoder.SCALING_FACTORS[plan.sf]
    R = plan.amount * (Decimal(10) ** plan.dp) / SF
    mode = encoder.rounding_mode(plan.pair)
    decoded = decoder.decode_value(
        plan.A, plan.r, plan.S, plan.sf, plan.dp, quantity_present=False
    )
    delta = plan.amount - decoded

    print("── BitLedger check-amount (verification) ──")
    print("Use this to confirm amount → N, rounding, and SF/dp/S before you `make` or `encode`.")
    print()
    if plan.rf:
        print("STATUS:  ROUNDING on encode — bits 26–27 will be set (not exact).")
    else:
        print("STATUS:  EXACT — no rounding; bits 26–27 = 00.")
    print()
    if plan.sf_banner:
        print(plan.sf_banner)
        print()
    print(f"Amount (parsed):      {plan.amount}")
    print(f"SF index / scale:     {plan.sf}  (×{SF})")
    print(f"dp / S / pair:        dp={plan.dp}   S={plan.S}   pair={plan.pair:#04b}  mode={mode!r}")
    print(f"R = amount×10^dp/SF:  {R}")
    print(f"Integer N (≤33.55M):  {plan.N}")
    print(f"A / r:                A={plan.A}   r={plan.r}   composite N={(plan.A << plan.S) | plan.r}")
    print(f"Bits 26–27:           {_rounding_bits_label(plan.rf, plan.rd)}")
    if plan.rf:
        print(f"Decoded after wire:   {decoded}")
        print(f"Delta (typed − dec):  {delta}")
    print()
    print("Next: `bitledger make` with the same flags for the full plan + suggested `encode` line.")


def cmd_make(ns: argparse.Namespace) -> int:
    resolved = resolve_encoding_plan(ns)
    if resolved[0] is None:
        code, msg = resolved[1]
        print(msg, file=sys.stderr)
        return code
    plan = resolved[0]
    if getattr(ns, "json", False):
        print(json.dumps(plan_as_json_dict(plan), indent=2))
        return 0
    _emit_make_report(plan)
    return 0


def cmd_check_amount(ns: argparse.Namespace) -> int:
    resolved = resolve_encoding_plan(ns)
    if resolved[0] is None:
        code, msg = resolved[1]
        print(msg, file=sys.stderr)
        return code
    _emit_check_amount_report(resolved[0])
    return 0


def add_make_arguments(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--profile",
        help="Profile JSON path (overrides BITLEDGER_PROFILE and `bitledger profile use` active pointer)",
    )
    p.add_argument(
        "--amount",
        required=True,
        metavar="DECIMAL",
        help="Full real amount; commas/underscores allowed (e.g. 24,456,346,932.00)",
    )
    p.add_argument(
        "--sf",
        type=int,
        default=None,
        help="If set, plan for this SF index only (no search)",
    )
    p.add_argument(
        "--min-sf",
        type=int,
        default=0,
        help="When searching, minimum SF index (default 0)",
    )
    p.add_argument(
        "--max-sf",
        type=int,
        default=127,
        help="When searching, maximum SF index (default 127; table- and wire-limited)",
    )
    p.add_argument(
        "--legacy-sf-search",
        action="store_true",
        help="When searching SF: first ascending index with any valid encoding (ignore exact-first)",
    )
    p.add_argument(
        "--emit-l2",
        choices=("auto", "short", "full"),
        default="auto",
        help="(make / encode) shown in suggested encode line",
    )
    p.add_argument("--sender", help="Layer1 sender id (profile override)")
    p.add_argument("--subentity", type=int, help="Layer1 sub-entity 0-31")
    p.add_argument("--compound-session", type=int, choices=(0, 1))
    p.add_argument("--perms", type=int)
    p.add_argument("--currency", type=int, help="Layer2 currency_code (override profile)")
    p.add_argument("--txtype", type=int, choices=(1, 2, 3))
    p.add_argument("--compound-prefix", type=int)
    p.add_argument("--sep-group", type=int)
    p.add_argument("--sep-record", type=int)
    p.add_argument("--sep-file", type=int)
    p.add_argument("--optimal-split", type=int)
    p.add_argument("--dp", type=int)
    p.add_argument("--account-pair", type=int, default=4)
    p.add_argument("--direction", type=int, default=0)
    p.add_argument("--status", type=int, default=0)
    p.add_argument("--debit-credit", type=int, default=0)
    p.add_argument("--split-order", type=int, default=0)
