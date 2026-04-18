# BitLedger — Command Examples and Output Guide

All output below is real — captured from the live `v1.0.0` CLI. Every command
is runnable as-is from the project root (`python3 -m bitledger.cli <command>`
or `bitledger <command>` if installed).

---

## 1. Getting oriented

### Command listing

```
$ bitledger help
```
```
BitLedger — binary financial transmission protocol CLI

Commands:
  setup           Interactive wizard — configure Layer 1/2 session profile and save to JSON
  encode          Build a .bl binary record from amount or raw A/r fields
  decode          Parse a .bl file or hex string into a human-readable journal entry
  make            PRIMARY — plan a record: SF search, rounding check, copy-paste encode line
  suggest-sf      Alias of make (same output and flags)
  check-amount    Verify amount→SF/N/rounding plan without the suggested encode block
  profile         Manage named session profiles (list, use, show)
  simulate        Encode/decode smoke test using a synthetic record
  help            Show this listing; --extra for full protocol guide

Run `bitledger help --extra` for full protocol guide, workflows, and norms.
Run `bitledger <command> --help` for per-command flags.
```

### Extended guide (excerpt)

```
$ bitledger help --extra
```
```
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

NORMAL WORKFLOW
───────────────
1. Setup once:    bitledger setup --out my.json --name work
2. Activate:      bitledger profile use work
3. Plan:          bitledger make --amount 149.99
4. Encode:        bitledger encode --amount 149.99 --auto-sf --out tx.bl
5. Verify:        bitledger decode --in tx.bl

COMMAND NORMS
─────────────
• All monetary input must be Decimal (e.g. "149.99", not 149.99).
• Rounding gate: encode refuses if amount rounds — run `make` first.
• Exit codes:  0 = success   1 = user/input error   2 = protocol error
• --quiet suppresses all output except errors; useful for scripting.

... (continues with full COMMAND REFERENCE, QUANTITY MODE, CONFIG FILES, etc.)
```

### Per-command flags

```
$ bitledger encode --help
```
```
usage: bitledger encode [-h] [--quiet] [--profile PROFILE] [--out OUT]
                        [--emit-l2 {auto,short,full}] [--sender SENDER]
                        [--sf SF] [--auto-sf] [--min-sf MIN_SF]
                        [--max-sf MAX_SF] [--legacy-sf-search]
                        [--accept-rounding] [--rounding-report]
                        [--currency CURRENCY] [--txtype {1,2,3}]
                        [--optimal-split OPTIMAL_SPLIT] [--dp DP]
                        [--amount DECIMAL] [--description DESCRIPTION]
                        [--A A] [--r R] ...

options:
  --amount DECIMAL      Monetary amount (Decimal); derives N,A,r from profile
                        SF, --dp, optimal split, and --account-pair rounding mode
  --auto-sf             With --amount: search --min-sf..--max-sf for SF
                        (default: smallest exact encoding, else smallest that fits)
  --min-sf / --max-sf   Constrain SF search range (default 0..127)
  --accept-rounding     With --amount: allow encode when rounding_flag would be set
  --rounding-report     With --amount: print typed−wire delta table
  --out OUT             Write .bl file (else dry-run)
  --emit-l2 {auto,short,full}
                        Control Layer 2 wire form (default: auto)
  --description TEXT    Narrative line in journal output
  ...
```

---

## 2. Planning a record — `make`

`make` is the primary command. It shows you exactly what will be encoded before
you commit a byte to disk.

### Basic: plan a $149.99 transaction

