# CONFLICT-005 — Detailed explication

This document explains **CONFLICT-005**: a real ambiguity between two parts of the BitLedger Layer 3 field map when `account_pair = 1111` (compound continuation). It records the **resolved** interpretation used by this project’s encoder/decoder work.

**Related reading (in this repo):**

- [BitLedger_CompoundMode_DesignNote.md](BitLedger_CompoundMode_DesignNote.md) — compound mode purpose, 1111 marker, **sub-type table for bits 37–38**, completeness, Layer 2 compound prefix, BitPads v2 tradeoffs.
- [BitLedger_Protocol_v3.docx.md](BitLedger_Protocol_v3.docx.md) — full Layer 3 layout, Rules 1–2, compound section.
- [bitledger_clireview.md](../../reviews/bitledger_clireview.md) — original conflict statement (§5).

---

## 1. The Layer 3 fields involved (1-indexed spec bits)

In a **40-bit Layer 3 record** (Set A + BitLedger block):

| Bits (spec) | Set A / value side | BitLedger block |
|-------------|--------------------|-----------------|
| 1–32 | Value block (multiplicand/multiplier, rounding, split order, direction **29**, status **30**, debit/credit, quantity-present **32**, …) | — |
| 33–36 | — | **Account pair** (4 bits). Values `0000`–`1101` standard pairs; `1110` correction/void; **`1111` compound continuation** (only if compound mode + batch rules allow). |
| 37–38 | — | Documented **twice** under two incompatible meanings (see §2). |
| 39 | — | **Completeness** (partial vs full; for `1111`, chains continuations). |
| 40 | — | Extension flag |

**Cross-layer Rules 1 and 2 (normal records):**

- **Rule 1:** bit **37** must equal bit **29** (direction in Set A equals “Direction (BL)” in BitLedger block).
- **Rule 2:** bit **38** must equal bit **30** (status in Set A equals “Status (BL)” in BitLedger block).

These rules give **redundant encoding** of direction/status so a single-bit flip in either place is detectable.

---

## 2. The contradiction (why CONFLICT-005 exists)

### 2.1 Reading A — “Bits 37–38 always mirror 29–30”

The main Layer 3 / BitLedger field tables state that bit 37 is direction (must match bit 29) and bit 38 is status (must match bit 30). That implies **37 and 38 are not free**: they are **copies** of 29 and 30 for validation.

### 2.2 Reading B — “Continuation sub-type lives in bits 37–38”

The **compound continuation** design (and the Universal Domain companion text) treats **`1111` records differently**: bits **37–38** carry a **2-bit continuation sub-type**:

| Bits 37–38 | Sub-type (1111 only) |
|------------|----------------------|
| 00 | Standard linked leg (e.g. COGS after revenue) |
| 01 | Correcting |
| 10 | Reversal |
| 11 | Cross-batch continuation |

Those four meanings are **not** the same as “mirror of direction/status”. Example from the design note: a **correcting** continuation (sub-type `01`) may need a wire pattern where **37–38 = 01** while bits **29–30** describe the **visible** direction/status of **this** leg. If Rules 1–2 were enforced literally, **01** in 37–38 would **force** 29 and 30 to equal 0 and 1 respectively, which may not match the accounting story you want on the Set A side.

So the spec family contains **mutually exclusive instructions** unless one scope is narrowed.

---

## 3. Resolution (Orchestrator / project norm)

**Adopted interpretation:**

1. **When `account_pair != 1111`:**  
   - Bits **37** and **38** are **mirrors** of bits **29** and **30**.  
   - **Rules 1 and 2 apply**; violation ⇒ `DecoderError` (or encoder rejects inconsistent input).

2. **When `account_pair == 1111`:**  
   - Bits **37–38** carry the **continuation sub-type** (`00`–`11`) as defined in [BitLedger_CompoundMode_DesignNote.md](BitLedger_CompoundMode_DesignNote.md).  
   - **Rules 1 and 2 are suspended** for that record: the decoder **does not** require `37 == 29` or `38 == 30`.  
   - Bits **29–30** still mean direction/status **for the Set A / presentation slice** of that continuation record; bits **37–38** mean **which kind of continuation** this is.

