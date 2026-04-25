# Plan — Hash Log, Templates, and Recall (v1.1.0)

**Status:** Implementing — all decisions resolved.
**Version target:** 1.1.0 (MINOR — no wire format change)
**Date:** 2026-04-18

---

## What this adds

Three coordinated features built on a shared hash log:

1. **Hash log** — every encode and decode optionally writes a JSONL entry with
   `wire_id` (exact blob identity) and `semantic_id` (transaction identity). Catches
   duplicates at two levels: same wire bytes (replay) and same transaction content
   (accidental re-encode).

2. **Templates** — saved parameter sets for recurring transactions. Each use
   produces a genuinely new wire record by incrementing `record_sep` (and `group_sep`
   on overflow), changing the L2 bytes and therefore the wire_id. Description
   supports static strings plus `{YYYY}`, `{MM}`, `{DD}` interpolation.

3. **Recall** — search and filter the hash log for past records by amount, account
   pair, date, template, or partial hash. Re-encode any result with a new wire_id
   via retransmit (increments a per-record retransmit counter for the same record_sep
   differentiation).

---

## Hash log

**Location:** `~/.config/bitledger/hash_log.jsonl` (configurable in master config).
Newline-delimited JSON — one object per line, append-only.

**Entry schema:**
```json
{
  "wire_id":       "a3f8b291c4d7e520c1d3f4b2",
  "semantic_id":   "c7d9f4010a3b2c1d",
  "timestamp":     "2026-04-18T14:32:01.423Z",
  "log_direction": "encode",
  "wire_bytes_hex":"9c000000000020956f001d4b8040",
  "amount":        "149.99",
  "account_pair":  4,
  "tx_direction":  0,
  "tx_status":     0,
  "currency":      0,
  "session_id":    "deadbeef01000000",
  "template_id":   null,
  "instance":      null,
  "parent_wire_id":null
}
```

**wire_id:** `blake2b(wire_bytes, digest_size=16).hexdigest()` — 32 hex chars.
Same bytes on sender and receiver → same wire_id. Shared record reference.

**semantic_id:** `blake2b(canonical, digest_size=16).hexdigest()` where canonical
= `str(amount)|account_pair|direction|status|currency|sender_id` as bytes.
Same transaction regardless of wire encoding → same semantic_id.

**Duplicate detection:**
- `wire_id` match → existing log entry for exact same blob ("replay or re-send")
- `semantic_id` match AND no `template_id` → DecoderWarning ("same transaction, check for accidental duplicate")
- `semantic_id` match AND `template_id` present → logged as recurring instance, no warning

**Opt-in:** hash log is disabled by default. Activated by `--hash-log` flag on
encode/decode, or `hash_log_enabled: true` in master config.

---

## Templates

**Location:** `~/.config/bitledger/templates/` — one JSON per template, named
`<name>.json`. Configurable via `template_dir` in master config.

**Template JSON schema:**
```json
{
  "name": "monthly-rent",
  "template_id": "a3f8b291c4d7e520",
  "amount": "1495.00",
  "account_pair": 4,
  "direction": 0,
  "status": 0,
  "debit_credit": 0,
  "quantity_present": false,
  "description": "Rent {YYYY}-{MM}",
  "profile": null,
  "created": "2026-04-18T09:00:00Z",
  "counter": 0,
  "instances": 0,
  "last_used": null
}
```

**Wire differentiation via record_sep counter:**
```
record_sep = (counter % 31) + 1        # values 1..31
group_sep  = min(counter // 31, 15)    # values 0..15
```
Capacity: 31 × 16 = 496 instances before full wrap. Warn when `counter >= 480`.
After wrap: `record_sep` and `group_sep` repeat. `wire_id` will match a previous
instance — the log detects this and notes it as a counter wrap, not a true duplicate.

**template_id:** `blake2b(name|amount|account_pair|direction|currency, digest_size=8).hexdigest()`
— 16 hex chars. Stable identifier for the template across renames or moves.

**Description interpolation** (applied at encode time):
- `{YYYY}` → 4-digit year
- `{MM}` → 2-digit month
- `{DD}` → 2-digit day
- `{MONTH}` → full month name

---

## Recall

Search and filter the hash log. Two modes:

