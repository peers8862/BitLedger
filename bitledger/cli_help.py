"""Extended help system for BitLedger CLI.

`bitledger help` — command listing with one-line descriptions
`bitledger help --extra` — full guide: protocol overview, command norms, workflows,
    error codes, config locations, and protocol references for new users.

Coverage tracking (update as commands get full --extra content):
    setup        ✓ full
    encode       ✓ full
    decode       ✓ full
    make         ✓ full
    check-amount ✓ full
    profile      ✓ full
    simulate     stub
    suggest-sf   stub (alias of make)
    help         ✓ full
"""

from __future__ import annotations

import argparse
import sys


_COMMAND_BRIEF = {
    "setup":        "Interactive wizard — configure Layer 1/2 session profile and save to JSON",
    "encode":       "Build a .bl binary record from amount or raw A/r fields",
    "decode":       "Parse a .bl file or hex string into a human-readable journal entry",
    "make":         "PRIMARY — plan a record: SF search, rounding check, copy-paste encode line",
    "suggest-sf":   "Alias of make (same output and flags)",
    "check-amount": "Verify amount→SF/N/rounding plan without the suggested encode block",
    "profile":      "Manage named session profiles (list, use, show)",
    "simulate":     "Encode/decode smoke test using a synthetic record",
    "help":         "Show this listing; --extra for full protocol guide",
}

