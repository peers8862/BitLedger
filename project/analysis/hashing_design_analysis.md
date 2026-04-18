# BitLedger — Hashing & Unique Record ID: Design Analysis

**Status:** Planning — no implementation yet. All decisions marked with ★ need owner input.

---

## 1. What problem are we solving?

Hashing for record identity covers several distinct use cases that can be built
independently or together:

| Goal | Description | Urgency |
|------|-------------|---------|
| **A. Record deduplication** | Detect if you're about to encode a transaction you've already encoded | High |
| **B. Decode replay detection** | Detect if you've decoded this exact wire record before | High |
| **C. Audit log integrity** | Prove a log of records hasn't been tampered with, reordered, or had entries dropped | Medium |
| **D. Stable record reference** | Assign a durable ID so a record can be referenced by other systems (reconciliation, linking) | Medium |
| **E. File-level integrity** | Verify a `.bl` file hasn't been corrupted or modified since creation | Low |

These are not the same problem and don't require the same mechanism. The design
below covers all five, clearly separated.

---

## 2. What BitLedger has now

### Existing integrity mechanisms

| Mechanism | Layer | Coverage | Limitation |
|-----------|-------|----------|------------|
| CRC-15 | Layer 1 | Detects bit errors in the 8-byte session header | Wire corruption only; not per-record; not cryptographic |
| Mirror rules (Rules 1–2) | Layer 3 | Direction and status bits must match at two positions | Structural constraint, not an identity |
| Invalid rounding gate (Rule 3) | Layer 3 | bits 26=0,27=1 is a protocol violation | Value consistency check, not an identity |

### No hash or fingerprint exists

Zero mentions of hash, fingerprint, or record ID anywhere in the protocol spec
(README.md) or implementation. The decoder produces no record identifier.

### Wire budget: what bits are free?

**Layer 3 (40-bit record) — fully allocated:**
```
Bits 1–25   Value block (N = A split at S bits with r)
Bits 26–27  Rounding flag + direction
Bits 28–32  split_order, direction, status, debit_credit, quantity_present
Bits 33–36  account_pair (4-bit type code)
Bits 37–38  direction mirror, status mirror (Rules 1–2)
Bits 39–40  completeness, extension_flag
```
**No free bits in the 40-bit L3 record.** Any hash reference requires either
a protocol version change or an external mechanism.

**Extension pathway (already in the model):**
`extension_flag` (bit 40) and `extensions: list[int]` exist in `TransactionRecord`
but are not yet formally defined. This is the intended future expansion point
for attaching additional data after the 40-bit core.

**Layer 2 — one reserved bit:**
Bit 48 (`reserved=1`) is always 1, not available.

**Layer 1 — `sender_id` (32 bits) and `sub_entity_id` (5 bits):**
These are identity fields, not free bits. They can be used as part of a
composite record ID without any protocol change (see Option C below).

---

## 3. What gets hashed? (The canonical form question)

This is the most consequential design decision. Four candidates:

### 3a. Full wire bytes — `hash(L1 + L2 + L3)`
Hash the complete raw bytes of the blob as written to disk.

```
record_id = hash(l1_bytes + l2_bytes + n40_bytes)
```

- **Pro:** Exact byte-level integrity; `sha256sum` on the file gives the same result.
- **Pro:** Simplest to compute — no parsing needed.
- **Con:** Same transaction encoded twice with a different sender_id produces
  a different hash. That's usually the right behavior, but not always.
- **Con:** Short-form L2 (0x6F) and full L2 with matching defaults produce
  *different* hashes for the same logical record (unless you normalize first).
- **Use for:** File integrity, exact duplicate detection, audit log.

### 3b. L3 only — `hash(n40_bytes)`
Hash just the 5-byte transaction record.

```
record_id = hash(n40.to_bytes(5, 'big'))
```

- **Pro:** Session-independent — same transaction amount/type always hashes the same.
- **Pro:** Simplest input surface.
- **Con:** Two identical transactions from different senders or sessions are
  indistinguishable — false duplicate detection.
- **Con:** Does not cover the scaling context (SF, dp) stored in L2, so the same
  n40 with different L2 settings means different real values, but same hash.
