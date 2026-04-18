# Architectural Decision Log — BitLedger

Non-obvious decisions made during development. Read before touching encoder, decoder, or models.

Format:
```
## YYYY-MM-DD — [decision title]

**Decision:** [what was decided]

**Context:** [what situation prompted this]

**Why:** [the reasoning]

**Consequence:** [what this commits us to or rules out]
```

---

## 2026-04-14 — Adopted Workwarrior orchestrator system as dev control plane

**Decision:** Use the Workwarrior multi-agent orchestrator framework (roles, templates, gates, workflows, scripts) as the development control plane for BitLedger.

**Context:** Project initialization. Need a structured way to manage parallel agent work, task contracts, and quality gates.

**Why:** The framework provides proven patterns for: task card contracts (Gate A), test verification before merge (Gate B), and serialization safety for high-risk files. The generic infrastructure transfers cleanly; only project-specific content was replaced.

**Consequence:** All work follows the Orchestrator → Builder → Verifier → Docs handoff sequence. No implementation starts without a task card. No merge without Verifier sign-off.

---

## 2026-04-18 — CONFLICT-005 resolution (bits 37–38, account_pair 1111)

**Decision:** For Layer 3 records with `account_pair = 0b1111` (compound continuation), bits **37–38** carry the **2-bit continuation sub-type** (`00` Standard, `01` Correcting, `10` Reversal, `11` Cross-batch) per [BitLedger_CompoundMode_DesignNote.md](../../project/protocol%20docs/markdown/BitLedger_CompoundMode_DesignNote.md). **Cross-layer Rules 1 and 2 are suspended** for these records (do not require bit 37 = bit 29 or bit 38 = bit 30). For **all other** account pairs, bits 37–38 remain **mirrors** of bits 29–30 and Rules 1–2 **apply**.

**Context:** CONFLICT-005 ([bitledger_clireview.md](../../project/reviews/bitledger_clireview.md) §5): the main field map describes 37–38 as mirrors of 29–30, while compound continuation text assigns 37–38 to sub-type — mutually exclusive if enforced together on `1111` records.

**Why:** The compound design note and worked examples require distinguishable continuation kinds without tying them to Set A direction/status mirrors; mirror rules remain the default integrity check for normal pairs.

**Consequence:** `encoder.py` / `decoder.py` branch on `account_pair == 1111`; `TransactionRecord` gains explicit continuation sub-type for `1111`; compound tests assert suspension of mirror checks only in that case. TASK-2.06 / TASK-2.07 may proceed under this resolution.

---

## 2026-04-18 — CLI binary `.bl` plus terminal formatting

**Decision:** The BitLedger CLI writes **canonical protocol bytes** to **`--out path.bl`** (project convention: `*.bl` = BitLedger binary artifact). Unless **`--quiet`**, it also prints a **formatted** representation (journal and/or hex via `formatter.py`) to the terminal for the same emitted payload so operators can verify output without hex-dumping the file.

**Context:** Operators need both machine-readable archives and human-readable confirmation in one run.

**Why:** Matches BitPads CLI’s `--out` pattern; keeps wire format pure in `.bl` while avoiding a second tool invocation.

**Consequence:** Document `--out`, `--quiet`, and default print behaviour in README / CLI help when `bitledger.py` is implemented. Normative spec remains v3 bytes; `.bl` is a filename/container convention, not an extra header, unless explicitly extended later.

---

## 2026-04-18 — TransactionRecord.true_value uses Decimal

**Decision:** `TransactionRecord.true_value` is typed as `decimal.Decimal`, not `float`, despite the condensed overview showing `float` in a sketch.

**Context:** Spec prohibits float in the encode path; Python `float` misrepresents values like $4.53.

**Why:** Aligns with TASK-2.03 risk note and encoder fragility.

**Consequence:** Application code must pass `Decimal` into records; JSON profiles store amounts as strings if needed.
