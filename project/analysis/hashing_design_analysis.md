# BitLedger — Hashing & Unique Record ID: Design Analysis

**Status:** Planning — no implementation yet. Decisions marked ★ need owner input before implementation.
**Revised:** 2026-04-18 — updated after design review session.

---

## 1. Two separate mechanisms, not one

The hashing question has two distinct parts that should be designed independently:

**Part A — Local log (on machines, not in transmission)**
Both sender and receiver independently compute a hash from their local copy of the
bytes. The hash is stored in a local audit log. Nothing new travels on the wire.
This is Phase 1 and 2. No protocol change.

**Part B — Wire-embedded hash (travels with the record)**
The hash is appended after the 5-byte L3 record, signaled by `extension_flag=1`
(bit 40), and parsed by the receiver as part of the blob. This IS part of the
transmission. This is Phase 3. Requires formalizing the extension byte format.

These should be thought through and potentially implemented separately.
Part A has no protocol impact. Part B requires an extension type registry.

---

## 2. What full audit actually entails

A complete financial audit trail must answer six questions:

| Question | Data needed | In BitLedger wire? |
|----------|-------------|-------------------|
| **What** was transacted | amount, account_pair, direction, currency | ✓ L3 + L2 |
| **Who** created it | sender identity | Partial — `sender_id` (32-bit) in L1, but defaults to 0x00000000 |
| **When** it was created | timestamp | ✗ **Not in the protocol at all** |
| **In what sequence** | ordering | Partial — `record_sep` (5-bit, wraps at 31), unreliable across sessions |
| **Has it been modified** | content hash | ✗ Not implemented |
| **Is anything missing** | chain integrity | ✗ Not implemented |

### The timestamp gap

There is no time field anywhere in BitLedger — not in L1, L2, or L3. This means:
- A wire record carries no evidence of when it was created
- Audit timestamps must be added by the local tool at encode/decode time (machine clock)
- If a `.bl` file is decoded later from backup, the log captures the decode time,
  not the original encode time — these may differ significantly
- For wire-embedded timestamps, a timestamp extension type would be needed alongside
  the hash extension (see §6)

### The sender identity gap

`sender_id` (32-bit in L1) defaults to `0x00000000` in the default profile. With
a default profile, every record appears to come from the same zero sender, making
attribution useless. A real audit trail requires sender_id to be set to something
meaningful at `bitledger setup` time.

### The sequence gap

`record_sep` (5-bit, values 1–31) is a per-batch sequential index that wraps every
31 records. `group_sep` (4-bit) and `file_sep` (3-bit) both default to 0. These
fields cannot reliably identify the position of a record across sessions or long batches.

### A complete audit log entry

```json
{
  "id": "a3f8b291c4d7e520c1d3f4b2",
  "prev": "00000000000000000000000000000000",
  "session_id": "deadbeef01000000",
  "timestamp": "2026-04-18T14:32:01.423Z",
  "wire_bytes": "9c000000000020956f001d4b8040",
  "amount": "149.99",
  "account_pair": 4,
  "direction": 0,
  "status": 0,
  "currency": 0,
  "valid": true,
  "warnings": []
}
```

`id` is chained: `blake2b(prev_id_bytes || wire_bytes || timestamp_bytes, digest_size=16)`
`session_id` is derived from the Layer 1 header bytes (see §4)
`prev` = `id` of the previous log entry; first entry uses a zero-filled sentinel

Walking the chain from first to last and recomputing each `id` from its inputs
verifies that no entry was inserted, deleted, or reordered.

---

## 3. Why would duplicates occur?

In BitLedger's personal-use context, duplicates arise from user error, not
adversarial attack. Concrete scenarios:

| Scenario | How it happens | Realistic? |
|----------|---------------|-----------|
| **Manual re-run** | Encode a transaction, file gets lost, encode it again | Very common |
| **Retry on perceived failure** | Send `.bl`, no receipt confirmation, send again — receiver got both | Common in any networked use |
| **Backup re-processing** | Restore `.bl` files from backup, decode everything to rebuild log | Likely over time |
| **Scripting loop error** | `for amount in ...; do bitledger encode ...` runs twice | Scripting use |
| **Test-to-production bleed** | Test records encoded with same profile as production | As usage grows |
| **Session reconnect** | Transmission drops mid-batch; sender restarts from last confirmed — receiver buffered ahead | Multi-party only |

Deduplication for personal use is primarily **user error protection**, not
adversarial replay defense. This argues for **warn by default, not hard reject** —
mirroring the rounding gate pattern already in the CLI.

---

## 4. What is reliable for hash construction?

The user asked whether `sender_id`, session context, and separators could inform
hash construction. The short answer: most separator fields are unreliable in
default profiles; a session nonce is the cleanest solution.