- **Use for:** Content-addressable dedup *within* a known session/batch.

### 3c. Canonical semantic form — `hash(canonical_fields)`
Normalize to a deterministic byte string of the meaningful fields before hashing:
amount, account_pair, direction, status, currency, sender_id, etc.

```python
canonical = (
    amount.as_canonical_bytes()  # Decimal → fixed-point bytes
    + account_pair.to_bytes(1, 'big')
    + direction.to_bytes(1, 'big')
    + status.to_bytes(1, 'big')
    + currency_code.to_bytes(1, 'big')
    + sender_id.to_bytes(4, 'big')
)
record_id = hash(canonical)
```

- **Pro:** Hash is stable across re-encodings (different SF choices, short vs. full L2).
- **Pro:** Truly represents "the same transaction" regardless of wire representation.
- **Con:** Requires a defined canonical form — a spec decision.
- **Con:** More code; the canonical form must be maintained as fields evolve.
- **Use for:** Reconciliation, stable external references, dedup across re-encodes.

### 3d. L1 composite identity (no hash at all)
Use `sender_id (32-bit) + record_sep (5-bit sequential index from L2)` as a
composite record identifier. Already in the wire format; zero new code needed.

```
record_id = f"{sender_id:08x}:{batch_group:02d}:{record_sep:03d}"
# e.g. "deadbeef:00:007"
```

- **Pro:** Zero implementation cost; purely semantic.
- **Con:** `record_sep` is 5 bits (values 1–31 per batch) — wraps every 31 records.
- **Con:** Requires `sender_id` to be set (default is 0x00000000 in current profiles).
- **Con:** Not a hash — can't detect tampering or corruption.
- **Use for:** Human-readable record reference within a session. Insufficient alone
  for dedup or integrity.

---

## 4. Hash algorithm options (stdlib only — zero external deps)

BitLedger currently has **zero runtime dependencies**. This constraint must be
weighed explicitly. All options below are `hashlib` (stdlib since Python 3.3).

| Algorithm | Output | Speed | Security | Notes |
|-----------|--------|-------|----------|-------|
| `blake2b(digest_size=8)` | 8 bytes / 16 hex chars | Fastest | 64-bit collision space | Best fit for personal use short IDs |
| `blake2b(digest_size=16)` | 16 bytes / 32 hex chars | Fastest | 128-bit | Recommended for record IDs |
| `blake2b(digest_size=32)` | 32 bytes / 64 hex chars | Fast | 256-bit | Full-strength, heavier in logs |
| `blake2s(digest_size=16)` | 16 bytes / 32 hex chars | Fast (32-bit opt) | 128-bit | Smaller platform variant |
| `sha256` | 32 bytes / 64 hex chars | Moderate | 256-bit | Universal; OS tools understand it |
| `sha3_256` | 32 bytes / 64 hex chars | Slower | 256-bit | NIST standard; no speed advantage here |
| CRC-32 (via `zlib`) | 4 bytes | Instant | None (not a hash) | Collision-prone; only for error detection, not identity |

**BLAKE2b is the recommendation**: it is the fastest stdlib option, supports
variable digest length (pick 8, 16, or 32 bytes based on needs), is used in
production cryptographic systems, and requires no external dependencies.

For personal use with a bounded number of records:
- `digest_size=8` → 64-bit; collides with ~50% probability after ~2³² (~4 billion) records. Fine.
- `digest_size=16` → 128-bit; effectively collision-free for any personal use case.

**HMAC (keyed hashing):** `hmac.new(key, data, hashlib.blake2b)` from stdlib.
Adds authentication — only someone with the key can forge a valid hash.
Needed if records ever cross trust boundaries. Overkill for single-user personal use,
but the infrastructure is stdlib and trivial to add later.

---

## 5. Where does the hash live?

Six placement options, from zero protocol impact to full wire integration:

### Option A: External JSONL hash log
A newline-delimited JSON log alongside encoded records. No wire format changes.

```jsonl
{"id":"a3f8b291c4d7e520","blob":"tx.bl","amount":"149.99","ts":"2026-04-18T14:32:00Z","prev":null}
{"id":"c91d3f4a8b27e016","blob":"tx2.bl","amount":"59.76","ts":"2026-04-18T14:33:12Z","prev":"a3f8b291c4d7e520"}
```

