# Explorer A Report: Spec/Docs Drift Audit

Explorer: Explorer A
Date: 2026-04-14

Files read:
- `/Users/mp/making/bitledger/TECHNICAL_OVERVIEW.md` — condensed Technical Overview (markdown equivalent of `BitLedger_Technical_Overview.docx`; file header confirms this relationship)
- `/Users/mp/making/bitledger/README.md` — project README containing key protocol details cross-referencing v3 spec
- `/Users/mp/making/bitledger/system/CLAUDE.md` — project context and module registry
- `/Users/mp/making/bitledger/system/logs/decisions.md` — architectural decision log
- `/Users/mp/making/bitledger/system/context/working-conventions.md` — agent operating norms
- `/Users/mp/making/bitledger/system/fragility-register.md` — fragility policy
- `/Users/mp/making/bitledger/system/TASKS.md` — task board
- `/Users/mp/making/bitledger/mathmodel_by_grok.md` — formal mathematical model (quotes from full spec)
- `/Users/mp/making/bitledger/review_by_grok.md` — external review quoting protocol details

**Access note:** `BitLedger_Protocol_v3.docx` and `BitLedger_Technical_Overview.docx` are binary files. The Bash execution tool was unavailable, preventing the Python XML extraction script from running. This audit therefore uses `TECHNICAL_OVERVIEW.md` (which self-identifies as "a condensed technical reference" of the Technical Overview docx) as Source B, and `README.md` plus `mathmodel_by_grok.md` as the closest available cross-references to the full protocol spec (Source A). Where Source A cannot be directly verified, items are flagged as unverifiable rather than assumed aligned.

---

## Summary

confirmed-aligned: 14
spec-vs-overview-conflict: 5 (HIGH: 2, MEDIUM: 2, LOW: 1)
spec-only gaps: 6
overview-only additions: 9

---

## Contradiction Matrix

---

### CONFIRMED-ALIGNED

1. **Layer 1 field layout** — Both sources agree: 64 bits, SOH at bit 1, Protocol Version bits 2–4, Core Permissions bits 5–8, Session Defaults bits 9–12, Sender ID bits 13–44 (32 bits), Sub-Entity ID bits 45–49 (5 bits), CRC-15 bits 50–64. README and TECHNICAL_OVERVIEW.md are consistent.

2. **Layer 2 field layout** — Both agree: 48 bits, Transmission Type bits 1–2 (00=invalid), SF bits 3–9 (7-bit), Optimal Split bits 10–13, Decimal Position bits 14–16, Enquiry/ACK bells bits 17–18, Group Separator bits 19–22, Record Separator bits 23–27, File Separator bits 28–30, Entity ID bits 31–35, Currency Code bits 36–41, Rounding Balance bits 42–45, Compound Prefix bits 46–47, Reserved bit 48 = 1.

3. **Layer 3 field layout** — Both agree: 40 bits. Multiplicand bits 1–17, Multiplier bits 18–25, Flags bits 26–32 (Rounding, RoundDir, SplitOrder, Direction, Status, Debit/Credit, QuantityPresent), Account Pair bits 33–36, BL Direction bit 37, BL Status bit 38, Completeness bit 39, Extension Flag bit 40.

4. **Value encoding formula** — Both agree: N = A × (2^S) + r, A = floor(N / 2^S), r = N mod 2^S, Real Value = (N × SF) / 10^D. Maximum N = 33,554,431 (2^25 - 1). Default split S = 8.

5. **CRC-15 algorithm** — TECHNICAL_OVERVIEW.md provides implementation: polynomial 0x8003 (x^15 + x + 1). mathmodel_by_grok.md confirms "polynomial x^15 + x + 1" and CRC-15 over L1 bits 1–49. Encoder appends crc15(49 bits), decoder verifies crc15(64 bits) == 0.

6. **Rounding signal bits 26–27** — Both agree: 00=exact, 10=rounded down, 11=rounded up, 01=protocol error. README and TECHNICAL_OVERVIEW.md tables are identical.