### Separator field reliability audit

| Field | Size | Default | Reliable as ID? | Why |
|-------|------|---------|-----------------|-----|
| `sender_id` | 32-bit (L1) | `0x00000000` | Only if configured | Must be set at setup; zero in default profile |
| `sub_entity_id` | 5-bit (L1) | 0 | No | Usually 0 |
| `record_sep` | 5-bit (L2) | 0 | No | Per-batch sequential, wraps at 31, often 0 |
| `group_sep` | 4-bit (L2) | 0 | No | Signal field, not identity |
| `file_sep` | 3-bit (L2) | 0 | No | Signal field, not identity |
| `entity_id` | 5-bit (L2) | 0 | No | Usually 0 |
| n40 content | 40-bit (L3) | varies | ✓ Always | Carries actual transaction data |
| Machine timestamp | — (from tool) | — | ✓ Added by tool | Not in protocol; added at log time |

### The session nonce approach

When a session starts (or `bitledger setup` runs), generate a random 16-byte nonce
stored locally in the profile or a session-state file. **Never transmitted on wire.**
This is a local session anchor for hash construction.

```
record_id = blake2b(session_nonce || n40_bytes || unix_timestamp_bytes, digest_size=16)
```

Properties:
- **Session-scoped**: different sessions → different nonces → different IDs even for
  identical transactions
- **Content-sensitive**: different n40 → different ID
- **Time-sensitive**: same transaction encoded twice in the same session → different
  timestamps → different IDs (protects against rapid duplicate encode)
- **No dependency on unreliable fields**: doesn't require sender_id ≠ 0 or separators
  to be set

When `sender_id` IS set, also derive a session fingerprint from the Layer 1 bytes:
```
session_id = blake2b(L1_bytes, digest_size=8).hexdigest()
```
This connects the log to the actual wire identity when sender attribution is
configured. Both session_nonce and session_id can be stored in the log entry.

### ★ Decision needed: nonce storage location
- In the profile JSON (persists across invocations, same nonce for same profile)
- In a separate session-state file (new nonce each `setup` run)
- Generated fresh per-invocation (safest for dedup; any re-run = different ID)

---

## 5. Wire bytes vs L3 vs semantic — resolved

Three candidates, two use cases. The answer is to use different hash inputs
for different purposes:

### Candidate A: Full wire blob — `hash(L1 + L2 + L3_bytes)`
Best for **file-level integrity** and **exact replay detection**.

```python
record_id = blake2b(blob_bytes, digest_size=16).hexdigest()
```

- Works cleanly when hashing a complete `.bl` file (includes all layers)
- Same logical transaction in a different session (different sender_id, different L1) →
  different hash — correct for replay detection
- Short-form 0x6F and full L2 with matching defaults → different hashes for same
  logical record (a known edge case; can be normalized if needed)
- **Problem in multi-record sessions**: L1 and L2 are sent once, not per record.
  Individual L3 records don't carry their own L1/L2. Hashing individual records
  requires constructing the context.

### Candidate B: L3 only — `hash(n40_bytes)`
Only safe within a known, fixed L2 context. **Not recommended as a general ID.**

The same n40 value means different amounts under different L2 settings
(optimal_split S, scaling_factor_index, decimal_position). Two records with
identical n40 but different L2 session parameters carry different values.
Without L2 context, L3-only hashing is semantically misleading.

### Candidate C: Semantic fields — `hash(amount + account_pair + direction + currency)`
Best for **duplicate transaction detection across re-encodings**.

```python
canonical = (
    str(decoded_amount).encode()     # Decimal as canonical string
    + account_pair.to_bytes(1, 'big')
    + direction.to_bytes(1, 'big')
    + status.to_bytes(1, 'big')
    + currency_code.to_bytes(1, 'big')
    + sender_id.to_bytes(4, 'big')
)
semantic_id = blake2b(canonical, digest_size=16).hexdigest()
```

- Stable across re-encodings (different SF choices, different L2 profiles)
- Requires decoding first (needs L2 context to get `decoded_amount`)
- "Same transaction" regardless of wire representation — most useful for dedup

### Recommendation: store both in the log

```json
{
  "wire_id":     "a3f8b291...",   ← hash(wire_bytes): for replay detection
  "semantic_id": "c7d9f401...",   ← hash(decoded fields): for duplicate transaction detection
  ...
}
```

These answer different questions and both are cheap to compute. A duplicate check
on encode uses `semantic_id` (same transaction?). A replay check on decode uses
`wire_id` (same wire bytes?).

---

## 6. Part B — Wire-embedded hash via extension bytes