- Stored at `~/.config/bitledger/hash_log.jsonl` (configurable)
- Appended on encode; checked on decode
- **Chain integrity**: each entry includes `prev` = ID of previous entry
- **Pro:** Zero protocol impact; backward compatible; trivial to implement
- **Pro:** Searchable, human-readable, portable
- **Con:** Log is separate from the record blob; can be lost or bypassed
- **Verdict: Recommended as Phase 1**

### Option B: Sidecar file (`.bl.sha256`)
Each `.bl` file gets a companion hash file written alongside it.

```
tx.bl         ← binary record blob
tx.bl.sha256  ← "a3f8b291c4d7e520  tx.bl\n" (sha256sum format)
```

- Compatible with OS tools: `sha256sum -c tx.bl.sha256`
- **Pro:** Familiar format; OS-level verification; works without the CLI
- **Con:** Sidecar can be lost independently of the blob
- **Con:** Only covers file integrity, not semantic dedup across re-encodings
- **Verdict: Good supplement to Option A; low cost to add**

### Option C: Composite sequential ID (no implementation)
Use existing wire fields as a record reference:
`sender_id:group_sep:record_sep` already in L1/L2.

- **Verdict:** Useful as a human-readable reference; insufficient alone for
  dedup or integrity; recommend adding as a formatted field in journal output.

### Option D: Log file with chain integrity (Phase 2)
Extend Option A with cryptographic chaining: each entry's hash incorporates
the previous entry's hash. Tampering with any record invalidates all subsequent
entries.

```
H₁ = blake2b(record₁_bytes)
H₂ = blake2b(H₁ || record₂_bytes)
H₃ = blake2b(H₂ || record₃_bytes)
```

- **Pro:** Detects insertion, deletion, and reordering — full tamper-evidence
- **Con:** Chain must be repaired manually if a record is legitimately deleted
- **Verdict: Phase 2 addition after Phase 1 log is working**

### Option E: Extension bytes in wire format (Phase 3)
Use the existing `extension_flag` (bit 40) + `extensions: list[int]` field.
Define extension type 0x01 as a "record hash" block appended after the L3 record.

```
[L1: 8 bytes] [L2: 1-6 bytes] [L3: 5 bytes] [Ext type: 1 byte] [Hash: 8-32 bytes]
```

- Extension_flag=1 in L3 signals that additional bytes follow
- First extension byte = type (0x01 = hash, others TBD)
- Next N bytes = hash value (length determined by type)
- **Pro:** Hash is inseparable from the record; no external log needed
- **Con:** Requires formal extension byte spec — currently undefined
- **Con:** Breaking change for decoders that don't handle extensions
- **Con:** Increases per-record size: 14 bytes → 14 + 1 + 8 = 23 bytes minimum
- **Verdict: Phase 3 — depends on formalizing extension_flag semantics**

### Option F: Control record hash frame (existing mechanism)
After encoding a batch, emit a 1-byte control record to close the batch,
then a multi-byte "hash stream" using consecutive control records.

- The existing control record is 8 bits; a hash would require 8–32 bytes
  → 8-32 control records just for one hash
- Awkward and wasteful; control records are designed for 4-bit payloads
- **Verdict: Not recommended for hash transport**

---

## 6. Deduplication: scope and behavior

### Scope options

| Scope | Storage | Persistence | Coverage |
|-------|---------|-------------|----------|
| Session-only | In-memory `set` | Lost on restart | Current process only |
| File-level | Sidecar `.sha256` | Persists with .bl | One file per record |
| Global log | JSONL or SQLite | Persistent | All encoded records |

For personal use, **global log** is most useful — you want to know if you've
encoded this transaction before, regardless of when.

### Behavior on duplicate

★ **Decision needed:** When a duplicate is detected, should the tool:
1. **Warn** (print to stderr, continue encoding) — "WARN: this record matches hash abc123 logged 2026-04-18"
2. **Hard reject** (exit 2, refuse to write .bl) — treat duplicate as a protocol error
3. **Prompt** (ask the user to confirm) — useful for interactive use, not scriptable