7. **Cross-layer validation rules** — Both agree: bit 29 must equal bit 37 (Direction), bit 30 must equal bit 38 (Status). Violation raises ProtocolError.

8. **Control record structure** — Both agree: 8-bit format `0 [TTT] [PPPP]`, leading 0 distinguishes from transaction records. Type assignments (000–110) are consistent across README and TECHNICAL_OVERVIEW.md.

9. **Layer 2 short-form** — Both agree: 1-byte control record `0 110 1111` replaces 48-bit header when all values equal session defaults. README: "Type 110 Layer 2 short-form (all defaults, skip 48-bit header)". TECHNICAL_OVERVIEW.md: consistent.

10. **Compound transaction mechanics** — Both agree: `1111` account pair code signals continuation, `bit 39 = 1` (Partial) on the first record, `bit 39 = 0` (Full) on the final continuation. Compound group identity = Record Separator value.

11. **Account pair codes 0000–1101** — 14 of the 16 codes are identically described in both README.md and TECHNICAL_OVERVIEW.md account pair tables.

12. **Module count and names** — Both CLAUDE.md and README.md list 11 Python modules: bitledger.py, encoder.py, decoder.py, setup_wizard.py, simulator.py, formatter.py, models.py, profiles.py, currencies.py, control.py, errors.py.

13. **Transmission Type code 00 is invalid** — TECHNICAL_OVERVIEW.md Layer 2: "Code 00 is INVALID — ensures first byte is never all zeros". Not contradicted anywhere.

14. **Compound mode requires two conditions** — TECHNICAL_OVERVIEW.md Critical Notes: "Compound mode requires both Layer 1 bit 11 = 1 AND Layer 2 compound prefix ≠ 00." Not contradicted elsewhere.

---

### SPEC-VS-OVERVIEW CONFLICTS

#### CONFLICT-001: Account Pair `1110` — "Correction" vs "Correction / Netting"
- Spec says (README.md, Account Pair Codes table): `1110` = **"Correction / Netting"**
- Overview says (TECHNICAL_OVERVIEW.md, Account Pair Table): `1110` = **"Correction"** only; behavior column reads "Inference suspended / Inference suspended" for both Dir=0 and Dir=1
- File/section: README.md line 96 vs TECHNICAL_OVERVIEW.md line 236
- Severity: **MEDIUM** — affects how implementers name this account type and whether "Netting" is a valid use case for this pair code. The behavior description "Inference suspended" is present only in the Technical Overview, not in the README/protocol.
- Recommended resolution: Treat the full protocol spec (BitLedger_Protocol_v3.docx) as authoritative. Read the .docx directly before implementing `account_pair = 0b1110` behavior. Do not assume the shorter name is canonical.

#### CONFLICT-002: Error Detection — "Three mechanisms" vs six rules
- Spec says (README.md, Error Detection section): **"Three independent error detection mechanisms operate on every record without a separate checksum field"** — lists CRC-15, cross-layer flag validation, invalid rounding state.
- Overview says (TECHNICAL_OVERVIEW.md, Error Detection Rules section): Lists **six rules**: Rule 1 (Direction), Rule 2 (Status), Rule 3 (Rounding state), Rule 4 (CRC-15/Session Integrity), Rule 5 (Batch close count == records received), Rule 6 (Compound integrity / 1111 markers only when enabled).
- File/section: README.md lines 131–135 vs TECHNICAL_OVERVIEW.md lines 356–366
- Severity: **HIGH** — if implementers follow the README's "three mechanisms" description, they may omit Rule 5 (Batch close count validation) and Rule 6 (Compound integrity enforcement). Both are behaviorally significant. Rule 5 in particular is the primary batch-level data integrity check.
- Recommended resolution: Adopt all six rules from TECHNICAL_OVERVIEW.md. The README's "three" is a marketing-level summary. The Technical Overview's six-rule enumeration is the implementation contract.

