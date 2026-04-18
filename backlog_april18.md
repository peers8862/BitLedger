# Backlog — 2026-04-18

Consolidated from implementation review: **what is solid**, **edge cases** (rejections and traps), and **follow-on gaps**. Paths are relative to the `bitledger/` project unless noted.

---

## 1. Solid and usable (good to go)

- **Value path:** `encode_value` / `decompose`, rounding modes, overflow checks, **Decimal-only** monetary input, **SF indices 0–17** via `SCALING_FACTORS`, quantity vs split decode in `decode_value`.
- **Layer packing:** Layer 1 (incl. **CRC-15**), Layer 2 (full + **0x6F** short form), **40-bit** Layer 3 `serialise` / `unpack_record`.
- **Decoder rules:** Mirror rules (with **1111** / CONFLICT-005 suspension), invalid rounding nibble, **L1 CRC**, **compound context** check after unpack, optional **`validate_batch_integrity`** for Rule 5 when callers have counts.
- **CLI:** `setup`, `encode` (raw `--A`/`--r` or `--amount`, profile/L1/L2 overrides, `--out` `.bl`, `--emit-l2`, `--description`), `decode` (hex or `--in`), `simulate`; exit codes for usage vs protocol errors.
- **Profiles:** JSON save/load; **default** name overwrite guarded unless `force` / `setup --force`.
- **Human output:** Layer headers, README-style journal (optional binary/hex from `n40`), compact record summary / pipe-grouped binary.
- **Quality gate:** `python -m pytest tests/` (see `system/config/test-baseline.yaml`).

---

## 2. Thinner / know the limits

- **Rule 5** on single-record decode: not automatic; only when orchestration calls `validate_batch_integrity`.
- **Control records:** `encode_control` / `decode_control` tested; no full framed multi-record session in the CLI.
- **Wire gaps:** decimal code **111**, extension bytes, rich batch/session state machines — partial or explicitly “not implemented” where code comments apply.

---

## 3. Edge cases (numeric and value encoding)

- **`N` range:** `N` must be in **0 … 33,554,431**; above → `EncoderError` (overflow).
- **`S` (optimal split):** must be **0 … 17** for `decompose`; outside → `EncoderError`.
- **`encode_value`:** **`float`** rejected; use **`Decimal`**.
- **SF index vs wire:** Value layer accepts **`sf_index` only in `SCALING_FACTORS` range (0–17)**. Layer 2 still carries a **7-bit** SF field (0–127); indices **≥ 18** are an edge case (likely failure at encode/decode value, not necessarily at Layer 2 unpack alone).
- **Rounding nibble:** **`rounding_flag == 0`** and **`rounding_dir == 1`** illegal on encode (`serialise`) and decode (Rule 3).
- **Decimal wire `111` (D=7):** not implemented → `EncoderError` from `_wire_dp_to_d`; decode: **`decimal_position_wire > 6`** → `DecoderError`.

---

## 4. Edge cases (Layer 1)

- **Length:** must be **exactly 8 bytes**.
- **CRC-15:** wrong remainder / flipped payload bits → **`Layer 1 CRC-15 verification failed`**.
- **SOH:** high bit of 49-bit payload must be **1**; else **`SOH marker missing`**.

---

## 5. Edge cases (Layer 2)

- **Shape:** **6 bytes** full header or **single `0x6F`** short form; else `DecoderError`.
- **`transmission_type == 00`:** invalid on encode and decode; CLI `--txtype 0` rejected.

---

## 6. Edge cases (Layer 3 and cross-layer)

- **Rules 1 & 2:** bit **37** must match direction (29), bit **38** must match status (30), **except** `account_pair == 0b1111` (CONFLICT-005: subtype in those bits; mirrors not checked).
- **Rule 6 (compound):** **`1111`** on decode rejected unless **L1 compound active** and **L2 `compound_prefix != 00`** (`validate_compound_context`). Encoder matches for `serialise` with `1111`.
- **`1111` encode:** **`continuation_subtype`** must be **0…3** when used.

---

## 7. Edge cases (quantity vs split)

- **`quantity_present`:** decode uses **`N = A * r`** vs **`(A << S) | r`**. Wrong flag or wrong `A`/`r` changes semantics without always being a structural wire error.

---

## 8. Edge cases (control, profiles, CLI)

- **Control byte:** high bit set (not a control record) → `decode_control` raises.
- **Profile:** missing file → `ProfileError`; saving **`name == "default"`** over existing file → `ProfileError` unless **`force`**.
- **Decode CLI:** invalid hex → exit **1**; protocol errors → **2**.