Recommendation: **warn by default; add `--reject-duplicate` flag for strict mode.**
This mirrors the rounding gate pattern already in the CLI.

### What constitutes a duplicate?

This depends on the canonical form chosen (§3):
- **Wire bytes hash**: only exact byte-level copies are duplicates. Re-encoding the
  same transaction with a different sender_id or profile = not a duplicate.
- **Semantic hash**: same amount + account_pair + direction + currency = duplicate
  even if encoded with different wire parameters.

★ **Decision needed:** Which definition of "same record" matches your use case?

---

## 7. CLI surface

### On existing commands (minimal surface)

```bash
# Encode: compute and log hash of the produced blob
bitledger encode --amount 149.99 --auto-sf --out tx.bl --hash-log

# Encode: reject if this wire record was logged before
bitledger encode --amount 149.99 --auto-sf --out tx.bl --hash-log --reject-duplicate

# Decode: check hash on decode, log if not seen before
bitledger decode --in tx.bl --hash-log

# Decode: emit the record's hash to stdout (for scripting)
bitledger decode --in tx.bl --print-hash
```

`--hash-log` without a path uses the default (`~/.config/bitledger/hash_log.jsonl`).
`--hash-log PATH` uses a specific log file.

### New `log` subcommand family (full surface)

```bash
bitledger log list                       # Print all logged hashes with metadata
bitledger log list --since 2026-04-01   # Filter by date
bitledger log find --hash a3f8b291      # Locate a record by (partial) hash
bitledger log verify                     # Verify chain integrity of the log
bitledger log verify --full              # Verify + recompute all hashes from blobs
bitledger log export --format csv        # Export log as CSV for external tools
bitledger log prune --before 2026-01-01 # Remove old entries (breaks chain — warns)
```

### Config toggle

In `~/.config/bitledger/config.json`:
```json
{
  "warn_short_form_mismatch": true,
  "hash_log_enabled": false,
  "hash_log_path": "~/.config/bitledger/hash_log.jsonl",
  "hash_algorithm": "blake2b-16",
  "hash_log_chain": false,
  "duplicate_action": "warn"
}
```

`hash_log_enabled: false` by default — opt-in feature, not on unless you ask for it.

---

## 8. Protocol impact assessment

| Option | Wire change | Protocol version | Backward compat |
|--------|-------------|-----------------|-----------------|
| A (external log) | None | 1.x.x — no change | Full |
| B (sidecar) | None | 1.x.x | Full |
| C (composite ID from existing fields) | None | 1.x.x | Full |
| D (chain log) | None | 1.x.x | Full |
| E (extension bytes) | YES — extension_flag meaning defined | 2.0.0 — major | Breaking for old decoders |
| F (control record hash) | Minor (new control type) | 1.x.x if additive | Requires decoder awareness |

**Phase 1–2 (external log + chain): no protocol changes, version stays 1.x.x**
**Phase 3 (extension bytes): requires protocol version bump to 2.0.0**

---

## 9. Implementation complexity

### Phase 1: External log (minimal) — low complexity

New files:
- `bitledger/hasher.py` — `compute_record_id(blob: bytes, algorithm: str) -> str`
- `bitledger/hash_log.py` — `append_log(path, entry)`, `check_log(path, record_id) -> LogEntry | None`

Changes to existing files:
- `bitledger/config.py` — add 4 new config fields
- `bitledger/cli.py` — add `--hash-log` / `--print-hash` flags to encode + decode

New CLI surface:
- `bitledger/cli_log.py` — `cmd_log_list`, `cmd_log_find`, `cmd_log_verify`

Tests:
- `tests/test_hasher.py` — hash stability, algorithm variants
- `tests/test_hash_log.py` — append, lookup, duplicate detection

No changes to encoder.py, decoder.py, models.py (not HIGH FRAGILITY).

### Phase 2: Chain integrity — low-medium complexity

Extend `hash_log.py` to include `prev` field in each entry and verify chain
in `log verify`. ~50 lines additional code.

### Phase 3: Extension bytes on wire — high complexity

