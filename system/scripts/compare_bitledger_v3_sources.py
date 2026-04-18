#!/usr/bin/env python3
"""Compare BitLedger Protocol v3 markdown mirrors (formatting vs content).

Exits 0 if lowercase alphanumeric streams match (same words/digits in same order).
Typical paths (from Bitpads repo root):

  bitpads/protocol docs/markdown/BitLedger_Protocol_v3.md
  bitledger/project/protocol docs/markdown/BitLedger_Protocol_v3.docx.md
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def alnum_stream(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("path_a", type=Path, help="First markdown file (e.g. bitpads copy)")
    p.add_argument("path_b", type=Path, help="Second markdown file (e.g. bitledger copy)")
    args = p.parse_args()
    a = args.path_a.read_text(encoding="utf-8", errors="replace")
    b = args.path_b.read_text(encoding="utf-8", errors="replace")
    sa, sb = alnum_stream(a), alnum_stream(b)
    if sa == sb:
        print(f"OK: alnum streams identical ({len(sa)} chars). No semantic divergence detected.")
        return 0
    print(f"FAIL: streams differ (len {len(sa)} vs {len(sb)}).", file=sys.stderr)
    shorter = min(len(sa), len(sb))
    for i in range(shorter):
        if sa[i] != sb[i]:
            ctx = 48
            print(f"First mismatch at alnum index {i}", file=sys.stderr)
            print("A:", repr(sa[max(0, i - ctx) : i + ctx]), file=sys.stderr)
            print("B:", repr(sb[max(0, i - ctx) : i + ctx]), file=sys.stderr)
            return 1
    print("FAIL: one stream is a prefix of the other.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