```
$ bitledger make --amount 149.99
```
```
(SF search 0..127: index 0; prefer smallest exact encoding, else smallest that fits)

── BitLedger make (plan → record) ──
Amount (parsed):     149.99
Wire scaling:        SF index = 0  (×1 = 10^0)
Decimal position:    dp = 2  (divide by 10^2 on decode)
Optimal split S:     8
Account pair:        0b100  rounding_mode = 'down'
R = amount×10^dp/SF: 14999.00
Stored integer N:    14999  (max wire 33,554,431)
Decomposed:          A = 58   r = 151   (N = (A<<S)|r = 14999)
Bits 26–27:          00  exact (no rounding)
Decoded wire value:  matches typed amount (exact).
── Suggested encode ──
bitledger encode --emit-l2 auto --amount 149.99 --sf 0 --dp 2 --optimal-split 8 \
  --account-pair 4 --direction 0 --status 0 --debit-credit 0 --split-order 0
```

What the output tells you:
- **SF index 0 (×1)** — the scaling factor chosen; determines how N maps to a real value
- **dp = 2** — wire divides by 10² on decode, so integers represent cents
- **N = 14999** — the 25-bit integer stored on wire; well under the 33.5M maximum
- **A = 58, r = 151** — the bit-split of N at split S=8: `(58 << 8) | 151 = 14999` ✓
- **Bits 26–27: 00** — exact encoding; no rounding occurred
- **Suggested encode** — copy-paste ready command line

### Machine-readable plan — `make --json`

For scripting or automation:

```
$ bitledger make --amount 149.99 --json
```
```json
{
  "amount": "149.99",
  "sf_index": 0,
  "scaling_factor": "1",
  "dp": 2,
  "optimal_split": 8,
  "account_pair": 4,
  "rounding_mode": "down",
  "R": "14999.00",
  "N": 14999,
  "A": 58,
  "r": 151,
  "rounding_flag": false,
  "rounding_dir": 0,
  "bits_26_27": "00  exact (no rounding)",
  "decoded_wire_value": "149.99",
  "delta_typed_minus_decoded": "0.00",
  "quantity_present": false,
  "suggested_encode_argv": [
    "encode", "--emit-l2", "auto", "--amount", "149.99",
    "--sf", "0", "--dp", "2", "--optimal-split", "8",
    "--account-pair", "4", "--direction", "0",
    "--status", "0", "--debit-credit", "0", "--split-order", "0"
  ]
}
```

`suggested_encode_argv` is a ready-to-use argument list for programmatic invocation.

### Verify without the encode block — `check-amount`

When you just want to confirm the numbers without the suggested encode line:

```
$ bitledger check-amount --amount 149.99
```
```
── BitLedger check-amount (verification) ──
Use this to confirm amount → N, rounding, and SF/dp/S before you `make` or `encode`.

STATUS:  EXACT — no rounding; bits 26–27 = 00.

(SF search 0..127: index 0; prefer smallest exact encoding, else smallest that fits)

Amount (parsed):      149.99
SF index / scale:     0  (×1)
dp / S / pair:        dp=2   S=8   pair=0b100  mode='down'
R = amount×10^dp/SF:  14999.00
Integer N (≤33.55M):  14999
A / r:                A=58   r=151   composite N=14999
Bits 26–27:           00  exact (no rounding)

Next: `bitledger make` with the same flags for the full plan + suggested `encode` line.
```

---

## 3. Encoding — writing a `.bl` file

### Standard encode: amount → binary