#### CONFLICT-003: Rounding Balance sign convention phrasing
- Spec says (mathmodel_by_grok.md, rounding balance): `+m` when high bit = 0 (positive surplus, rounded up); `-m` when high bit = 1 (deficit, rounded down).
- Overview says (TECHNICAL_OVERVIEW.md, Rounding Balance section): **"High bit = sign (0=up, 1=down)"** — the word "sign" combined with "0=up" is semantically ambiguous. In standard sign-magnitude convention, 0 means positive (not a direction). The description could be read as "0=positive/surplus/rounded-up" or literally "the sign bit where 0 means the rounding went up".
- File/section: TECHNICAL_OVERVIEW.md lines 110–116 (Rounding Balance subsection)
- Additional note: The table immediately following the description (`0001–0111 = net +1 to +7 units rounded up`, `1001–1111 = net -1 to -7 units rounded down`) is unambiguous and consistent with the mathmodel. The prose description is the source of ambiguity.
- Severity: **LOW** — the table is definitive and unambiguous. The verbal description is imprecise but does not contradict the table. A developer reading the table will implement correctly.
- Recommended resolution: When implementing, use the table definition. Add a clarifying comment in code: "Sign-magnitude: high bit 0 = positive surplus (rounded up), high bit 1 = deficit (rounded down)."

#### CONFLICT-004: Currency table capacity vs seeded count
- Spec says (TECHNICAL_OVERVIEW.md Layer 2): Currency Code field is **6-bit (64 currencies, 0=session default)** — implying the protocol supports up to 63 distinct non-default currency codes.
- Overview says (CLAUDE.md and README.md): `currencies.py` is a **"Seeded 32-currency table"** — the implementation will only seed 32 currencies.
- File/section: TECHNICAL_OVERVIEW.md line 87 vs CLAUDE.md line 29 and README.md line 229
- Severity: **MEDIUM** — the protocol field can hold 64 values; the implementation seeds only 32. This is not a bit-layout conflict (the 6-bit field is correct), but the implementation leaves 32 currency code slots undeclared. Codes 33–63 (1-indexed) are valid protocol codes that the Python tool will not be able to encode/decode to named currencies. Whether this is intentional (reserved for user extension) or a gap is not specified in either document.
- Recommended resolution: Flag for Orchestrator decision: are codes 33–63 reserved for user-defined currencies (requiring runtime extension support), or are they simply unused in v1 of the implementation? The protocol spec (.docx) should define this.

#### CONFLICT-005: Compound continuation bits 37–38 — sub-type vs mirror requirement
- Spec says (TECHNICAL_OVERVIEW.md Layer 3 bit layout, lines 143–146): Bit 37 = "Direction (BL) — Mirror of bit 29" and Bit 38 = "Status (BL) — Mirror of bit 30". The cross-layer validation rules (Rule 1 and Rule 2) require these to equal their counterparts.
- Overview says (TECHNICAL_OVERVIEW.md Compound Transactions section, lines 303–309): In continuation records (account pair = 1111), **bits 37–38 carry sub-type**, not direction/status mirrors. Sub-types: 00=standard linked, 01=correcting, 10=reversal, 11=cross-batch.
- File/section: TECHNICAL_OVERVIEW.md lines 143–146 (Layer 3 layout) vs TECHNICAL_OVERVIEW.md lines 303–309 (Compound section) — this is an **intra-document conflict within the Technical Overview itself**.
- Severity: **HIGH** — this is a direct contradiction within the same document. The Layer 3 field map says bits 37–38 are always mirrors of bits 29–30 and must pass Rule 1 and Rule 2 validation. The Compound section says those same bits carry sub-type semantic when account pair = 1111, which would cause Rule 1 and Rule 2 validation to fail for continuation records. The decoder must know to skip mirror validation for continuation records or the sub-type would be rejected as a Direction/Status mismatch.
- Recommended resolution: This requires human decision before implementation. The resolution must explicitly state: (a) whether mirror validation is skipped for `account_pair == 0b1111`, and (b) whether the sub-type encoding is the authoritative behavior for continuation records. Read `BitLedger_Protocol_v3.docx` directly to resolve. This is the highest-priority finding.

---

