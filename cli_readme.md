# BitLedger CLI

Reference for the `bitledger` command-line tool (Python 3.10+, stdlib only). Install from the `bitledger` project directory:

```bash
pip install -e ".[dev]"
bitledger --help
```

On **Homebrew / PEP 668** Python, plain `pip install` into the system interpreter is blocked. Use **`pipx`** so `bitledger` is on your PATH (typically `~/.local/bin`, which most shells already include):

```bash
cd /path/to/bitledger   # this repo’s pyproject.toml
pipx install .
# after you pull code changes:
pipx install --force .
```

The console script entry point is `bitledger` → `bitledger.bitledger:main`. For development without install, run via Python (no `__main__` package hook):

```bash
cd bitledger
PYTHONPATH=. python -c "import sys; from bitledger.cli import main; sys.exit(main(sys.argv[1:]))" setup --help
```

See also the project [README.md](README.md) for protocol background.

---

## Subcommands

| Command | Purpose |
|--------|---------|
| `setup` | Interactive Layer 1 / Layer 2 profile wizard; optional JSON output |
| `make` | **Primary:** plan a BitLedger record — **SF search** in range (or fixed `--sf`; exact-first unless **`--legacy-sf-search`**), **N / A / r**, **bits 26–27**, **delta** if rounded, copy-paste **`encode`** line |
| `check-amount` | **Verify** the same resolution as `make` (STATUS exact vs rounding, key numbers); **no** suggested `encode` block — use when you want a clean check before `make` / `encode` |
| `suggest-sf` | Alias of **`make`** (identical flags and output) |
| `encode` | Build a binary record (Layer 1 + Layer 2 + 40-bit Layer 3) |
| `decode` | Parse a `.bl` file or inline hex back to headers + journal |
| `simulate` | Encode/decode smoke loop on a canned record |
| `profile` | **`list`**, **`use`**, **`show`** — discover JSON profiles, set active pointer, print active summary |

---

## `profile` (`list` \| `use` \| `show`)

Profiles are JSON files (from **`setup --out`**). **Active profile** is a small pointer file:

- **`$XDG_CONFIG_HOME/bitledger/active.json`** if `XDG_CONFIG_HOME` is set  
- else **`~/.config/bitledger/active.json`**

| Subcommand | Purpose |
|------------|---------|
| **`profile list`** | List **`*.json`** in the profile directory (default **`./profiles`**, or **`BITLEDGER_PROFILE_DIR`**, or **`--dir`**) |
| **`profile use TARGET`** | Resolve **`TARGET`** (short name like `corp` / `corp.json`, or a full path) and write the active pointer |
| **`profile show`** | Print active file path and a one-line Layer 1/2 summary |

**Profile resolution** for **`encode`**, **`make`**, **`check-amount`**, **`simulate`** (when they load defaults):

1. **`--profile PATH`** if passed  
2. else **`BITLEDGER_PROFILE`** env (path to `.json`)  
3. else **active pointer** from **`profile use`**

```bash
bitledger profile list
bitledger profile list --dir ./profiles
bitledger profile use corp
bitledger profile use /absolute/path/to/corp.json
bitledger profile show
```

---

## `make` / `check-amount` / `suggest-sf`

Shared resolution: **`--profile`**, then **`BITLEDGER_PROFILE`**, then **active pointer**; then Layer 1/2 overrides (`--dp`, `--optimal-split`, `--currency`, `--sf`, …). **`--amount`** accepts commas/underscores.

- **Without `--sf`:** searches **`--min-sf` … `--max-sf`** (defaults **0 … 127**) for the **smallest** SF with an **exact** encoding (`rounding_flag = 0`) when possible; otherwise the smallest SF where `encode_value` succeeds. Pass **`--legacy-sf-search`** to restore the older rule (first ascending SF with any success).
- **With `--sf`:** validates that index only (or exits **2**).
- **`--rounding-report`:** after the normal report, append a **typed − wire** block (scale **`k`**, **`dp`**, **`rf`/`rd`**, \(\Delta\) sum/mean for the planned amount).
- **`--quantity-present` `0`|`1`:** matches **`encode`**; when **`1`**, suggested **`encode`** includes **`--quantity-present 1`**, JSON includes **`quantity_present`**, and decode lines in **`make`** / reports use **\(N = A \times r\)** semantics for the wire value.

**`make`** — full **plan → record** output plus **Suggested encode** one-liner. **`make --json`** (and **`suggest-sf --json`**) prints the plan as **JSON**; with **`--rounding-report`**, adds **`rounding_observation`** (typed / wire / \(\Delta\) / scale fields).