```
$ bitledger encode --amount 149.99 --auto-sf --out tx.bl
```
```
────────────────────────────────────────
LAYER 1 — Session
  protocol_version=1
  permissions R/W/C/R = True/True/False/False
  split_order_default=0  opposing_explicit=False
  compound_mode_active=False  bitledger_optional=False
  sender_id=0x00000000  sub_entity_id=0
────────────────────────────────────────
────────────────────────────────────────
LAYER 2 — Batch
  transmission_type=1  SF_index=0
  optimal_split=8  decimal_position_wire=2
  currency_index=0 (Session default)  compound_prefix=0
  group_sep=0  record_sep=0  file_sep=0
────────────────────────────────────────
─────────────────────────────────────────────────────────────────
BITLEDGER JOURNAL ENTRY
Session : sender 0x00000000  /  sub-entity 00
Batch   : Group 00  /  Record 000  /  Currency: index 0
─────────────────────────────────────────────────────────────────
DEBIT    Asset                      index 0       149.99
CREDIT   Op Income                  index 0       149.99
─────────────────────────────────────────────────────────────────
Description : (no description)
Status      : Settled — past
Precision   : Exact
─────────────────────────────────────────────────────────────────
Binary  : 00000000000111010 10010111 0000000 0100 0 0 0 0
Hex     : 00 1D 4B 80 40
─────────────────────────────────────────────────────────────────
BITLEDGER RECORD
  account_pair=0b100  dir=0  status=0
  completeness=0  qty_present=False
  A=58  r=151
Binary : 00000000000111010 | 10010111 | 0000000 | 0100 | 0 | 0 | 0 | 0
Hex    : 00 1D 4B 80 40  (0x001D4B8040)
Wrote 14 bytes to tx.bl
```

14 bytes on disk: 8 (L1) + 1 (0x6F short-form L2) + 5 (L3 record).

### With a description

```
$ bitledger encode --amount 149.99 --auto-sf --description "Office supplies Q1" --out tx.bl
```
```
...
─────────────────────────────────────────────────────────────────
BITLEDGER JOURNAL ENTRY
...
─────────────────────────────────────────────────────────────────
DEBIT    Asset                      index 0       149.99
CREDIT   Op Income                  index 0       149.99
─────────────────────────────────────────────────────────────────
Description : Office supplies Q1
Status      : Settled — past
Precision   : Exact
```

### Dry run (no `--out`)

Omit `--out` to preview the blob without writing a file:
```
Emit 14 bytes (pass --out file.bl)
```

---

## 4. Decoding

### From a `.bl` file

```
$ bitledger decode --in tx.bl
```

Produces the same Layer 1 / Layer 2 / Journal / Record output as encode (shown above).

### From a hex string on the command line

The full record as continuous hex — useful for piping or debugging:

```
$ bitledger decode 9c000000000020956f001d4b8040
```
```
────────────────────────────────────────
LAYER 1 — Session
  protocol_version=1
  permissions R/W/C/R = True/True/False/False
  ...
────────────────────────────────────────
LAYER 2 — Batch
  transmission_type=1  SF_index=0  optimal_split=8  decimal_position_wire=2
  ...
─────────────────────────────────────────────────────────────────
BITLEDGER JOURNAL ENTRY
...
DEBIT    Asset          index 0       149.99
CREDIT   Op Income      index 0       149.99
─────────────────────────────────────────────────────────────────
Description : (no description)
Status      : Settled — past
Precision   : Exact
─────────────────────────────────────────────────────────────────
Hex     : 00 1D 4B 80 40
```

### With rounding report and comparison

Compare what was typed vs. what's actually on the wire:

```
$ bitledger decode --in tx.bl --rounding-report --compare-amount 149.99
```
```
... (full journal output) ...

── Rounding report (typed − wire) ──
  Scale: SF_index = k (×10^k); dp = decimal_position wire; qty=quantity_present
  #1  k=0  dp=2  pair=0b100  qty=0  rf=0 rd=0
       typed=149.99  wire=149.99  Δ=0.00
  Count: 1 total  (1 exact, 0 non-exact on wire)
  Δ sum (typed−wire): 0.00   mean: 0.00   (Δ>0: 0,  Δ<0: 0,  Δ=0: 1)
```

Zero delta — this record is bit-perfect.

---

## 5. Rounding visibility

### Seeing a rounding delta in `make`

When an amount has more precision than the wire can carry at the current SF/dp:

