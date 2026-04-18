"""`bitledger profile list|use|show` and shared profile path resolution."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from bitledger.errors import ProfileError
from bitledger.profiles import load_profile


def config_dir() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg).expanduser() / "bitledger"
    return Path.home() / ".config" / "bitledger"


def active_profile_file() -> Path:
    return config_dir() / "active.json"


def read_active_profile_path() -> Path | None:
    p = active_profile_file()
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        path = Path(data["path"]).expanduser()
        if path.is_file():
            return path.resolve()
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return None


def write_active_profile(path: Path) -> None:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise ProfileError(f"profile not found: {resolved}")
    out = active_profile_file()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"path": str(resolved)}), encoding="utf-8")


def effective_profile_path(ns: object) -> Path | None:
    """
    Order: explicit --profile, env BITLEDGER_PROFILE, then active pointer file.
    Returns None if no profile is configured.
    """
    if getattr(ns, "profile", None):
        return Path(ns.profile).expanduser()
    env = os.environ.get("BITLEDGER_PROFILE")
    if env:
        return Path(env).expanduser()
    return read_active_profile_path()


def profiles_search_dir(ns: object | None = None) -> Path:
    if ns is not None and getattr(ns, "profile_dir", None):
        return Path(ns.profile_dir).expanduser().resolve()
    env = os.environ.get("BITLEDGER_PROFILE_DIR")
    if env:
        return Path(env).expanduser().resolve()
    return (Path.cwd() / "profiles").resolve()


def resolve_profile_target(target: str, ns: argparse.Namespace) -> Path:
    """Name in profile dir, or path to a .json file."""
    raw = Path(target).expanduser()
    if raw.is_file():
        return raw.resolve()
    base = profiles_search_dir(ns)
    for name in (target, f"{target}.json"):
        cand = base / name
        if cand.is_file():
            return cand.resolve()
    raise ProfileError(f"profile not found: {target!r} under {base}")


def cmd_profile_list(ns: argparse.Namespace) -> int:
    d = profiles_search_dir(ns)
    if not d.is_dir():
        print(f"No profile directory: {d}", file=sys.stderr)
        print("Create it or set BITLEDGER_PROFILE_DIR.", file=sys.stderr)
        return 0
    rows: list[tuple[str, str]] = []
    for path in sorted(d.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            label = str(data.get("name", path.stem))
        except (OSError, ValueError):
            label = path.stem
        rows.append((label, str(path.resolve())))
    if not rows:
        print(f"(no *.json in {d})")
        return 0
    w = max(len(a) for a, _ in rows)
    print(f"{'NAME':<{w}}  PATH")
    for label, pth in rows:
        print(f"{label:<{w}}  {pth}")
    return 0


def cmd_profile_use(ns: argparse.Namespace) -> int:
    try:
        path = resolve_profile_target(ns.target, ns)
        write_active_profile(path)
    except ProfileError as e:
        print(str(e), file=sys.stderr)
        return 2
    print(f"Active profile set to:\n  {path}")
    print(f"(Stored in {active_profile_file()})")
    return 0


def cmd_profile_show(ns: argparse.Namespace) -> int:
    p = read_active_profile_path()
    if p is None:
        print("No active profile (run `bitledger profile use <name>`).", file=sys.stderr)
        print("Or set BITLEDGER_PROFILE or pass --profile on encode/make.", file=sys.stderr)
        return 1
    try:
        l1, l2 = load_profile(p)
    except ProfileError as e:
        print(str(e), file=sys.stderr)
        return 2
    print(f"Active profile file: {p}")
    print(f"  sender_id=0x{l1.sender_id:08X}  sub_entity={l1.sub_entity_id}")
    print(
        f"  SF_index={l2.scaling_factor_index}  dp={l2.decimal_position}  "
        f"split={l2.optimal_split}  currency={l2.currency_code}  tx={l2.transmission_type}"
    )
    print(f"  compound_mode_active={l1.compound_mode_active}  compound_prefix={l2.compound_prefix}")
    return 0


def add_profile_cli(sub: Any) -> None:
    pp = sub.add_parser(
        "profile",
        help="List profiles, set active profile pointer, or show active summary",
    )
    psub = pp.add_subparsers(dest="profile_action", required=True)

    pl = psub.add_parser("list", help="List *.json profiles in the profile directory")
    pl.add_argument(
        "--dir",
        dest="profile_dir",
        help="Override profile directory (default: ./profiles or BITLEDGER_PROFILE_DIR)",
    )
    pl.set_defaults(func=cmd_profile_list)

    pu = psub.add_parser(
        "use",
        help="Set active profile (pointer under XDG config …/bitledger/active.json)",
    )
    pu.add_argument(
        "target",
        help="Filename in profile dir (e.g. corp) or path to a .json file",
    )
    pu.add_argument(
        "--dir",
        dest="profile_dir",
        help="Directory to resolve a short name (default: ./profiles or BITLEDGER_PROFILE_DIR)",
    )
    pu.set_defaults(func=cmd_profile_use)

    ps = psub.add_parser("show", help="Print active profile path and Layer1/2 summary")
    ps.set_defaults(func=cmd_profile_show)