The `extension_flag` (bit 40 of L3) and `extensions: list[int]` field already
exist in the model. The extension byte format needs to be defined to make the
receiver "aware" a hash is being sent.

### Proposed extension byte format

```
After the 5-byte L3, when extension_flag = 1:

Byte 0:  Extension type code
           0x00 = reserved
           0x01 = record hash
           0x02 = unix timestamp (4 bytes = seconds, or 8 bytes = milliseconds)
           0x03 = hash + timestamp compound
           0x04–0xFF = reserved for future types
Byte 1:  Payload length N (bytes to follow)
Bytes 2..N+1: Payload
```

For a hash extension:
```
0x01 0x10 <16 bytes BLAKE2b-128 hash>   = 18 extension bytes
```

For a timestamp extension:
```
0x02 0x08 <8 bytes unix milliseconds>   = 10 extension bytes
```

For both compound:
```
0x03 0x18 <16 bytes hash> <8 bytes timestamp>   = 26 extension bytes
```

### What the hash covers

The hash in the extension covers `hash(L1_bytes + L2_bytes + L3_bytes_without_extension)`.
The hash cannot cover itself (circular). The receiver recomputes:
```
expected = blake2b(l1_bytes + l2_bytes + l3_core_bytes, digest_size=16)
```
and compares with the received extension payload. A mismatch is a `DecoderWarning`
or `DecoderError` depending on severity configuration.

In multi-record sessions (L1 and L2 sent once, then many L3 records), each L3
record's extension hash covers `hash(session_fingerprint + l3_bytes_without_extension)`
where `session_fingerprint = blake2b(L1_bytes + L2_bytes, digest_size=8)` is
computed once and reused.

### Record size impact

| Configuration | Bytes per record |
|---------------|-----------------|
| L1 + L2-short + L3 (current) | 14 bytes |
| + hash extension only | 14 + 2 + 16 = 32 bytes |
| + timestamp extension only | 14 + 2 + 8 = 24 bytes |
| + hash + timestamp (compound) | 14 + 2 + 24 = 40 bytes |
| L1 + L2-full + L3 + hash+ts | 8 + 6 + 5 + 26 = 45 bytes |

The extension roughly doubles record size for the hash+timestamp case. This
may conflict with the protocol's low-bandwidth design goal. ★ Decision needed.

### Protocol version impact
Defining extension types is a MINOR protocol addition if done additively —
decoders that don't handle extensions can still parse the 40-bit L3 core.
However, it requires `extension_flag` semantics to be formally specified in
`README.md` (currently undefined). Treat as **1.x.0** if non-breaking, or
**2.0.0** if any decoder behavior must change.

---

## 7. Algorithm — confirmed recommendation

| Algorithm | Output | Speed | Notes |
|-----------|--------|-------|-------|
| `blake2b(digest_size=8)` | 8B / 16 hex | Fastest | 64-bit; fine for < ~2³² records |
| `blake2b(digest_size=16)` | 16B / 32 hex | Fastest | **Recommended** — 128-bit, zero deps |
| `blake2b(digest_size=32)` | 32B / 64 hex | Fast | Full SHA-256 equivalent strength |
| `sha256` | 32B / 64 hex | Moderate | OS-tool compatible (sha256sum) |

All are `hashlib` (stdlib). No external dependencies required.

**Recommendation: `blake2b(digest_size=16)` for IDs in log entries and extension bytes.**
`sha256` as an optional alternative for sidecar files (OS tool compatibility).

HMAC (keyed hash via `hmac` stdlib module) would add authentication — only someone
with the key can forge a valid hash. Not needed for personal use; straightforward
to add later as a `hash_key` master config field.

---

## 8. CLI surface

### Minimal flags on existing commands

```bash
# Encode: compute and log hash; check for duplicate
bitledger encode --amount 149.99 --auto-sf --out tx.bl --hash-log

# Encode: reject if duplicate detected (strict mode)
bitledger encode --amount 149.99 --auto-sf --out tx.bl --hash-log --reject-duplicate

# Decode: check hash log on decode; log if new
bitledger decode --in tx.bl --hash-log

# Decode: emit the record's hash IDs for scripting
bitledger decode --in tx.bl --print-hash

# Encode with wire-embedded hash (Phase 3, extension bytes)
bitledger encode --amount 149.99 --auto-sf --out tx.bl --embed-hash
```

`--hash-log` without a path uses `~/.config/bitledger/hash_log.jsonl` from master config.

### New `log` subcommand family

```bash
bitledger log list                        # All log entries with metadata
bitledger log list --since 2026-04-01    # Filter by date
bitledger log find --hash a3f8b291       # Locate by partial hash
bitledger log verify                      # Walk and verify chain integrity
bitledger log verify --full               # Verify + recompute all hashes from blobs
bitledger log export --format csv         # Export for external tools
```