```
$ bitledger make --amount 1234.5678 --rounding-report
```
```
(SF search 0..127: index 0; ...)

── BitLedger make (plan → record) ──
Amount (parsed):     1234.5678
Wire scaling:        SF index = 0  (×1 = 10^0)
Decimal position:    dp = 2  (divide by 10^2 on decode)
...
R = amount×10^dp/SF: 123456.7800
Stored integer N:    123456  (max wire 33,554,431)
Decomposed:          A = 482   r = 64   (N = (A<<S)|r = 123456)
Bits 26–27:          10  rounded down (true amount ≥ decoded wire value)
Decoded wire value:  1234.56
Delta (typed − decoded): 0.0078
── Suggested encode ──
bitledger encode ... --accept-rounding
── Rounding report (typed − wire) ──
  #1  k=0  dp=2  pair=0b100  qty=0  rf=1 rd=0
       typed=1234.5678  wire=1234.56  Δ=0.0078
  Count: 1 total  (0 exact, 1 non-exact on wire)
  Δ sum (typed−wire): 0.0078   mean: 0.0078   (Δ>0: 1,  Δ<0: 0,  Δ=0: 0)
```

Key signals:
- **Bits 26–27: 10** — the record is flagged as "rounded down" on wire
- **Delta: 0.0078** — the discarded sub-cent precision
- **Suggested encode includes `--accept-rounding`** — you must opt in explicitly

### The rounding gate

If you try to encode a rounding amount without acknowledging it:

```
$ bitledger encode --amount 149.991   # exit 2
```
```
Encode would round this amount (bits 26–27). Run `bitledger check-amount` /
`bitledger make` with the same flags, then pass --accept-rounding to encode,
or change SF/dp/account-pair.
```

Pass `--accept-rounding` once you've reviewed the plan:

```
$ bitledger encode --amount 149.991 --accept-rounding
```
```
...
─────────────────────────────────────────────────────────────────
DEBIT    Asset          index 0       149.99      ← wire value
...
Precision   : Rounded                             ← rounding bit is set
─────────────────────────────────────────────────────────────────
Binary  : 00000000000111010 10010111 1000000 0100 0 0 0 0
                                     ↑ bit 26 = 1 (rounded)
```

The `Precision: Rounded` field in the journal entry is the human-readable
indicator; the raw bit is visible in the binary line at position 26–27.

---

## 6. Quantity mode

Standard mode packs N as a bit-split: `N = (A << S) | r`.
Quantity mode uses multiplication: `N = A × r`.

Use this when A is a unit count and r is a unit price (or any product).

```
$ bitledger make --amount 59.76 --quantity-present 1
```
```
(SF search 0..127: index 0; ...)

── BitLedger make (plan → record) ──
Amount (parsed):     59.76
Wire scaling:        SF index = 0  (×1 = 10^0)
Decimal position:    dp = 2  (divide by 10^2 on decode)
Optimal split S:     8
Quantity mode:       decode uses N = A × r for wire value (see rounding report).
Account pair:        0b100  rounding_mode = 'down'
R = amount×10^dp/SF: 5976.00
Stored integer N:    5976  (max wire 33,554,431)
Decomposed:          A = 23   r = 88   (N = (A<<S)|r = 5976)
Bits 26–27:          00  exact (no rounding)
Decoded wire value:  matches typed amount (exact).
── Suggested encode ──
bitledger encode ... --quantity-present 1
```

The `Quantity mode:` line is a reminder that decode will use `A × r`, and the
`quantity_present=1` flag is automatically included in the suggested encode.

---

## 7. Smoke test

Quick sanity check that encode→decode roundtrip is intact:

```
$ bitledger simulate
```
```
Roundtrip OK: 1 197 4
```

`1 197 4` = `multiplicand=1, multiplier=197, account_pair=4` — confirmed that
the synthetic test record survives encode and decode unchanged.

With `--quiet`, the output is suppressed and only the exit code signals success.

---

## 8. Error handling

### User error (exit 1) — bad input

```
$ bitledger decode ZZZZZZZZ
Invalid hex: non-hexadecimal number found in fromhex() arg at position 0
```

```
$ bitledger encode --amount 1.23 --auto-sf --min-sf 90 --max-sf 10
--max-sf must be >= --min-sf
```