**`check-amount`** — same math, **verification-first**: **STATUS** (EXACT vs ROUNDING), compact number block, reminder to run **`make`** for the encode line. No `bitledger encode …` dump.

**`suggest-sf`** — alias of **`make`**.

```bash
bitledger check-amount --amount "24,456,346,932.00" --dp 2 --account-pair 4
bitledger make --amount "24,456,346,932.00" --dp 2 --account-pair 4
bitledger make --profile profiles/corp.json --amount 80400000000
bitledger suggest-sf --amount 2500000000 --dp 2 --account-pair 4
bitledger make --amount 100 --sf 3 --dp 2   # fixed SF only
```

---

## `setup`

Writes a profile JSON when `--out` is set.

| Flag | Description |
|------|-------------|
| `--out PATH` | Write profile JSON to `PATH` |
| `--name NAME` | Profile name stored in JSON (default: `default`) |
| `--force` | Allow overwriting when `name` is `default` and the file already exists |
| `--quiet` | Suppress human-readable header echo |

---

## `encode`

Emits **14 bytes** by default when Layer 2 uses short form (`0x6F`): 8 (L1) + 1 (short L2) + 5 (L3), or **19 bytes** with full Layer 2: 8 + 6 + 5.

### Output

| Flag | Description |
|------|-------------|
| `--out PATH` | Write raw bytes to `PATH` (convention: `.bl`) |
| `--quiet` | Skip printed headers and journal |
| `--emit-l2 auto\|short\|full` | Layer 2: `0x6F` short form, full 6-byte header, or `auto` from defaults |

### Profile / session

| Flag | Description |
|------|-------------|
| `--profile PATH` | Load Layer 1/2 defaults (wins over **`BITLEDGER_PROFILE`** and **`profile use`**) |

### Layer 1 overrides (optional)

`--sender`, `--subentity`, `--compound-session`, `--perms` — see inline `--help` for formats.

### Layer 2 overrides (BitPads-aligned)

| Flag | Wire field |
|------|------------|
| `--sf` | Scaling factor index (0–127; table uses **×10^index** for every wire index **0–127**) |
| `--currency` | 6-bit currency index |
| `--txtype` | Transmission type **1**, **2**, or **3** only (`00` is invalid and rejected) |
| `--compound-prefix` | Compound prefix (2 bits) |
| `--sep-group` | **Group separator — 4 bits** (BitLedger v3 Layer 2; if older docs mention 6 bits for a command table, the wire format here is **4**) |
| `--sep-record` | Record separator (5 bits) |
| `--sep-file` | File separator (3 bits) |
| `--optimal-split` | Optimal split `S` for value decomposition (0–15) |
| `--dp` | Decimal position wire code (0–6; `111` reserved / not implemented) |

### Value and Layer 3

**Either** raw multiplicand / remainder **or** a decimal amount:

| Flag | Description |
|------|-------------|
| `--amount DECIMAL` | `Decimal` string (**commas / underscores** allowed); derives `N`, `A`, `r`, rounding flags from `--sf`, `--dp`, `--optimal-split` (profile or defaults), and `--account-pair` rounding mode |
| `--auto-sf` | With **`--amount`**: search **`--min-sf`..`--max-sf`** (defaults **0..127**) using the same policy as **`make`** (smallest exact SF when possible); **mutually exclusive** with **`--sf`** |
| `--min-sf`, `--max-sf` | Bounds for **`--auto-sf`** search only |
| `--legacy-sf-search` | With **`--auto-sf`**: first ascending SF with any valid encoding (old behaviour) |
| `--accept-rounding` | With **`--amount`**: required when encode would set **rounding_flag** (non-exact wire value); otherwise encode exits **2** with a short explanation |
| `--rounding-report` | With **`--amount`**: print scale (**SF index `k`**, **`dp`**) and **typed − wire** table plus \(\Delta\) sum/mean (stdout; works with **`--quiet`**) |
| `--A`, `--r` | Raw value limbs when `--amount` is omitted |
| `--rounding-flag`, `--rounding-dir`, `--split-order` | Layer 3 flags |
| `--direction`, `--status`, `--debit-credit` | Posting semantics |
| `--quantity-present` | `1` = quantity mode (`N = A×r` at decode) |
| `--account-pair` | 4-bit pair code (`1111` = continuation; requires session compound + batch compound prefix) |
| `--completeness`, `--extension-flag`, `--continuation-subtype` | As per protocol |

| Flag | Description |
|------|-------------|
| `--description TEXT` | Shown on the **Description** line of the journal block |