---

## 9. Edge cases (short-form Layer 2)

- **`0x6F`** expands to **code defaults** in the decoder. On-disk short form with **semantics that do not match** those defaults yields **logical** session/batch mismatch, not necessarily an immediate structural error.

---

## 10. Backlog — high-impact test / doc follow-ups

- Explicit tests or docs for **SF wire 18–127** vs table **0–17** (error surface and intended product behavior).
- **Quantity vs non-quantity** confusion and golden vectors in CLI help or `cli_readme.md`.
- **Short-form defaults** vs real batch mismatch (negative test or warning).
- **Multi-record sessions**, framing, control streams, batch close (Rule 5) in a small reference orchestration or CLI subcommand (if in scope).

---

## 12. Backlog — profile **store**, **list**, **activate** (anti-sprawl)

**Goal:** Users can discover profiles, pick a default for daily use, and avoid typing long `--profile` paths—**without** adding many top-level verbs (`list-profiles`, `activate-profile`, …).

**Preferred shape (single entry point):** one group, e.g. **`bitledger profile …`**, not new first-class commands for each action:

| Action | Proposed UX (sketch) | Notes |
|--------|----------------------|--------|
| **Store** | Already covered by **`setup --out path.json`**; optional **`profile import`** if we ever ingest foreign JSON. | Avoid duplicating `save_profile`; document “store = save path you choose.” |
| **List** | **`bitledger profile list [--dir DIR]`** | Default `DIR` = e.g. `./profiles` or `$BITLEDGER_PROFILE_DIR`; print **name** (from JSON) + path + one-line summary (currency, sf, dp). |
| **Activate** | **`bitledger profile use <name-or-path>`** writes **one small pointer file** (e.g. `~/.config/bitledger/active` or project-local `.bitledger/active`) containing resolved absolute path. | **Do not** copy JSON; pointer only. |
| **Resolve** | **`encode` / `make` / `decode`?** If `--profile` omitted, read pointer then env **`BITLEDGER_PROFILE`** then fail closed with a clear message. | Order of precedence documented once. |

**Anti-sprawl rules:** **`make`** is the single primary command for **planning a record** (SF, numbers, copy-paste `encode`). **`suggest-sf`** stays an alias of `make`. **`check-amount`** is a separate **verification** printout (same flags, no suggested `encode` block)—not merged into `make` so operators can verify without noise. Prefer **environment + one pointer** for activation over many verbs. Optional later: **`make --json`** for scripts (does not replace `check-amount` for human verify).

---

## 13. Next priorities (fresh pass — strengthen, don’t sprawl)

Ordered for **impact / cohesion** vs **new surface area**.

### Tier A — finish the value UX loop (mostly one codepath) — *partially done*

1. **`encode --auto-sf`** — **done** (`--min-sf` / `--max-sf`, same **`find_smallest_sf`** as `make`; mutually exclusive with **`--sf`**).
2. **Rounding gate on `encode`** — **done** (**`--accept-rounding`** required when **`--amount`** would round).
3. **`make --json`** — **done** (machine-readable plan + **`suggested_encode_argv`**).

### Tier B — profile ergonomics (one subcommand group) — *done*

4. **`bitledger profile list | use | show`** — shipped; pointer under **`$XDG_CONFIG_HOME/bitledger/active.json`** (or **`~/.config/bitledger/active.json`**). **`BITLEDGER_PROFILE`** and resolution order documented in **`cli_readme.md`**.

### Tier C — trust and spec clarity (docs/tests, little CLI)

5. **SF 18–127** — document “wire vs table” and single failure mode; extend table only when spec demands.
6. **Quantity + short-form** — one doc diagram + 2–3 pytest cases; no new flags unless decode warns on suspicious `0x6F`+amount mismatch.

### Tier D — defer (scope / sprawl risk)

7. **Multi-record / Rule 5 orchestration** — library helpers first; CLI subcommand only if it stays **one** optional `batch` entry later.

**Principle:** extend **`make` + `encode` + `profile`** as **families**; resist new top-level verbs until a family is clearly full.

---

## 14. Reference files

- `bitledger/cli_readme.md` — CLI flags and exit codes.
- `bitledger/PLAN_value_cli_ux.md` — value UX phases (merge `check-amount` into `make` where possible).
- `bitledger/system/config/test-baseline.yaml` — suggested pytest commands by change type.
- `bitledger/bitledger/encoder.py`, `decoder.py`, `cli_encode.py` — primary raise sites for protocol errors.