### Protocol error (exit 2) — corrupt or invalid record

```
$ bitledger decode DEADBEEFDEADBEEF001D4B8040
Layer 1 CRC-15 verification failed
```

The CRC-15 embedded in Layer 1 does not match its payload — the record is
rejected before any data is extracted.

### Decoder warning (non-fatal) — short-form mismatch

When a record uses the 0x6F short-form Layer 2 byte but a loaded profile has
different session settings, the decoder warns and suggests a fix:

```
$ bitledger decode --in tx.bl --profile custom_session.json
```
```
... (journal output) ...

WARN: Short-form 0x6F decoded but loaded profile differs in: scaling_factor_index, currency_code
  → Re-encode the sender record with --emit-l2 full, or verify sender session
    matches 0x6F defaults (SF=0, dp=0, split=0, txtype=1, currency=0).
  ref: Layer 2 short-form 0x6F — cli_readme.md §Layer 2 short-form
  (suppress: set warn_short_form_mismatch=false in master config)
```

This is a `DecoderWarning` — the decode succeeds, but the semantic interpretation
may be wrong. The message names the differing fields, gives a concrete fix, and
tells you how to suppress it if it's intentional.

---

## 9. Exit codes at a glance

| Code | Meaning | Example |
|------|---------|---------|
| `0` | Success | Normal encode/decode/make |
| `1` | User/input error | Bad hex, missing file, bad flag combination |
| `2` | Protocol/internal error | CRC failure, rule violation, overflow |

```bash
bitledger encode --amount 149.99 --auto-sf --out tx.bl
echo $?   # → 0

bitledger decode ZZZZZZZZ
echo $?   # → 1

bitledger decode DEADBEEFDEADBEEF001D4B8040
echo $?   # → 2
```

---

## 10. Scripting patterns

### Test if a record encodes without rounding

```bash
bitledger make --amount "$AMOUNT" --json | python3 -c "
import json, sys
plan = json.load(sys.stdin)
if plan['rounding_flag']:
    print(f'WARNING: delta={plan[\"delta_typed_minus_decoded\"]}')
    sys.exit(1)
print('Exact encoding confirmed')
"
```

### Encode and capture hex

```bash
bitledger encode --amount 149.99 --auto-sf --out /tmp/rec.bl
xxd /tmp/rec.bl
# 00000000: 9c00 0000 0000 2095 6f00 1d4b 8040        ......  o..K.@
```

### Suppress all output, check exit only

```bash
bitledger encode --amount 149.99 --auto-sf --out tx.bl --quiet
if [ $? -eq 0 ]; then echo "OK"; fi
```

### Plan batch — pipe JSON amounts

```bash
for amount in 10.00 24.99 149.99 1000.00; do
    bitledger make --amount "$amount" --json \
        | python3 -c "import json,sys; p=json.load(sys.stdin); print(p['amount'], p['N'], p['bits_26_27'])"
done
# 10.00 1000 00  exact (no rounding)
# 24.99 2499 00  exact (no rounding)
# 149.99 14999 00  exact (no rounding)
# 1000.00 100000 00  exact (no rounding)
```

---

## Wire size reference

| Content | Size |
|---------|------|
| Layer 1 (full) | 8 bytes |
| Layer 2 full header | 6 bytes |
| Layer 2 short-form (`0x6F`) | 1 byte |
| Layer 3 record | 5 bytes |
| **Total (short-form L2)** | **14 bytes** |
| **Total (full L2)** | **19 bytes** |
| 100 records (short-form) | ~1,400 bytes |
| Equivalent CSV/JSON (est.) | ~10,000–200,000 bytes |

---

## See also

- `README.md` — Protocol specification v3.0
- `cli_readme.md` — Full flag reference for every command
- `DEVGUIDE.md` — Developer workflow, version bumps, how to direct Claude Code
- `bitledger help --extra` — Full in-terminal guide with protocol norms