**Browse mode** — list matching log entries in a table:
```
bitledger recall --amount 149.99
bitledger recall --account-pair 4
bitledger recall --since 2026-04-01
bitledger recall --template monthly-rent
bitledger recall --last 20
```

**Lookup mode** — find a specific record by partial hash (wire_id or semantic_id):
```
bitledger recall --id a3f8b291
```

**Retransmit** — re-encode a found record as a new wire blob:
```
bitledger recall --id a3f8b291 --retransmit --out new.bl
```

Retransmit uses a per-`wire_id` retransmit counter stored in the log (counts
how many times this specific record has been retransmitted). Applies the same
record_sep / group_sep differentiation as templates to produce a genuinely new
wire blob → new wire_id. New log entry includes `parent_wire_id` pointing to the
original.

---

## CLI surface

### New subcommands

```
bitledger log list [--since DATE] [--amount AMT] [--account-pair N] [--last N]
bitledger log find --id PARTIAL_HASH
bitledger log stats                          ← count, date range, top amounts

bitledger template save --name NAME --amount AMT [--account-pair N] [--direction N]
                        [--description TEXT] [--profile PATH]
bitledger template list
bitledger template show NAME
bitledger template use NAME [--out PATH] [--description TEXT] [--hash-log]
bitledger template history NAME              ← log entries for this template

bitledger recall [--amount AMT] [--account-pair N] [--since DATE]
                 [--template NAME] [--last N]
bitledger recall --id PARTIAL_HASH [--retransmit --out PATH]
```

### Flags added to existing commands

```
bitledger encode ... --hash-log [PATH]       ← compute and log wire_id + semantic_id
bitledger encode ... --reject-duplicate      ← exit 2 instead of warn on duplicate
bitledger decode ... --hash-log [PATH]       ← same on decode side
```

---

## New files

| File | Purpose |
|------|---------|
| `bitledger/hasher.py` | `compute_wire_id`, `compute_semantic_id`, `compute_session_id`, `compute_template_id` |
| `bitledger/hash_log.py` | `LogEntry` dataclass, `append_log`, `check_log`, `search_log`, `default_log_path` |
| `bitledger/templates.py` | `Template` dataclass, `save_template`, `load_template`, `list_templates`, `use_template`, `record_sep_for_counter`, `interpolate_description` |
| `bitledger/cli_log.py` | `cmd_log_list`, `cmd_log_find`, `cmd_log_stats`, `add_log_cli` |
| `bitledger/cli_template.py` | `cmd_template_save`, `cmd_template_list`, `cmd_template_show`, `cmd_template_use`, `cmd_template_history`, `add_template_cli` |
| `bitledger/cli_recall.py` | `cmd_recall`, `add_recall_cli` |
| `tests/test_hasher.py` | Hash computation stability, uniqueness, algorithm |
| `tests/test_hash_log.py` | Append, lookup, duplicate detection, search filters |
| `tests/test_templates.py` | Save/load, record_sep counter, description interpolation, template_id stability |

## Modified files

| File | Change |
|------|--------|
| `bitledger/config.py` | 5 new `MasterConfig` fields |
| `bitledger/cli.py` | Wire up `log`, `template`, `recall`; add `--hash-log`/`--reject-duplicate` to encode/decode |
| `system/TASKS.md` | New tasks section for v1.1.0 |
| `RELEASE.md` | New v1.1.0 section |
| `pyproject.toml` | `version = "1.1.0"` |

---

## Master config additions

```json
{
  "warn_short_form_mismatch": true,
  "hash_log_enabled": false,
  "hash_log_path": "",
  "hash_ids": "both",
  "duplicate_action": "warn",
  "template_dir": ""
}
```

`hash_log_path` and `template_dir`: empty string = use XDG default.
`hash_ids`: `"wire"`, `"semantic"`, or `"both"`.
`duplicate_action`: `"warn"` or `"reject"`.

---

## What is deferred

- Chain hashing (`prev` field in log entries) → v1.2.0
- Wire-embedded hash via extension bytes → v2.0.0
- `log verify` chain walk → v1.2.0
- `template export/import` for receiver coordination → v1.2.0
- Schedule / date-based auto-trigger for templates → future
