"""CLI entry — setup | encode | decode | simulate."""

from __future__ import annotations

import argparse
import sys
from decimal import InvalidOperation
from pathlib import Path

from bitledger import decoder, encoder, formatter
from bitledger.cli_encode import apply_encode_overrides
from bitledger.cli_make import (
    add_make_arguments,
    cmd_check_amount,
    cmd_make,
    find_smallest_sf,
    parse_amount_string,
)
from bitledger.errors import DecoderError, EncoderError, ProfileError
from bitledger.models import Layer1Config, Layer2Config, SessionState, TransactionRecord
from bitledger.cli_profile import add_profile_cli, effective_profile_path
from bitledger.profiles import load_profile, save_profile
from bitledger.setup_wizard import run_wizard
from bitledger.simulator import simulate_record_roundtrip


def _write_bl(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def cmd_setup(ns: argparse.Namespace) -> int:
    l1, l2 = run_wizard()
    if ns.out:
        save_profile(Path(ns.out), ns.name or "default", l1, l2, force=bool(ns.force))
    if not ns.quiet:
        print(formatter.format_layer1_header(l1), end="")
        print(formatter.format_layer2_header(l2), end="")
        print("Profile saved:", ns.out or "(pass --out path.json)")
    return 0


def _emit_l2_choice(ns: argparse.Namespace, l1: Layer1Config, l2: Layer2Config) -> str:
    mode = ns.emit_l2
    if mode == "short":
        return "short"
    if mode == "full":
        return "full"
    return "short" if encoder.layer2_matches_short_form_defaults(l2, l1) else "full"


def cmd_encode(ns: argparse.Namespace) -> int:
    l1 = Layer1Config()
    l2 = Layer2Config()
    pp = effective_profile_path(ns)
    if pp:
        l1, l2 = load_profile(pp)
    try:
        apply_encode_overrides(ns, l1, l2)
    except EncoderError as e:
        print(str(e), file=sys.stderr)
        return 2
    if getattr(ns, "auto_sf", False) and ns.amount is None:
        print("--auto-sf requires --amount", file=sys.stderr)
        return 1
    if getattr(ns, "auto_sf", False) and getattr(ns, "sf", None) is not None:
        print("Do not combine --auto-sf with --sf (search replaces SF).", file=sys.stderr)
        return 1
    if getattr(ns, "auto_sf", False) and int(getattr(ns, "max_sf", 127)) < int(
        getattr(ns, "min_sf", 0)
    ):
        print("--max-sf must be >= --min-sf", file=sys.stderr)
        return 1
    if ns.amount is not None:
        try:
            amt = parse_amount_string(ns.amount)
        except (InvalidOperation, ValueError) as e:
            print(f"Invalid --amount: {e}", file=sys.stderr)
            return 1
        dp = l2.decimal_position & 7
        S = l2.optimal_split & 0xF
        pair = ns.account_pair & 0xF
        if getattr(ns, "auto_sf", False):
            lo = int(getattr(ns, "min_sf", 0))
            hi = int(getattr(ns, "max_sf", 127))
            found = find_smallest_sf(
                amt,
                dp,
                pair,
                S,
                lo,
                hi,
                legacy_first_success=bool(getattr(ns, "legacy_sf_search", False)),
            )
            if found is None:
                print(
                    f"No SF in {lo}..{hi} fits this amount (try make/check-amount, or raise --max-sf).",
                    file=sys.stderr,
                )
                return 2
            sf_chosen, _ = found
            l2.scaling_factor_index = sf_chosen
        try:
            _N, A, r, rf, rd = encoder.encode_value(
                amt,
                l2.scaling_factor_index & 0x7F,
                dp,
                pair,
                S,
            )
        except EncoderError as e:
            print(str(e), file=sys.stderr)
            return 2
        if rf and not getattr(ns, "accept_rounding", False):
            print(
                "Encode would round this amount (bits 26–27). "
                "Run `bitledger check-amount` / `bitledger make` with the same flags, "
                "then pass --accept-rounding to encode, or change SF/dp/account-pair.",
                file=sys.stderr,
            )
            return 2
        rec = TransactionRecord(
            multiplicand=A,
            multiplier=r,
            rounding_flag=bool(rf),
            rounding_dir=rd,
            split_order=ns.split_order,
            direction=ns.direction,
            status=ns.status,
            debit_credit=ns.debit_credit,
            quantity_present=bool(ns.quantity_present),
            account_pair=ns.account_pair,
            completeness=ns.completeness,
            extension_flag=bool(ns.extension_flag),
            continuation_subtype=ns.continuation_subtype,
        )
    else:
        rec = TransactionRecord(
            multiplicand=ns.A,
            multiplier=ns.r,
            rounding_flag=bool(ns.rounding_flag),
            rounding_dir=ns.rounding_dir,
            split_order=ns.split_order,
            direction=ns.direction,
            status=ns.status,
            debit_credit=ns.debit_credit,
            quantity_present=bool(ns.quantity_present),
            account_pair=ns.account_pair,
            completeness=ns.completeness,
            extension_flag=bool(ns.extension_flag),
            continuation_subtype=ns.continuation_subtype,
        )
    S = l2.optimal_split
    try:
        n40 = encoder.serialise(rec, S, l1, l2)
        blob = encoder.encode_layer1_bytes(l1)
        l2mode = _emit_l2_choice(ns, l1, l2)
        if l2mode == "short":
            blob += bytes([encoder.LAYER2_SHORT_FORM])
        else:
            blob += encoder.encode_layer2_bytes(l2)
        blob += n40.to_bytes(5, "big")
    except EncoderError as e:
        print(str(e), file=sys.stderr)
        return 2
    if ns.out:
        _write_bl(Path(ns.out), blob)
    if not ns.quiet:
        print(formatter.format_layer1_header(l1), end="")
        print(formatter.format_layer2_header(l2), end="")
        ss = SessionState(
            layer1=l1,
            layer2=l2,
            current_split=l2.optimal_split,
            current_currency=l2.currency_code,
            current_sf_index=l2.scaling_factor_index,
        )
        print(
            formatter.format_journal(
                rec, ss, n40=n40, description=getattr(ns, "description", "") or ""
            ),
            end="",
        )
        print(formatter.format_record_summary(rec, n40), end="")
        print(f"Wrote {len(blob)} bytes to {ns.out}" if ns.out else f"Emit {len(blob)} bytes (pass --out file.bl)")
    return 0


def cmd_decode(ns: argparse.Namespace) -> int:
    if ns.in_path:
        raw = Path(ns.in_path).read_bytes()
    elif ns.record_hex:
        try:
            raw = bytes.fromhex(ns.record_hex.replace(" ", ""))
        except ValueError as e:
            print(f"Invalid hex: {e}", file=sys.stderr)
            return 1
    else:
        print("decode: provide positional HEX or --in file.bl", file=sys.stderr)
        return 1
    try:
        l1 = decoder.unpack_layer1(raw[:8])
        rest = raw[8:]
        if rest and rest[0] == encoder.LAYER2_SHORT_FORM:
            l2 = Layer2Config()
            body = rest[1:]
        else:
            l2 = decoder.unpack_layer2(rest[:6])
            body = rest[6:]
        n40 = int.from_bytes(body[:5], "big")
        rec = decoder.unpack_record(n40, l2.optimal_split)
        decoder.validate_compound_context(rec, l1, l2)
    except (DecoderError, OSError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2
    if not ns.quiet:
        ss = SessionState(
            layer1=l1,
            layer2=l2,
            current_split=l2.optimal_split,
            current_currency=l2.currency_code,
            current_sf_index=l2.scaling_factor_index,
        )
        print(formatter.format_layer1_header(l1), end="")
        print(formatter.format_layer2_header(l2), end="")
        print(formatter.format_journal(rec, ss, n40=n40), end="")
        print(formatter.format_record_summary(rec, n40), end="")
    return 0


def cmd_simulate(ns: argparse.Namespace) -> int:
    pp = effective_profile_path(ns)
    l1, l2 = load_profile(pp) if pp else (Layer1Config(), Layer2Config())
    rec = TransactionRecord(
        multiplicand=1,
        multiplier=197,
        rounding_flag=False,
        direction=0,
        status=0,
        debit_credit=0,
        account_pair=4,
        completeness=0,
    )
    out = simulate_record_roundtrip(rec, l2.optimal_split, l1, l2)
    if not ns.quiet:
        print("Roundtrip OK:", out.multiplicand, out.multiplier, out.account_pair)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="bitledger")
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("setup", help="Configure Layer1/Layer2 profile (interactive)")
    ps.add_argument("--quiet", action="store_true")
    ps.add_argument("--out", help="Write profile JSON path")
    ps.add_argument("--name", default="default")
    ps.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing profile named default at --out",
    )
    ps.set_defaults(func=cmd_setup)

    pe = sub.add_parser("encode", help="Emit .bl bytes (L1+L2+L3)")
    pe.add_argument("--quiet", action="store_true")
    pe.add_argument(
        "--profile",
        help="Profile JSON (overrides BITLEDGER_PROFILE and active pointer from `profile use`)",
    )
    pe.add_argument("--out", help="Binary .bl output path")
    pe.add_argument(
        "--emit-l2",
        choices=("auto", "short", "full"),
        default="auto",
        help="Layer2: 0x6F short-form, full 6-byte, or auto when defaults match session",
    )
    pe.add_argument("--sender", help="Layer1 sender id (e.g. 0xDEADBEEF)")
    pe.add_argument("--subentity", type=int, help="Layer1 sub-entity 0-31")
    pe.add_argument("--compound-session", type=int, choices=(0, 1), help="Layer1 compound_mode_active")
    pe.add_argument("--perms", type=int, help="Layer1 core permissions nibble 0-15 (R/W/C/R)")
    pe.add_argument(
        "--sf",
        type=int,
        default=None,
        help="Layer2 scaling_factor_index 0-127 (do not combine with --auto-sf)",
    )
    pe.add_argument(
        "--auto-sf",
        action="store_true",
        help="With --amount: search --min-sf..--max-sf for SF (default: smallest exact encoding, else smallest that fits; overrides profile/--sf)",
    )
    pe.add_argument(
        "--min-sf",
        type=int,
        default=0,
        help="With --auto-sf: start of SF search (default 0)",
    )
    pe.add_argument(
        "--max-sf",
        type=int,
        default=127,
        help="With --auto-sf: end of SF search (default 127; table- and wire-limited)",
    )
    pe.add_argument(
        "--legacy-sf-search",
        action="store_true",
        help="With --auto-sf: first ascending SF with any valid encoding (old behaviour)",
    )
    pe.add_argument(
        "--accept-rounding",
        action="store_true",
        help="With --amount: allow encode when rounding_flag would be set",
    )
    pe.add_argument("--currency", type=int, help="Layer2 currency_code 0-63")
    pe.add_argument("--txtype", type=int, choices=(1, 2, 3), help="Layer2 transmission_type")
    pe.add_argument("--compound-prefix", type=int, help="Layer2 compound_prefix 0-3")
    pe.add_argument("--sep-group", type=int, help="Layer2 group_sep (4-bit)")
    pe.add_argument("--sep-record", type=int, help="Layer2 record_sep (5-bit)")
    pe.add_argument("--sep-file", type=int, help="Layer2 file_sep (3-bit)")
    pe.add_argument("--optimal-split", type=int, help="Layer2 optimal_split 0-15")
    pe.add_argument("--dp", type=int, help="Layer2 decimal_position wire code 0-7")
    pe.add_argument(
        "--amount",
        metavar="DECIMAL",
        help="Monetary amount (Decimal); derives N,A,r from profile SF, --dp, optimal split, and --account-pair rounding mode",
    )
    pe.add_argument(
        "--description",
        default="",
        help="Narrative line in journal output (encode/decode display)",
    )
    pe.add_argument("--A", type=int, default=1)
    pe.add_argument("--r", type=int, default=197)
    pe.add_argument("--rounding-flag", type=int, default=0)
    pe.add_argument("--rounding-dir", type=int, default=0)
    pe.add_argument("--split-order", type=int, default=0)
    pe.add_argument("--direction", type=int, default=0)
    pe.add_argument("--status", type=int, default=0)
    pe.add_argument("--debit-credit", type=int, default=0)
    pe.add_argument("--quantity-present", type=int, default=0)
    pe.add_argument("--account-pair", type=int, default=4)
    pe.add_argument("--completeness", type=int, default=0)
    pe.add_argument("--extension-flag", type=int, default=0)
    pe.add_argument("--continuation-subtype", type=int, default=None)
    pe.set_defaults(func=cmd_encode)

    pd = sub.add_parser("decode", help="Decode .bl file or hex (L1+L2+L3)")
    pd.add_argument("--quiet", action="store_true")
    pd.add_argument("--in", dest="in_path", help="Binary .bl file path")
    pd.add_argument("record_hex", nargs="?", default=None, help="Continuous hex (optional if --in)")
    pd.set_defaults(func=cmd_decode)

    pm = sub.add_parser("simulate", help="Encode/decode smoke test")
    pm.add_argument("--quiet", action="store_true")
    pm.add_argument("--profile")
    pm.set_defaults(func=cmd_simulate)

    pmk = sub.add_parser(
        "make",
        help="Primary: plan a BitLedger record — SF, N/A/r, rounding, copy-paste `encode` line",
    )
    add_make_arguments(pmk)
    pmk.add_argument(
        "--json",
        action="store_true",
        help="Emit encoding plan as JSON (stdout only)",
    )
    pmk.set_defaults(func=cmd_make)

    psf = sub.add_parser(
        "suggest-sf",
        help="Alias of make — same output (SF search in range unless --sf is set)",
    )
    add_make_arguments(psf)
    psf.add_argument("--json", action="store_true", help="Emit encoding plan as JSON")
    psf.set_defaults(func=cmd_make)

    pchk = sub.add_parser(
        "check-amount",
        help="Verify amount → SF/N/rounding (same flags as make); no suggested encode block",
    )
    add_make_arguments(pchk)
    pchk.set_defaults(func=cmd_check_amount)

    add_profile_cli(sub)

    ns = p.parse_args(argv)
    try:
        return ns.func(ns)
    except ProfileError as e:
        print(str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