**Rationale:**  
The compound design note is internally consistent and explains audit behaviour (correcting vs reversal vs cross-batch). The mirror rules remain the strong default for **all non-continuation** records. Encoder/decoder and tests follow this split.

**Logged as:** `system/logs/decisions.md` — entry **2026-04-18 — CONFLICT-005 resolution (bits 37–38, account_pair 1111)**.

---

## 4. Encoder / decoder consequences

| Component | Behaviour |
|-----------|-----------|
| **Encoder** | For `1111`, pack sub-type into bits 37–38; set 29–30 from the transaction’s Set A semantics; **do not** overwrite 37–38 to match 29–30. For other pairs, set 37–38 from 29–30 (or reject if caller sends mismatch). |
| **Decoder** | If `(bits 33–36) != 1111`, enforce Rules 1–2. If `== 1111`, read sub-type from 37–38; **skip** mirror checks; still validate other rules (rounding flags, completeness chains, compound session/batch gates). |
| **`models.py`** | `TransactionRecord` should carry an explicit **optional** continuation sub-type (or an enum) when pair is `1111`, so formatter/simulator can display “Standard / Correcting / …” without inferring from illegal mirror assumptions. |

---

## 5. Session / batch gates (unchanged)

`1111` remains **invalid** unless:

- Session (Layer 1 / config) allows compound mode, **and**
- Layer 2 **compound prefix** is not `00` forbidding compounds for that batch,

as already specified in TASK-2.06 / protocol text. CONFLICT-005 does **not** relax those gates; it only clarifies **what bits 37–38 mean** once `1111` is legal.

---

## 6. CLI output: binary `.bl` and terminal formatting

**Normative wire format** remains BitLedger v3 bytes only (no BitPads Meta in `.bl` unless a future explicit `--wrap` mode is added).

### 6.1 `.bl` file convention (this project)

| Item | Convention |
|------|------------|
| **Filename** | `*.bl` — **BitLedger binary artifact** (tooling convention; not a separate ISO-style standard). |
| **Contents** | Raw octets: concatenation of **Layer 1 (8)** + **Layer 2 (6) or L2 short-form (1)** + **Layer 3 (5 per record)** + optional **control records (1 each)** as implemented by the command. Default `encode`/`emit` SHOULD document which slice is written (e.g. “single record” = 5 bytes only vs “session blob” = full prefix). |
| **Endianness / bit order** | MSB-first packing per spec; on-disk bytes are the same order as on-wire in the reference implementation. |
| **Git** | Do not commit user `.bl` outputs unless they are tiny **fixture vectors** under `tests/`. |

### 6.2 Terminal output (same invocation)

For human use, the CLI SHOULD default to **both**:

1. **Binary path** — write the same bytes to `--out path.bl` when `--out` is given (aligned with BitPads `--out` habit).
2. **Formatted transcript to stderr or stdout** — journal line / hex / bit grouping (via `formatter.py`) so a run is self-describing in the terminal without opening the file.

Suggested behaviour (implementation detail, not yet coded):

- **`--out file.bl`** — required or strongly recommended for `encode`; writes binary.
- **`--quiet`** — suppress formatted print; only exit code (for scripts).
- **Default without `--quiet`** — print formatted decode of what was written (or `--format journal,hex`).

Hex on the terminal should match the bytes in `.bl` for the same operation.

---

## 7. Summary

| Question | Answer |
|----------|--------|
| What is CONFLICT-005? | Spec tension: bits 37–38 cannot be **both** strict mirrors of 29–30 **and** a 2-bit continuation sub-type on `1111`. |
| What do we do? | **Mirrors for non-1111; sub-type for 1111** with Rules 1–2 **off** for continuation records. |
| Where is compound narrative? | [BitLedger_CompoundMode_DesignNote.md](BitLedger_CompoundMode_DesignNote.md) (copy in-repo). |
| Where do `.bl` + print go? | **§6** — binary to `*.bl`, human-readable to terminal unless `--quiet`. |