### SPEC-ONLY GAPS (in protocol, not in overview)

**GAP-001: Full SF index table — indices 10–127** (Severity: HIGH)
- The Technical Overview shows SF indices 0000000 to 0001001 (10 entries, ×1 to ×1,000,000,000). The 7-bit SF field in Layer 2 supports 128 distinct values. Indices 10–127 (binary 0001010 through 1111111) are not defined in the Technical Overview. Whether these are reserved, user-definable, or protocol-defined is undocumented in the overview. The Control Record Type 000 payload table refers to indices 0–9 as standard and 10–14 as user-defined within a 4-bit control byte — but this does not cover the full 7-bit Layer 2 SF field range.

**GAP-002: Setup wizard question sequence** (Severity: MEDIUM)
- CLAUDE.md lists `setup_wizard.py` as implementing "Interactive Layer 1 + Layer 2 configuration wizard". The README references `bitledger setup` command. The Technical Overview (markdown) does not describe the wizard's question sequence, field prompts, or validation logic. The full Technical Overview docx "includes setup wizard specification" per README line 247. No equivalent content appears in TECHNICAL_OVERVIEW.md.

**GAP-003: Simulation design specification** (Severity: MEDIUM)
- README references `bitledger simulate --profile retail --compound --enquiry`. CLAUDE.md lists `simulator.py`. The Technical Overview markdown does not describe the simulation scenario structure, default transaction sequences, or ACK/NACK exchange patterns. The full Technical Overview docx is referenced as the source for "simulation design" (README line 247).

**GAP-004: Full value range tables** (Severity: LOW)
- TECHNICAL_OVERVIEW.md contains an abbreviated value range table (5 SF rows × 4 D columns). The full spec (BitLedger_Protocol_v3.docx) is described as containing "complete value range tables". The condensed table is present but the remaining 5 SF rows (×10, ×1,000, ×10,000, ×100,000, ×10,000,000) at all four decimal positions are absent from the Technical Overview.

**GAP-005: Decimal Position valid value specification** (Severity: HIGH)
- Both documents show decimal positions 0, 2, 4, 6 as the valid values for the 3-bit field (bits 14–16). The 3-bit field can hold values 0–7. Values 1, 3, 5, 7 (odd values) are not mentioned in the overview — it is unclear whether they are reserved, invalid (raise ProtocolError), or simply not tabulated. Encoding software that accepts raw bit values 000–111 without validation could encode an invalid decimal position silently.

**GAP-006: Extension byte chaining and ordering rule** (Severity: MEDIUM)
- TECHNICAL_OVERVIEW.md lists 7 extension byte use cases (Quantity, Subcategory, Opposing Account, Currency Override, Timestamp Offset, Precision Anchor, Party Type) and states "Chainable — bit 8 of each extension triggers the next." However, no ordering rule is specified: if multiple extensions are present, what determines the sequence? Which extension type comes first? The full spec presumably defines a canonical ordering or type-prefix byte. The overview only states the chaining mechanism, not the ordering or type identification scheme for multi-extension records.

---

### OVERVIEW-ONLY ADDITIONS (implementation detail or undocumented protocol element)

**ADD-001: Python serialise() function implementation** (Severity: LOW)
- The Technical Overview provides a complete Python `serialise(record, S)` function. The full protocol spec presumably describes behavior, not implementation. This is an implementation-level addition that aids developers but is not part of the wire protocol definition.

**ADD-002: Encoder Decision Algorithm with rounding mode tables** (Severity: MEDIUM)
- `ROUND_UP_PAIRS = {0b0001, 0b0011, 0b0101, 0b0111, 0b1000, 0b1100}` and `ROUND_DOWN_PAIRS = {0b0100, 0b0110, 0b1001, 0b1011}` — These sets define per-account-pair rounding behavior. The protocol spec may define these, but they appear only in the Technical Overview. Pairs not in either set (0b0010, 0b1101, 0b1010, 0b1011 for down + 0b1110, 0b1111) fall to 'nearest' mode. If the full spec defines a different table, this could cause rounding correctness issues.
- Note: 0b1011 (Asset/Asset) appears in ROUND_DOWN_PAIRS. This needs verification against the protocol spec as the semantic ("Asset transfer in") should not inherently favor round-down.