### Master config additions

```json
{
  "warn_short_form_mismatch": true,
  "hash_log_enabled": false,
  "hash_log_path": "~/.config/bitledger/hash_log.jsonl",
  "hash_algorithm": "blake2b-16",
  "hash_log_chain": false,
  "duplicate_action": "warn",
  "embed_hash_in_wire": false
}
```

`hash_log_enabled: false` — opt-in. Not active unless you pass `--hash-log` or
enable in config. Consistent with the principle that output is controlled explicitly.

---

## 9. Implementation plan (phased)

### Phase 1 — Local log, no protocol change (→ v1.1.0 MINOR)

New files:
- `bitledger/hasher.py` — `compute_wire_id()`, `compute_semantic_id()`, `compute_session_id()`
- `bitledger/hash_log.py` — `append_log()`, `check_log()`, `verify_chain()`

Changes to existing files (LOW fragility):
- `bitledger/config.py` — 5 new master config fields
- `bitledger/cli.py` — `--hash-log`, `--print-hash`, `--reject-duplicate` on encode + decode
- `bitledger/cli_log.py` — new `log list|find|verify|export` subcommand

No changes to `encoder.py`, `decoder.py`, `models.py`.

Tests: `tests/test_hasher.py`, `tests/test_hash_log.py`

### Phase 2 — Chain integrity (→ v1.2.0 MINOR)

Extend `hash_log.py` with `prev` chain field. Add `log verify` chain walk.
Broken chain → `DecoderWarning` with exact entry position.

### Phase 3 — Wire-embedded hash via extension bytes (→ v2.0.0 MAJOR)

Requires:
1. Extension byte type registry formalized in `README.md`
2. `encoder.py` changes to set `extension_flag` and emit extension bytes (HIGH FRAGILITY)
3. `decoder.py` changes to parse extension types (HIGH FRAGILITY)
4. `models.py` changes to carry typed extensions, not just `list[int]`
5. New encoder flag: `--embed-hash` (+ optionally `--embed-timestamp`)
6. Protocol version bump to 2.0.0

---

## 10. Open decisions (★)

| # | Question | Options | Recommendation |
|---|----------|---------|----------------|
| 1 | **Primary goal now** | Dedup only / full audit / tamper detection | Start with dedup (Phase 1) |
| 2 | **Session nonce location** | Profile JSON / session-state file / per-invocation | Per-invocation is safest for dedup |
| 3 | **Duplicate behavior** | Warn / hard reject | Warn; `--reject-duplicate` for strict |
| 4 | **Both wire_id + semantic_id?** | Yes (store both) / pick one | Store both — cheap, answers different questions |
| 5 | **Chain hashing in Phase 1?** | Yes (add prev now) / Phase 2 | Phase 2 — start simple |
| 6 | **Timestamp in wire (Phase 3)?** | Yes (0x02 extension) / hash only | Include — otherwise no temporal data on wire at all |
| 7 | **sender_id guidance** | Warn if 0x00000000 / silent | Warn on encode if sender_id is zero and --hash-log is on |
| 8 | **Hash in wire doubles record size** | Acceptable / too large | ★ Your call; 32 bytes vs 14 bytes is significant |
| 9 | **HMAC keyed hash** | Not now / add hash_key config | Defer; add later if records cross trust boundaries |
| 10 | **Log storage format** | JSONL / SQLite / sidecar .sha256 | JSONL (zero deps); sidecar for file-level as supplement |

---

## 11. What needs to be decided before Phase 1 implementation

Before any code is written, the following must be specified:

1. **Session nonce**: where is it stored, and when is a new one generated?
2. **Duplicate behavior**: warn or reject? (can be a config field)
3. **Whether to store both wire_id and semantic_id** in every log entry, or pick one
4. **sender_id warning**: should the tool warn when `--hash-log` is active and sender_id is 0x00000000?

Everything else (algorithm, log format, CLI flags) is settled in this document.

---

## 12. Reference

| File | Relevant to |
|------|------------|
| `bitledger/models.py` — `TransactionRecord.extension_flag`, `.extensions` | Phase 3 wire embedding |
| `bitledger/models.py` — `Layer1Config.sender_id`, `Layer2Config.record_sep` | Session identity gaps |
| `bitledger/config.py` — `MasterConfig` | Where new hash config fields go |
| `bitledger/errors.py` — `DecoderWarning` | Pattern for hash mismatch warnings |
| `README.md` §extension_flag | Needs formal extension type spec for Phase 3 |
| `DEVGUIDE.md` — version bump table | Phase 1=1.1.0, Phase 2=1.2.0, Phase 3=2.0.0 |