_EXTRA_GUIDE = """
╔══════════════════════════════════════════════════════════════════╗
║          BitLedger  —  Extended CLI Guide                        ║
╚══════════════════════════════════════════════════════════════════╝

PROTOCOL OVERVIEW
─────────────────
BitLedger encodes a complete double-entry accounting transaction in
40 bits (5 bytes). Three layers wrap every record:

  Layer 1 (8 bytes)   — session identity, sender ID, CRC-15
  Layer 2 (6 bytes or 0x6F short-form)
                      — scaling factor (SF), decimal position (dp),
                        currency, transmission type, batch separators
  Layer 3 (5 bytes)   — 40-bit transaction record:
                        bits 39-15: value field (N split into A and r)
                        bits 14-8 : flags (rounding, direction, status, ...)
                        bits  7-0 : account pair, mirrors, completeness

One record = 14-19 bytes. 100 records ≈ 512 bytes.
Reference: README.md (protocol spec v3.0)


NORMAL WORKFLOW
───────────────
1. Setup once:
     bitledger setup --out my.json --name work

2. Activate profile:
     bitledger profile use work   (or: export BITLEDGER_PROFILE=my.json)

3. Plan a record:
     bitledger make --amount 149.99

   Output shows: recommended SF index, encoded A and r, rounding status,
   and a ready-to-paste `encode` command line.

4. Encode:
     bitledger encode --amount 149.99 --auto-sf --out tx.bl

5. Verify:
     bitledger decode --in tx.bl


COMMAND NORMS
─────────────
• All monetary input must be Decimal (e.g. "149.99", not 149.99).
  Float inputs are rejected: protocol precision requires exact decimal.

• Rounding gate: if an amount cannot be represented exactly at the
  chosen SF/dp, encode refuses unless you pass --accept-rounding.
  Always run `make` first to see the rounding delta.

• Exit codes:  0 = success
               1 = user/input error (bad flags, missing file)
               2 = protocol/encode/decode error

• --quiet suppresses all output except errors; useful for scripting.

• Profile resolution order (highest to lowest priority):
    1. --profile flag
    2. BITLEDGER_PROFILE environment variable
    3. Active pointer: ~/.config/bitledger/active.json
    4. Fail closed with a clear message

• Master config: ~/.config/bitledger/config.json
  Controls session-wide toggles (e.g. warn_short_form_mismatch).


COMMAND REFERENCE
─────────────────

  setup [--out PATH] [--name NAME] [--force]
    Interactive wizard. Asks for sender ID, currency, SF index, dp,
    transmission type, and other Layer 1/2 fields. Saves a profile JSON
    you can load in every subsequent command.
    --force: overwrite an existing "default" profile at --out.

  encode [--amount DECIMAL | --A INT --r INT] [options]
    Builds the full L1+L2+L3 binary blob.
    Key flags:
      --amount DECIMAL     Monetary input (preferred over raw A/r)
      --auto-sf            Search SF range for best fit
      --min-sf / --max-sf  Constrain SF search (default 0..127)
      --accept-rounding    Allow encoding when amount rounds
      --rounding-report    Print typed−wire delta table
      --out PATH           Write .bl file (else dry-run)
      --emit-l2 auto|short|full
                           Control Layer 2 wire form (default: auto)
      --description TEXT   Narrative line in journal output

  decode [HEX | --in PATH] [options]
    Reads a .bl file or continuous hex string. Prints Layer 1, Layer 2,
    journal entry, and record summary.
    Key flags:
      --rounding-report         Print scale and wire amount
      --compare-amount DECIMAL  Compute typed−wire delta (requires above)
      --profile PATH            Compare against profile when 0x6F short-form
                                is detected (warns on mismatch)

  make --amount DECIMAL [options]
    PRIMARY planning command. Outputs:
      • Recommended SF index (exact-first search by default)
      • Encoded N, A, r values
      • Rounding flag and delta (if any)
      • Copy-paste `encode` command line
    --json: machine-readable plan for scripting
    --quantity-present 1: quantity mode (N = A × r, not bit-split)
    --rounding-report: add delta table to output

  check-amount --amount DECIMAL [options]
    Same as make but omits the suggested encode block.
    Use for verification without encode noise.

  suggest-sf   Alias of make — identical flags and output.

  profile list [--dir DIR]
    List all profile JSONs in DIR (default: ./profiles or $BITLEDGER_PROFILE_DIR).
    Shows name, currency, SF index, decimal position.

  profile use NAME-OR-PATH
    Write active pointer to ~/.config/bitledger/active.json.
    Subsequent commands resolve profile from this pointer automatically.

  profile show [--profile PATH]
    Print the fields of the active or specified profile.

  simulate [--profile PATH]
    Encode a synthetic record (A=1, r=197, account_pair=4) and decode it.
    Used as a smoke test to confirm Layer 1/2/3 roundtrip is intact.

  help [--extra]
    This listing. --extra for the full guide (you are reading it).


QUANTITY MODE
─────────────
When --quantity-present 1 is set, the value field encodes a quantity:
  N = A × r       (not the bit-split (A<<S)|r used in standard mode)

Use this for records where A is a unit count and r is a unit price,
or any other multiplicative decomposition.

Standard mode (default):
  N = (A << S) | r      where S = optimal_split from Layer 2

The quantity_present flag is stored in bit 8 of Layer 3.
Reference: README.md §Layer 3 value field, §quantity_present flag


SHORT-FORM LAYER 2 (0x6F)
──────────────────────────
When Layer 2 settings match all defaults (SF=0, dp=0, split=0,
txtype=1, currency=0, compound_prefix=0), the encoder emits a single
0x6F byte instead of the full 6-byte header (--emit-l2 auto or short).

On decode: 0x6F expands to the same defaults. If your profile has
non-default settings and you receive a 0x6F record, the decoder will
warn (DecoderWarning) and suggest re-encoding with --emit-l2 full.

To suppress this warning:
  Set warn_short_form_mismatch=false in ~/.config/bitledger/config.json


ERROR STYLE
───────────
All errors print a compact single-line message to stderr:
  ERROR: <description>
  Protocol reference if applicable.

Warnings (non-fatal) print:
  WARN: <description>
  → <suggested fix>
  ref: <protocol element or doc>
  (suppress: set <key>=false in master config)


SCALING FACTOR (SF) REFERENCE
──────────────────────────────
SF index 0..127 maps to a multiplier in SCALING_FACTORS table.
  SF=0: ×1     SF=1: ×2     SF=2: ×5     SF=3: ×10  ...
  SF=17: ×10^17   SF=18..127: higher powers and composite factors

`make` always searches for the smallest SF that encodes your amount
exactly (exact-first). Use --legacy-sf-search for the old behaviour
(first ascending SF with any valid encoding).

Reference: project/analysis/value_encoding_scaling_factor_reference.md


CONFIG FILES
────────────
  Master config:  ~/.config/bitledger/config.json
  Active profile: ~/.config/bitledger/active.json
  Profile store:  anywhere; convention is ./profiles/ in your project

  Environment override: BITLEDGER_PROFILE=/path/to/profile.json


PROTOCOL DOCS
─────────────
  README.md                         — Protocol spec v3.0 (primary reference)
  cli_readme.md                     — Full CLI flag reference
  project/analysis/                 — Value encoding, notation, SF reference
  project/protocol docs/markdown/   — CONFLICT-005, compound mode resolution
  CLAUDE.md                         — Agent model and code quality gates
"""


def cmd_help(ns: argparse.Namespace) -> int:
    if getattr(ns, "extra", False):
        print(_EXTRA_GUIDE)
        return 0
    print("BitLedger — binary financial transmission protocol CLI\n")
    print("Commands:")
    for cmd, brief in _COMMAND_BRIEF.items():
        print(f"  {cmd:<14}  {brief}")
    print("\nRun `bitledger help --extra` for full protocol guide, workflows, and norms.")
    print("Run `bitledger <command> --help` for per-command flags.")
    return 0