**ADD-003: Critical notes about Decimal vs float** (Severity: MEDIUM)
- The Technical Overview states: "NEVER use Python float for monetary values. Always use decimal.Decimal." This is an implementation constraint not present in the wire protocol. However, it is critical for correctness of the Python implementation.

**ADD-004: Python data model field defaults** (Severity: LOW)
- `Layer1Config.protocol_version = 1` default, `Layer2Config.transmission_type = 1`, `Layer2Config.optimal_split = 8`, etc. These are implementation choices embedded in the dataclasses. If the protocol spec defines different defaults (e.g., protocol_version should default to the latest version, not 1), this would be a conflict. Unverifiable without reading the .docx.

**ADD-005: Transmission Efficiency calculations** (Severity: LOW)
- The overview includes quantitative efficiency tables (509 bytes for 100 records, 5,068 bytes for 1,000 records). These are implementation-level claims. If the full spec has different efficiency figures, this would be a discrepancy, but these are derived values, not specification constraints.

**ADD-006: Journal entry output format template** (Severity: LOW)
- The Python `formatter.py` output template is specified only in the Technical Overview. The protocol spec presumably does not mandate a specific ASCII art display format. This is overview-only.

**ADD-007: `decode_control` / `encode_control` function implementations** (Severity: LOW)
- Control record encoding/decoding functions appear only in the Technical Overview. The protocol spec defines behavior; the functions are implementation artifacts.

**ADD-008: `to_bit_string()` and `to_hex()` helper functions** (Severity: LOW)
- These output formatting functions are overview-only implementation details.

**ADD-009: Compound continuation sub-types table** (Severity: HIGH)
- The four sub-types for bits 37–38 of continuation records (00=standard, 01=correcting, 10=reversal, 11=cross-batch) appear in the Technical Overview's Compound Transactions section. This table is not visible in the README or other protocol references. Whether this appears in the full protocol spec or was defined only in the Technical Overview is unverifiable without the .docx. Given its HIGH impact (affects how compound entries are classified), this must be verified against the protocol spec before implementation.

---

## Recommendations for Orchestrator

1. **HIGHEST PRIORITY — Resolve CONFLICT-005 before any encoder/decoder work begins.** The intra-document contradiction about bits 37–38 in continuation records (mirror bits vs sub-type encoding) makes it impossible to implement a correct decoder without knowing whether Rule 1/Rule 2 validation is suspended for `account_pair == 0b1111`. Read `BitLedger_Protocol_v3.docx` directly and issue a definitive resolution. This single ambiguity affects the decoder, encoder, compound transaction logic, and the data model (TransactionRecord.continuation_subtype field).

2. **HIGH PRIORITY — Verify the six error detection rules are the complete implementation contract.** README describes "three mechanisms" which conflicts with the Technical Overview's six-rule enumeration. Task cards for decoder.py must explicitly enumerate all six rules as acceptance criteria (Gate A requirement).

3. **HIGH PRIORITY — Verify odd Decimal Position values (1, 3, 5, 7) are invalid protocol states.** If the decoder must raise ProtocolError on these, tests must be written for all four. If they are simply undefined/reserved, the behavior (silent ignore vs error) must be specified before decoder implementation.

4. **MEDIUM PRIORITY — Obtain a human decision on currency codes 33–63.** The 6-bit field supports 64 codes but only 32 are seeded. The task card for currencies.py must specify whether codes 33–63 should raise an EncoderError, be allowed as opaque user-defined codes, or be blocked as reserved.

5. **MEDIUM PRIORITY — Read `BitLedger_Protocol_v3.docx` directly (using the Python XML extraction method) to resolve the four unverifiable items.** This audit could not access the binary .docx files. The five conflicts and six gaps identified above are based on the markdown equivalents. A second Explorer pass against the actual binary spec may reveal additional conflicts or confirm alignments.