### Examples

```bash
# Amount-driven encode (USD index 1), write binary
bitledger encode --amount 1247.50 --currency 1 --debit-credit 1 --out txn.bl

# Raw A/r (same as early demos)
bitledger encode --A 1 --r 197 --out raw.bl

# Full Layer 2 header
bitledger encode --emit-l2 full --amount 100 --sf 2 --dp 2 --out scaled.bl

# Large nominal: pick SF automatically, then write .bl
bitledger encode --quiet --amount 2500000000 --auto-sf --dp 2 --account-pair 4 --out big.bl
```

---

## `decode`

| Argument / flag | Description |
|-----------------|-------------|
| `RECORD_HEX` | Optional continuous hex (spaces allowed) if `--in` is not used |
| `--in PATH` | Read binary `.bl` from file |
| `--quiet` | Suppress headers, journal, and record summary |
| `--rounding-report` | Append scale (**`k`**, **`dp`**) and wire amount; optional \(\Delta\) vs **`--compare-amount`** (stderr hints if **`--compare-amount`** omitted) |
| `--compare-amount DECIMAL` | With **`--rounding-report`**: typed amount for **typed − wire** (\(\Delta\)) and aggregate lines |

After unpack, **Rule 6** is enforced: account pair `1111` is rejected unless Layer 1 `compound_mode_active` is on and Layer 2 `compound_prefix != 00`.

### Examples

```bash
bitledger decode 04D0051814
bitledger decode --in txn.bl
```

---

## Quantity mode (`--quantity-present`)

When `--quantity-present 1` is passed, the value field encodes a quantity product:

    N = A × r      (standard mode: N = (A << S) | r)

This is useful when A is a unit count and r is a unit price, or any multiplicative decomposition where both factors have independent meaning.

### Examples

**Plan a quantity record:**
```
bitledger make --amount 59.76 --quantity-present 1
```

**Encode a quantity record:**
```
bitledger encode --amount 59.76 --quantity-present 1 --auto-sf --out qty.bl
```

**Decode it back:**
```
bitledger decode --in qty.bl
```

**Machine-readable plan:**
```
bitledger make --amount 59.76 --quantity-present 1 --json
```
Output JSON will include `"quantity_present": true` and `"suggested_encode_argv"` with `--quantity-present 1`.

**Verify without encode block:**
```
bitledger check-amount --amount 59.76 --quantity-present 1
```

### Notes

- `quantity_present` is stored in bit 8 of the Layer 3 record.
- The `optimal_split` (S) from Layer 2 is irrelevant to the value field in quantity mode, but still present in the header.
- Rounding semantics are identical: if the amount cannot be encoded exactly, `--accept-rounding` is required.
- Protocol reference: README.md §Layer 3 value field, §quantity_present flag.

---

## Extended help (`bitledger help`)

```
bitledger help              # Command listing with one-line descriptions
bitledger help --extra      # Full guide: protocol, norms, workflows, config locations
```

Per-command flags are always available via:
```
bitledger <command> --help
```

---

## `simulate`

| Flag | Description |
|------|-------------|
| `--profile PATH` | Optional profile for Layer 2 split / session |
| `--quiet` | Minimal output |

---

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Usage / invalid user input (e.g. bad hex) |
| `2` | Protocol or profile error (`EncoderError`, `DecoderError`, `ProfileError`) |

---

## Human-readable output

When not `--quiet`, `encode` and `decode` print:

1. Layer 1 and Layer 2 header blocks  
2. A **README-aligned journal** (`BITLEDGER JOURNAL ENTRY`, session/batch lines, DEBIT/CREDIT narrative, description/status/precision, optional **Binary** / **Hex** from the 40-bit word)  
3. A compact `BITLEDGER RECORD` summary (including pipe-grouped binary per TASK-2.09)

**`--rounding-report`** may still print after **`encode --quiet`** or **`decode --quiet`** (structured **typed − wire** footer).

---

## Error detection (decoder)

Implemented checks include:

- **Rule 1 / 2**: Direction and status mirrors (suspended for `account_pair == 1111` per CONFLICT-005)  
- **Rule 3**: Invalid rounding state (`bit26=0`, `bit27=1`)  
- **Rule 4**: Layer 1 CRC-15 over bits 1–49  
- **Rule 5**: `decoder.validate_batch_integrity(expected, received)` for batch-close workflows (call from your orchestration when you have counts)  
- **Rule 6**: `validate_compound_context` on decode (and in `simulate_record_roundtrip`)

---

## Tests

```bash
cd bitledger
python -m pytest tests/ --tb=short
```