Requires:
1. Formal extension byte type registry in the protocol spec
2. `encoder.py` changes to emit extension bytes (HIGH FRAGILITY)
3. `decoder.py` changes to parse extension bytes (HIGH FRAGILITY)
4. `models.py` changes to carry hash in `TransactionRecord.extensions`
5. Full roundtrip tests for extended records
6. Protocol version bump to 2.0.0 in pyproject.toml and README.md

---

## 10. Recommended phased plan

### Phase 1 (1.1.0 — MINOR bump) — External log, no protocol change
Build `hasher.py` + `hash_log.py`, add `--hash-log` to encode/decode,
add `bitledger log` subcommand. Wire form unchanged.

### Phase 2 (1.2.0 — MINOR bump) — Chain integrity
Add `prev` chain field to log entries. Add `log verify` chain walk. Broken
chain emits `DecoderWarning` with position of first invalid entry.

### Phase 3 (2.0.0 — MAJOR bump) — Wire-embedded hash
Formalize extension_flag semantics. Define extension type 0x01 as record hash.
Update encoder, decoder, models. Full protocol version change.

---

## 11. Open decisions (★ need owner input before implementation)

| # | Question | Options | Default recommendation |
|---|----------|---------|----------------------|
| 1 | **Primary goal** | Dedup only / audit log / tamper detection / all | Start with dedup + log |
| 2 | **Canonical form** | Wire bytes / L3 only / semantic fields | Wire bytes (simplest to start) |
| 3 | **Hash algorithm** | blake2b-8 / blake2b-16 / sha256 | `blake2b(digest_size=16)` |
| 4 | **Chain hashing** | Phase 1 or Phase 2 | Phase 2 — start without |
| 5 | **Duplicate behavior** | Warn / hard reject / prompt | Warn by default; `--reject-duplicate` flag for strict |
| 6 | **Wire hash (Phase 3)** | Yes (extension bytes) / No (external only) | Defer to v2.0.0 |
| 7 | **HMAC / keyed hash** | No key / optional key from master config | No key for v1; add `hash_key` config in Phase 2 |
| 8 | **Log storage** | JSONL / SQLite / sidecar .sha256 | JSONL (zero deps) + optional sidecar |
| 9 | **Log location** | `~/.config/bitledger/` / project-local / configurable | Configurable, default `~/.config/bitledger/` |
| 10 | **Composite ID in journal** | Show sender_id:group:record_sep in all output | Yes — add to formatter.py |

---

## 12. Comparison: what similar tools do

| Tool | Approach | Relevant to BitLedger |
|------|----------|----------------------|
| Git | SHA-1/SHA-256 content-addressed objects; each commit hashes its content + parent | Chain hash model (Option D) |
| Bitcoin | SHA-256d on transaction bytes; TXID is the hash; chain via prev_hash in blocks | Wire-embedded hash (Phase 3) |
| SQLite WAL | Page checksums (CRC-32) for corruption detection | Not identity; wire integrity only |
| GNU coreutils `sha256sum` | Hash of file bytes, stored in `.sha256` | Sidecar model (Option B) |
| IPFS | BLAKE2b content-addressed IDs | Canonical form hash (Option A/3c) |
| systemd journal | HMAC-based sealing for tamper detection | Chain + keyed hash |

The closest analogy is **Git's object model**: content-addressed blobs where the
ID *is* the hash of the content. BitLedger records could follow the same pattern —
every `.bl` file is referenced by `blake2b(content)[:16]`, making it a
content-addressed store of financial records.

---

## 13. Reference

- `bitledger/encoder.py` — `serialise()`, `encode_layer1_bytes()`, `encode_layer2_bytes()`
- `bitledger/decoder.py` — `unpack_record()`, `decode_value()`
- `bitledger/models.py` — `TransactionRecord.extension_flag`, `TransactionRecord.extensions`
- `bitledger/config.py` — `MasterConfig` (where new hash config fields will go)
- `bitledger/errors.py` — `DecoderWarning` (pattern for hash mismatch warnings)
- `README.md` — Protocol spec §Layer 3, §extension_flag
- `DEVGUIDE.md` — Version bump decision table (Phase 1 = 1.1.0, Phase 3 = 2.0.0)
