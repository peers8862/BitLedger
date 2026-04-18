# Plan: value CLI UX (amount parsing, auto-SF, check-amount, rounding)

Goals: users type **full real amounts** (e.g. `24,456,346,932.00`); the tool proposes or selects **`sf` / `dp`** without mental math; **rounding is visible before commit**; behavior stays aligned with **README / TECHNICAL_OVERVIEW** (bits 26–27, `account_pair` modes, Rule 3, optional batch rounding balance).

Related context: [`backlog_april18.md`](backlog_april18.md), [`cli_readme.md`](cli_readme.md).

---

## Phase 0 — Parsing and normalization (foundation)

| Item | Description | Acceptance |
|------|-------------|------------|
| **0.1 Amount string** | Strip `_` and `,` grouping; trim spaces; parse with `Decimal` only. Reject `float` paths. | Unit tests: commas, leading/trailing spaces, negative (if allowed by product), scientific notation (optional policy). |
| **0.2 Single source** | One function used by `encode`, `check-amount`, `suggest-sf` (e.g. `bitledger/amount_parse.py` or in `cli_encode.py`). | No duplicated parsing logic. |
| **0.3 Error messages** | Clear failures: empty, invalid chars, overflow **before** SF search. | Stable message substrings for tests. |

**Risk:** Locale decimal comma vs `.` — decide one norm (e.g. `.` only in v1) or explicit `--locale` later.

---

## Phase 0.5 — Implemented: `make` / `suggest-sf` / `check-amount`

`bitledger make` (alias `suggest-sf`) is the **primary** “plan a BitLedger record” command: **smallest SF** in range (or **`--sf`**), **N, A, r**, **bits 26–27**, delta when rounded, **copy-paste `encode`**. **`check-amount`** uses the same **`resolve_encoding_plan`** logic with a **verification-only** layout (STATUS line, no encode block). **`encode --amount`** accepts **commas / underscores** via `parse_amount_string`. See [`cli_readme.md`](cli_readme.md).

---

## Phase 1 — `check-amount` + **`make --json`** — *done*

- **`check-amount`** + **`make --json`** — shipped; see [`cli_readme.md`](cli_readme.md).

---

## Phase 2 — Auto-SF on `encode` — *done*

- **`encode --auto-sf`** + **`--min-sf` / `--max-sf`**, conflict with **`--sf`**, uses **`find_smallest_sf`** (`tests/test_cli_encode_advanced.py`).
- **`make`** / **`suggest-sf`** already covered smallest-SF search (Phase 0.5).

**Policy note:** Wire allows SF **7-bit**; table today is **0–17** ([`backlog_april18.md`](backlog_april18.md) §3).

---

## Phase 3 — Rounding engagement on `encode` — *partially done*

| Item | Status |
|------|--------|
| **3.1** Require **`--accept-rounding`** when **`--amount`** implies `rf=1` | **Done** (stderr hint points to `check-amount` / `make`). |
| **3.2** Extra verbose block on encode | *Deferred* (optional). |
| **3.3** Journal precision line | Already reflects `rf` from record. |

---

## Phase 4 — Optional ergonomics (non-blocking)

| Item | Description | Acceptance |
|------|-------------|------------|
| **4.1 Suffixes** | Optional: `2.5B`, `12M` parsed to `Decimal` after explicit opt-in `--amount-suffix` or global config. | Document ambiguity (`M` = million SI). |
| **4.2 Profile hints** | Profile JSON optional `"value_tier": { "default_sf": 7, "dp": 2 }` for org defaults. | `load_profile` merges; documented in `cli_readme.md`. |
| **4.3 `setup` wizard** | Ask “typical magnitude band” → seeds `sf`/`dp` in profile. | Manual smoke or wizard test. |

---

## Phase 5 — Protocol-aligned batch rounding (larger scope)

| Item | Description | Acceptance |
|------|-------------|------------|
| **5.1 Layer 2 rounding balance** | Document current gap; design incremental update when emitting records in a batch tool. | Spec cross-ref TECHNICAL_OVERVIEW bits 42–45. |
| **5.2 Multi-record CLI** | Optional future: `batch encode` / stream → maintains rounding balance + Rule 5 close. | Out of scope for minimal `encode` unless prioritized. |

---

## Phase 6 — Documentation and CI

| Item | Description | Acceptance |
|------|-------------|------------|
| **6.1 `cli_readme.md`** | Sections for `check-amount`, `suggest-sf`, `--auto-sf`, amount parsing, rounding flags. | Single source for operators. |
| **6.2 `test-baseline.yaml`** | New files trigger targeted pytest for new modules. | Matches existing pattern. |
| **6.3 Examples** | README or `cli_readme`: one **billion-scale** walkthrough using `suggest-sf` then `encode`. | Copy-paste works from clean install. |

---

## Suggested implementation order

1. **Phase 0** (parsing) — low risk, unblocks everything.  
2. **Phase 1** (`check-amount`) — highest user value, no wire format change.  
3. **Phase 2.1–2.2** (`suggest-sf`) — pairs with check-amount.  
4. **Phase 2.3–2.4** (`encode --auto-sf`) — convenience path.  
5. **Phase 3** (rounding gates) — trust / compliance.  
6. **Phases 4–6** as time allows.

---

## Non-goals (for this plan)

- Changing **25-bit** `N` ceiling or core 40-bit layout (separate spec / vNext).  
- Replacing **`account_pair`–driven rounding** with a single global mode (would violate doc intent).  
- Full **DTN / multi-hop session** orchestration (separate product track).

---

## Open decisions (record before coding)

1. **Auto-SF policy:** smallest `sf` first vs “prefer exact `R` with smallest `|R - round(R)|`” tie-break.  
2. **Rounding gate:** default **warn** vs **abort** unless `--accept-rounding`.  
3. **Locale:** ASCII `.` only for v1 or accept `,` decimal.  
4. **SF > 17:** reject, clamp, or leave wire set with decode failure until table extended.
