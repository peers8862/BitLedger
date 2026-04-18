# BitLedger CLI — Architecture and Design Review

**Version:** 2026-04-14
**Scope:** This document synthesises all task cards, module contracts, spec audit findings,
and implementation plans for the BitLedger Python CLI. It is intended to allow humans and
agents to evaluate architectural decisions, identify gaps, and assess fitness for purpose
before or during implementation.

---

## Contents

1. [Protocol Overview](#1-protocol-overview)
2. [Module Architecture](#2-module-architecture)
3. [Implementation Plan — All Task Cards](#3-implementation-plan--all-task-cards)
4. [Data Flow and Dependency Waves](#4-data-flow-and-dependency-waves)
5. [Open Conflicts and Unresolved Decisions](#5-open-conflicts-and-unresolved-decisions)
6. [Python vs C/Assembly: Design Distance from Embedded Target](#6-python-vs-cassembly-design-distance-from-embedded-target)
7. [Absent Hardware Interface Modules](#7-absent-hardware-interface-modules)
8. [Risk Summary](#8-risk-summary)

---

## 1. Protocol Overview

BitLedger is a binary-native financial transmission protocol. A complete double-entry
accounting transaction — both sides of the ledger entry, accounting classification,
direction, settlement status, value, rounding metadata, and currency — is encoded in
**40 bits (5 bytes)**. The protocol was designed for low-power handheld hardware where
storage, bandwidth, and energy are primary constraints.

### Layer structure

```
Layer 1 — Session Initialisation    64 bits   8 bytes   once per session
Layer 2 — Batch Header              48 bits   6 bytes   once per batch
Layer 3 — Transaction Record        40 bits   5 bytes   once per transaction
Control Record                       8 bits   1 byte    on demand
```

### Layer 1 field map (64 bits)

```
Bit  1        SOH marker              Always 1. Self-framing start sentinel.
Bits 2–4      Protocol version        0–7
Bits 5–8      Core permissions        Read / Write / Correct / Represent
Bits 9–12     Session defaults        Split order / Opposing account / Compound / BL optional
Bits 13–44    Sender ID               32-bit integer
Bits 45–49    Sub-entity ID           5-bit (31 sub-entities)
Bits 50–64    CRC-15 checksum         Over bits 1–49. Polynomial x^15 + x + 1 (0x8003)
```

### Layer 2 field map (48 bits)

```
Bits 1–2      Transmission type       01/10/11 valid; 00 is INVALID (framing guard)
Bits 3–9      Scaling factor (SF)     7-bit index; ×1 to ×1,000,000,000 defined
Bits 10–13    Optimal split           4-bit; default 8; sets the multiplicand/multiplier boundary
Bits 14–16    Decimal position        000/010/100/110 (0/2/4/6 decimal places); odd values undefined
Bit  17       Enquiry bell            Request ACK before next batch
Bit  18       Acknowledge bell        Confirm previous batch received
Bits 19–22    Group separator         4-bit
Bits 23–27    Record separator        5-bit; compound group identity
Bits 28–30    File separator          3-bit
Bits 31–35    Entity ID               5-bit
Bits 36–41    Currency code           6-bit; 0=session default; 1–31=seeded; 32–62=user-defined; 63=multi-currency
Bits 42–45    Rounding balance        Sign-magnitude; 1000=escape
Bits 46–47    Compound prefix         00=none; 01=≤3 groups; 10=≤7 groups; 11=unlimited
Bit  48       Reserved                Always 1
```

### Layer 3 field map (40 bits)

```
Bits 1–17     Multiplicand (A)        Upper value bits at default split S=8
Bits 18–25    Multiplier (r)          Lower value bits / quantity
Bit  26       Rounding flag           0=exact  1=rounded
Bit  27       Rounding direction      0=down   1=up (valid only when bit 26=1)
Bit  28       Split order             0=session default  1=reversed
Bit  29       Direction               0=In  1=Out       ← MUST EQUAL BIT 37
Bit  30       Status                  0=Paid 1=Debt     ← MUST EQUAL BIT 38
Bit  31       Debit/Credit            0=Credit  1=Debit
Bit  32       Quantity present        0=flat value  1=split active (A=price, r=quantity)
Bits 33–36    Account pair            4-bit; 16 account type codes
Bit  37       Direction (BL)          Mirror of bit 29 (exception: sub-type when pair=1111)
Bit  38       Status (BL)             Mirror of bit 30 (exception: sub-type when pair=1111)
Bit  39       Completeness            0=Full  1=Partial (compound record continues)
Bit  40       Extension flag          0=complete  1=extension byte follows
```

### Value encoding formula

```
N = A × (2^S) + r

Where:
  S = Optimal Split (default 8)
  A = N >> S          (multiplicand — upper bits)
  r = N & ((1<<S)-1)  (multiplier — lower bits)
  Real value = (N × SF) / 10^D

Maximum N = 33,554,431  (2^25 − 1)
```

Spec test vectors (from TECHNICAL_OVERVIEW.md):

| Input | SF | D | N | A (S=8) | r |
|---|---|---|---|---|---|
| $4.53 | ×1 | 2 | 453 | 1 | 197 |
| $98,765.43 | ×1 | 2 | 9,876,543 | 38,580 | 63 |
| 24 units @ $2.49 (qty mode) | ×1 | 2 | 5,976 | 249 | 24 |
| $2,450,000 | ×100 | 2 | 24,500 | 95 | 180 |

### Error detection — six rules

| Rule | Mechanism | Layer |
|---|---|---|
| 1 | bit 29 == bit 37 (direction mirror) | Layer 3 field redundancy |
| 2 | bit 30 == bit 38 (status mirror) | Layer 3 field redundancy |
| 3 | NOT (bit 26=0 AND bit 27=1) (invalid rounding state) | Layer 3 invariant |
| 4 | CRC-15 over Layer 1 bits 1–49 | Session integrity |
| 5 | Batch close count == records received | Batch completeness |
| 6 | account_pair=1111 only when compound mode active | Compound integrity |

Note: The README describes "three error detection mechanisms". This is a marketing-level
summary. The Technical Overview defines six distinct rules, all of which must be enforced
in the decoder. Rules 5 and 6 are the most commonly omitted.

---

## 2. Module Architecture

The CLI is implemented as 11 Python modules across 4 logical tiers.

### Tier 0 — Foundation (no protocol logic)

| Module | Lines est. | Role |
|---|---|---|
| `errors.py` | ~30 | 4 typed exception classes |
| `models.py` | ~80 | 5 dataclasses forming the data contract |
| `currencies.py` | ~60 | 32-entry seeded currency table + lookup functions |

`models.py` is the highest-risk module in this tier. All 10 other modules import from it.
A field rename, type change, or default value change in `models.py` silently breaks callers
with no import error — just wrong runtime values. It is designated HIGH FRAGILITY and
requires Orchestrator approval for any post-initial change.

### Tier 1 — Core protocol

| Module | Lines est. | Role |
|---|---|---|
| `control.py` | ~100 | 8-bit control record encode/decode |
| `encoder.py` | ~200 | Value encoding, bit packing, CRC-15, Layer 1/2 headers |
| `decoder.py` | ~200 | Bit unpacking, value reconstruction, 6-rule validation |

`encoder.py` and `decoder.py` are HIGH FRAGILITY. The encoding is bit-precise; any
shift-constant error corrupts every record silently. The decoder's cross-layer validation
logic is the primary defence against protocol violations — a silent wrong decode is
effectively undetectable downstream.

### Tier 2 — I/O and persistence

| Module | Lines est. | Role |
|---|---|---|
| `profiles.py` | ~80 | JSON persistence for named Layer 1/2 configuration profiles |
| `formatter.py` | ~80 | ASCII journal entry, binary, and hex output renderers |

### Tier 3 — User interface

| Module | Lines est. | Role |
|---|---|---|
| `setup_wizard.py` | ~150 | Interactive Layer 1 + Layer 2 profile configuration |
| `simulator.py` | ~100 | Full encode → transmit → decode loop with reporting |
| `bitledger.py` | ~120 | argparse CLI entry point routing 4 subcommands |

`bitledger.py` is SERIALIZED — one writer at a time. It contains no protocol logic;
it is a thin router only.

### Dataclass contracts

**Layer1Config** (13 fields)

| Field | Type | Default | Notes |
|---|---|---|---|
| protocol_version | int | 1 | |
| perm_read | bool | True | |
| perm_write | bool | True | |
| perm_correct | bool | False | |
| perm_represent | bool | False | |
| default_split_order | int | 0 | |
| opposing_account_explicit | bool | False | |
| compound_mode_active | bool | False | |
| bitledger_optional | bool | False | |
| checksum | int or None | None | Distinguished from computed value 0 |
| sender_id | int | 0 | |
| sub_entity_id | int | 0 | |

**Layer2Config** (15 fields, key fields)

| Field | Type | Default | Notes |
|---|---|---|---|
| transmission_type | int | 1 | 0b00 is INVALID — never use as default |
| optimal_split | int | 8 | |
| decimal_position | int | 2 | |
| compound_prefix | int | 0 | |
| reserved | int | 1 | Always 1 per spec |

**TransactionRecord** (19 fields including extensions)

- `true_value` is typed `decimal.Decimal` — the spec datamodel says `float` but this
  implementation overrides it. Using Python `float` for $4.53 produces 4.529999…, which
  incorrectly sets rounding_flag=1 for an exactly representable value.
- `extensions` uses `field(default_factory=list)` — not a shared mutable default.

**SessionState** (10 fields)

- `current_split` defaults to 8 (matches Layer 2 `optimal_split` default)
- Mutable session state is always passed explicitly — no global state

---

## 3. Implementation Plan — All Task Cards

### Wave 0 — Bootstrapping (no prior dependencies)

**TASK-2.00: Python project scaffolding**
- `pyproject.toml` with entry point `bitledger = bitledger.bitledger:main`
- Stub modules for all 11 files (importable, no logic yet)
- `tests/` directory with `conftest.py` and placeholder test files
- `bitledger/profiles/` directory with `.gitkeep`
- Installs as `pip install -e .`; `bitledger --version` returns version string

**TASK-2.01: errors.py**
- 4 exception classes: `ProtocolError`, `EncoderError`, `DecoderError`, `ProfileError`
- Inheritance: all extend `Exception` directly; `ProtocolError` is distinct from
  `EncoderError`/`DecoderError` (they model different failure domains)
- Each carries a human-readable string message

**TASK-2.14: Prereq — docx data extraction**
- Python XML extraction from `BitLedger_Technical_Overview.docx` to obtain:
  the canonical 31-currency ordered list (wire-format data — order is immutable once deployed),
  wizard field order and valid ranges, simulator output format if specified
- Output to `system/audits/docx-extract.md`
- Must run before TASK-2.02 and TASK-2.10

### Wave 1 — Data model

**TASK-2.02: currencies.py**
- 32-entry table: index 0 = session-default sentinel (not a named currency); indices 1–31 =
  seeded standard world currencies in canonical spec order
- `lookup_by_index(n)` → currency dict; raises `ProfileError` out of range
- `lookup_by_code("USD")` → index; case-insensitive; raises `ProfileError` if unknown
- Codes 32–62 are user-defined — pass through without validation
- Code 63 = multi-currency batch sentinel
- **Fragility:** the index-to-currency mapping is wire-format data. Changing the order after
  any records have been encoded invalidates all records using the affected currency codes.

**TASK-2.03: models.py** *(HIGH FRAGILITY)*
- 5 dataclasses: `Layer1Config`, `Layer2Config`, `TransactionRecord`, `SessionState`,
  `ControlRecord`
- `true_value` on `TransactionRecord` is `decimal.Decimal` (override of spec `float`)
- All defaults must match spec exactly (see table above)
- Any post-initial change to field names, types, or defaults requires Orchestrator approval
  and a new task card

### Wave 2 — Core protocol

**TASK-2.04: control.py**
- `encode_control(type: int, payload: int) -> int`: `(type << 4) | payload`, result 0–127
- `decode_control(byte: int) -> tuple[int, int]`: raises `DecoderError` if high bit set
- Escape detection: payload=0b1111 on types 000/001/010 signals next byte carries full value
- ACK/NACK: type=0b011; bit 5 of full byte (first payload bit) = 0 → ACK, 1 → NACK
- Layer 2 short-form: type=0b110, payload=0b1111
- All 8 type codes handled without error

**TASK-2.05: encoder.py — value encoding core**
- `decompose(N, S)` → `(A, r)` = `(N >> S, N & ((1<<S)-1))` for all N in 0..33,554,431
- `rounding_mode(account_pair)` → 'up' | 'down' | 'nearest':
  - ROUND_UP_PAIRS: `{0001, 0011, 0101, 0111, 1000, 1100}` (liability-side entries)
  - ROUND_DOWN_PAIRS: `{0100, 0110, 1001, 1011}` (income/asset entries)
  - All others: 'nearest' (round half up)
- `encode_value(true_value, sf_index, decimal_position, account_pair)` → `(A, r, rounding_flag, rounding_dir)` using `decimal.Decimal` arithmetic only — never float
- Overflow: N > 33,554,431 raises `EncoderError`

**TASK-2.06: encoder.py — serialise + headers** *(BLOCKED on CONFLICT-005)*
- `serialise(record, S)` → 40-bit integer with exact shift constants matching spec bit positions
- `to_bit_string(n)` → groups as `17 | 8 | 7 | 4 | 1 | 1 | 1 | 1`
- `to_hex(n)` → 10 uppercase hex characters (5 bytes, no separators)
- CRC-15 computation and Layer 1 header encoding (64 bits)
- Layer 2 short-form emitted when all Layer 2 values equal session defaults
- account_pair=0b1111 rejected when compound_mode_active=False
- account_pair=0b1111 rejected when compound_prefix=0b00 even if compound_mode_active=True

**TASK-2.07: decoder.py** *(BLOCKED on CONFLICT-005)*
- `unpack(n)` → all fields from 40-bit integer; shift constants must be bitwise inverse of `serialise()`
- `decode_value(A, r, sf_index, decimal_position)` → `Decimal`; integer arithmetic in numerator only
- Enforces all 6 error detection rules; raises `DecoderError` with field name in message on violation
- Rule 1/2 (mirror rules) suspended for account_pair=0b1111 continuation records
- Layer 2 short-form decoded as session defaults
- Roundtrip: `serialise(unpack(n)) == n` for all valid records

### Wave 3 — I/O

**TASK-2.08: profiles.py**
- `save_profile(name, layer1, layer2)` → writes `bitledger/profiles/<name>.json`
- `load_profile(name)` → `(Layer1Config, Layer2Config)`; raises `ProfileError` if not found
- `list_profiles()` → sorted list of profile name strings
- `delete_profile(name)` → removes file; raises `ProfileError` if not found; name="default" is protected
- `get_default_profile()` → loads "default" or returns factory defaults if absent
- JSON field names must match dataclass field names exactly (models.py rename = silent breakage)
- Uses `pathlib.Path` throughout; no `os.path`

**TASK-2.09: formatter.py**
- `format_binary(n)` → 40-bit string grouped per spec section headers
- `format_hex(n)` → `0x` + 10 uppercase hex chars
- `format_journal(record, session)` → multi-line journal entry in exact spec format:
  - Debit/credit labels from direction bit
  - Amount in decimal with currency symbol
  - Rounding flag annotation
  - Account pair label
  - Binary and hex lines at bottom
- All formatters return `str` — no direct printing
- Uses `Decimal.quantize()` for display rounding — never float

### Wave 4 — User interface

**TASK-2.10: setup_wizard.py**
- `run_wizard(input_fn=input)` prompts for all Layer 1 and Layer 2 fields in spec-canonical order
- Each prompt: field name, valid range, current/default value; Enter keeps default
- Invalid input re-prompts with error message — does not crash
- Returns `(Layer1Config, Layer2Config)` on completion
- Accepts pre-populated config for edit mode
- transmission_type=0b00 is INVALID and must be rejected by the wizard
- Compound prefix ≠ 0b00 with compound_mode_active=False generates a warning (not error)
- `input_fn` parameter enables test injection without interactive prompts

**TASK-2.11: simulator.py**
- `run_simulation(profile_name, transactions)` → `SimulationResult` dataclass
- Per-transaction output: input values, encoded binary (hex + bit string), decoded journal entry, PASS/FAIL
- Layer 1/2 headers encoded at session/batch start; CRC-15 verified at receive end
- Rounding events logged: original value and encoded approximation shown
- Summary: N transactions, M encoded, K decoded OK, J errors

### Wave 5 — Entry point and validation

**TASK-2.12: bitledger.py** *(SERIALIZED)*
- 4 subcommands: `setup`, `encode`, `decode`, `simulate`
- `--profile NAME` consistent across all subcommands (shared parent parser)
- Exit codes: 0=success, 1=user error, 2=protocol/internal error
- All error output to stderr
- argparse `set_defaults(func=handler)` pattern — dispatcher is a single `args.func(args)` call
- Contains no protocol logic — thin router only

**TASK-2.13: Complete test suite**
- All 4 spec test vectors with exact Decimal equality (no float comparison)
- Roundtrip: encode → decode for minimum/maximum/mid-range values at all SF indices 0–17
- CRC-15 bit-flip: ALL 49 bits flipped individually; every flip produces non-zero remainder
- All 6 error detection rules tested with explicit rule-violating inputs
- Default profile protection test; missing profile raises `ProfileError`
- No `assertEqual(float, …)` anywhere in the test suite

---

## 4. Data Flow and Dependency Waves

```
Wave 0 ─────────────────────────────────────────────────────────────────────
  errors.py          models.py (stub)     TASK-2.14 (docx extraction)
         │                  │                       │
Wave 1 ──┼──────────────────┼───────────────────────┼──────────────────────
         │            models.py (full)        currencies.py
         │                  │                       │
Wave 2 ──┼──────────────────┴───────────────────────┘──────────────────────
         │         control.py     encoder.py (2 cards)    decoder.py
         │                  │              │                     │
Wave 3 ──┼──────────────────┴──────────────┴─────────────────────┘─────────
         │                  profiles.py              formatter.py
         │                        │                       │
Wave 4 ──┼──────────────────────  ┼───────────────────────┤───────────────
         │              setup_wizard.py           simulator.py
         │                        │                       │
Wave 5 ──┼────────────────────────┴───────────────────────┘───────────────
                         bitledger.py            test suite (complete)
```

All module dependencies flow in one direction. No circular imports.

**Module dependency table:**

| Module | Imports from |
|---|---|
| errors.py | (none) |
| models.py | errors.py |
| currencies.py | errors.py |
| control.py | errors.py, models.py |
| encoder.py | errors.py, models.py, currencies.py |
| decoder.py | errors.py, models.py, currencies.py |
| profiles.py | errors.py, models.py |
| formatter.py | errors.py, models.py, currencies.py, encoder.py |
| setup_wizard.py | errors.py, models.py, profiles.py |
| simulator.py | encoder.py, decoder.py, profiles.py, formatter.py |
| bitledger.py | all of the above |

---

## 5. Open Conflicts and Unresolved Decisions

### CONFLICT-005 — Bits 37–38 in continuation records *(BLOCKS TASK-2.06 and TASK-2.07)*

**The contradiction:**
The Layer 3 field map defines bits 37–38 as always mirroring bits 29–30 (direction and
status). The Compound Transactions section defines those same bits as carrying sub-type in
`account_pair=1111` records (00=Standard, 01=Correcting, 10=Reversal, 11=Cross-batch).
These are mutually exclusive. A correcting entry (sub-type 01) would require bit 37=0
while simultaneously mirroring a debit direction (bit 29=1).

**Proposed resolution (pending confirmation):**
Bits 37–38 carry sub-type in continuation records. Cross-layer Rules 1 and 2 are suspended
for account_pair=1111. This is the only interpretation that makes correcting entries and
reversals functionally distinguishable.

**Impact:** encoder.py, decoder.py, models.py (sub-type field needed on TransactionRecord),
all compound transaction tests.

### CONFLICT-001 — account_pair 0b1110 name

The README calls it "Correction / Netting"; the Technical Overview calls it "Correction"
only. Resolution: read `BitLedger_Protocol_v3.docx` before implementing account pair 1110
display logic. Affects formatter.py only; low urgency.

### GAP-005 — Odd decimal position values (1, 3, 5, 7)

The 3-bit decimal position field (bits 14–16) can hold values 0–7. Only 0, 2, 4, 6 are
documented. Whether odd values raise ProtocolError or are reserved/undefined is unspecified.
Resolution needed before decoder.py validates Layer 2 headers.

### GAP-001 — SF indices 10–127

The 7-bit SF field supports 128 values; only indices 0–9 are defined in the spec. Whether
10–127 are user-definable or reserved is undocumented in the available markdown. Affects
encoder.py validation and currencies.py lookup.

### ADD-002 — Rounding mode set membership

The ROUND_UP_PAIRS and ROUND_DOWN_PAIRS sets appear only in the Technical Overview, not
verifiably in the protocol spec. If the full spec defines different sets, the rounding
direction flag will be silently wrong for affected account pairs. Must be verified against
`BitLedger_Protocol_v3.docx` before encoder.py is merged.

---

## 6. Python vs C/Assembly: Design Distance from Embedded Target

The BitLedger protocol was designed for deployment on **low-power handheld hardware** where
the primary constraints are storage, transmission bandwidth, and energy per operation. The
CLI implementation described here uses Python 3.10+, dataclasses, `decimal.Decimal`, and
argparse. The following analysis examines where this diverges from a C or assembly
implementation targeting embedded deployment, and what that means for reliability in harsh
conditions.

### 6.1 What a C/assembly implementation would look like

In C, the Layer 3 transaction record would likely be a packed struct or a 5-byte array
manipulated with bitwise operations:

```c
// Typical embedded C representation
typedef struct __attribute__((packed)) {
    uint8_t  bytes[5];      // 40 bits, wire order
} bl_record_t;

// Field access via bitmask macros
#define BL_GET_ACCOUNT_PAIR(r)  (((r).bytes[4] >> 4) & 0x0F)
#define BL_GET_DIRECTION(r)     (((r).bytes[3] >> 3) & 0x01)
#define BL_SET_A(r, v)          /* ... bit manipulation ... */
```

The CRC-15 would be a hardware-native table-driven routine consuming a fixed number of
cycles. Session state would be a statically allocated struct (no heap). The encoder and
decoder would operate directly on buffers passed by pointer. An entire encode operation
might fit in 50–100 instructions with deterministic execution time.

An assembly implementation on an 8-bit or 16-bit microcontroller would be even more direct:
bit-shift operations on registers, with no memory allocation overhead, no garbage collector
pauses, and no floating-point unit needed (the value encoding uses only integer arithmetic).

### 6.2 Python design choices and their distance from embedded targets

**`decimal.Decimal` for monetary arithmetic**

The Python implementation uses `decimal.Decimal` as a safety constraint against
floating-point precision loss. In C, the same safety is achieved structurally: the
protocol encodes all values as integers (N = A × 2^S + r), and the real-value reconstruction
`(N × SF) / 10^D` is done in fixed-point or 64-bit integer arithmetic at display time. There
is no floating-point at any point in the encoding path. The Python `Decimal` type solves a
Python-specific problem: Python `float` being IEEE 754 double-precision, which misrepresents
common decimal fractions. In C on a microcontroller without an FPU, you would not use
floating point at all — the protocol integer representation is the natural form.

**Dataclasses and type annotations**

Python's typed dataclasses (`Layer1Config`, `Layer2Config`, `TransactionRecord`,
`SessionState`) provide safety at the cost of indirection. Each dataclass is a heap object;
field access involves attribute lookup. In C, these would be stack-allocated structs with
direct field access and no allocation cost. The Python model adds roughly 200–500 bytes of
per-instance overhead and unpredictable GC pauses that would be unacceptable in
interrupt-driven embedded code.

**argparse CLI**

The full argparse CLI with 4 subcommands, help text generation, and profile wizard makes
sense for a human-interactive desktop tool. An embedded implementation would have no CLI;
the encoding and decoding functions would be called directly by firmware. The CLI is
entirely absent from the embedded model.

**Error handling via exceptions**

Python exceptions propagate up the call stack and are caught at module boundaries. In C
embedded code, error handling is typically done with return codes (`BL_ERR_OVERFLOW`,
`BL_ERR_CRC_FAIL`, etc.) and the caller checks immediately. Python exceptions are not
slower in the happy path but do carry stack unwinding overhead on the error path — which
in an embedded CRC failure scenario might be a hard fault or watchdog trigger rather than
a graceful Python traceback.

**JSON profile persistence**

The Python CLI stores session configuration as named JSON files. An embedded device
would store session state in EEPROM or flash as a raw binary struct — typically exactly
the 64-bit Layer 1 header and 48-bit Layer 2 header, already in wire format, requiring no
serialisation step at session start.

### 6.3 What the Python implementation does share with an embedded target

- **Integer arithmetic throughout the encoding path.** The core `N = (A << S) | r` and
  CRC-15 operations are identical in Python and C. The algorithm is portable.
- **Fixed bit widths.** The protocol's 40/48/64-bit fields map cleanly to `uint8_t[5]`,
  `uint8_t[6]`, and `uint8_t[8]` arrays in C. Python's arbitrary-precision integers do
  not change the algorithm, just the representation.
- **Deterministic record structure.** Every Layer 3 record is exactly 5 bytes. No
  length prefixing, no schema negotiation, no variable-length encoding. This is as
  embedded-friendly as a protocol gets.
- **Error detection is structural, not additive.** The CRC-15 and cross-layer mirror
  bits are embedded in the record format itself. The decoder does not need a separate
  validation pass — validation is inherent in the decode operation. This is well-suited
  to embedded implementations where code space is at a premium.

### 6.4 Reliability in harsh conditions — what the Python CLI cannot do

An embedded deployment in harsh conditions (vibration, temperature extremes, power
interruptions, noisy communication channels) requires:

1. **Deterministic execution time.** Python's GC pauses are non-deterministic. A hard
   real-time embedded system would use C with statically allocated buffers.

2. **No dynamic memory allocation.** Python allocates on every function call, every
   object creation. Embedded systems often have no heap at all and operate entirely from
   a fixed memory map.

3. **Interrupt-safe operation.** An encoder/decoder running in an ISR (interrupt service
   routine) context must be reentrant, stack-bounded, and non-blocking. Python has the GIL
   and is not interrupt-aware.

4. **Power-fail recovery.** Partial writes during a power interruption must be detectable
   and recoverable. The CRC-15 on the Layer 1 header handles session-level detection, but
   record-level write atomicity requires hardware support (write-through cache, atomic flash
   sector writes) that is invisible to the Python layer.

5. **Communication error recovery.** In a noisy channel, the decoder must handle partial
   records, framing errors, and byte substitutions. The Python CLI has no serial framing or
   byte synchronization layer — it operates on already-correct integers.

The Python CLI is correctly scoped as a **desktop tool for encoding, decoding, and
simulation** — not as embedded firmware. The protocol itself is fully capable of embedded
deployment; the CLI is a reference implementation and test harness for that deployment.

---

## 7. Absent Hardware Interface Modules

The CLI as designed has no modules that connect it to physical transmission hardware. The
following modules would be required to enable a real encoder/decoder to interface with a
transmitting hardware attachment (serial port, USB CDC, I2C, SPI, UART, BLE, etc.):

### 7.1 Serial framing module (`framer.py`)

**What it does:** The protocol record stream has no byte-level framing. The Layer 1 SOH
bit (bit 1, always 1) provides session-start detection, but the decoder has no way to
synchronize to the byte boundary of an incoming serial stream, handle mid-stream join, or
detect a dropped byte that shifts all subsequent records by one byte.

A framing module would need to:
- Implement a byte synchronization strategy (e.g., scan for the SOH bit pattern in a
  sliding window)
- Handle record boundary detection (records are fixed-length once SF is known, so
  counting bytes is sufficient after sync)
- Buffer partial records during transmission
- Detect framing loss and re-sync

**Interfaces needed:** `read_raw_bytes(n: int) -> bytes` from a hardware source;
`write_raw_bytes(data: bytes)` to a hardware sink.

### 7.2 Transport layer module (`transport.py`)

**What it does:** Manages the physical I/O connection to the hardware attachment. The
current CLI operates on in-memory integers; a real deployment needs:
- Serial port open/close/configure (`pyserial` or platform UART)
- Baud rate, parity, stop bits configuration (or SPI clock/mode for SPI)
- Read with timeout (for ACK/enquiry-bell response waiting)
- Write with flow control
- Connection state tracking

For a USB CDC device this might wrap `pyserial`; for a custom UART it might wrap a
platform-specific driver; for Bluetooth it might wrap `bleak` or a custom BLE GATT profile.

**Functions needed:**
- `open_connection(port, baud) -> Connection`
- `close_connection(conn: Connection)`
- `send_record(conn, record_bytes: bytes)`
- `receive_record(conn, timeout_ms: int) -> bytes | None`

### 7.3 ACK/enquiry state machine (`session_protocol.py`)

**What it does:** The protocol defines an enquiry/acknowledge handshake (Layer 2 bits 17–18)
and ACK/NACK control records (type 0b011). The current CLI encodes and decodes these bits
but has no module that drives the actual handshake state machine:
- Send batch → await ACK if enquiry bell set
- On NACK: retransmit or escalate
- On timeout: retransmit or raise `ProtocolError`
- Track batch sequence numbers for ACK/NACK reference

This logic lives between the transport layer and the encoder/decoder. It is entirely absent
from the current design — the simulator approximates it but does not implement a real
half-duplex state machine against a hardware peer.

### 7.4 Hardware-specific value input module (`hw_input.py`)

**What it does:** In an embedded deployment, transaction values would come from hardware
sources — a barcode scanner, keypad, POS terminal, or sensor. On the desktop CLI, values
are typed by a human. A bridge module would:
- Accept raw input from a hardware peripheral (HID, serial, GPIO)
- Map hardware-specific value representations to `decimal.Decimal` in the units expected
  by `encode_value()`
- Handle hardware-specific error conditions (scanner timeout, keypad bounce)

### 7.5 Clock and timestamp module (`clock.py`)

**What it does:** Extension byte type 5 carries a timestamp offset relative to the session
start (see Extension Bytes section of the Technical Overview). The current design has no
module that:
- Captures session start time
- Computes record timestamps relative to session start
- Handles clock drift, RTC availability, and timestamp format on different hardware

An embedded device might use a hardware RTC or a free-running timer; a desktop tool would
use `datetime.datetime.now()`. This difference is currently unaddressed.

### 7.6 Session persistence / crash recovery module (`session_store.py`)

**What it does:** If a session is interrupted mid-batch (power failure, disconnection),
the protocol state (current split, record count, compound group state, rounding balance)
must be recoverable. The current `profiles.py` saves Layer 1 and Layer 2 *configuration*
but not *live session state*. A crash recovery module would:
- Checkpoint `SessionState` after each record (or batch) to a durable store
- On restart, detect incomplete sessions and determine whether to resume or discard
- Manage the Layer 2 batch close count for rule 5 validation across restarts

### 7.7 Summary of absent modules

| Module | Concern | Required for |
|---|---|---|
| `framer.py` | Byte synchronization, partial records | Any real hardware link |
| `transport.py` | Physical I/O (serial/USB/BLE/SPI) | Any real hardware link |
| `session_protocol.py` | ACK/NACK state machine | Half-duplex reliable delivery |
| `hw_input.py` | Hardware peripheral → Decimal | POS, scanner, keypad input |
| `clock.py` | Timestamp extension support | Extension byte type 5 |
| `session_store.py` | Crash recovery, session checkpointing | Persistent deployment |

None of these modules are in scope for the CLI as designed. The CLI targets human-in-the-loop
desktop use: encode a transaction from typed input, decode a hex string, run a simulation,
configure a profile. The protocol is hardware-capable; the CLI is not hardware-connected.

---

## 8. Risk Summary

### Highest severity

| Risk | Module | Consequence |
|---|---|---|
| CONFLICT-005 unresolved | encoder.py, decoder.py | Cannot implement compound transaction encode/decode correctly |
| Off-by-one in serialise() shift constants | encoder.py | Every record silently corrupted |
| float used instead of Decimal anywhere in encode path | encoder.py | Wrong rounding flag on exact values like $4.53 |
| models.py field rename post-initial | models.py | Cascading silent failures in all 10 dependent modules |

### Medium severity

| Risk | Module | Consequence |
|---|---|---|
| Rounding mode set membership wrong | encoder.py | Wrong rounding direction flag, no error raised |
| Rule 5 or Rule 6 omitted | decoder.py | Batch-level or compound-level corruption undetected |
| Currency index order wrong | currencies.py | All records using affected currencies decode to wrong currency |
| transmission_type=0b00 not blocked in wizard | setup_wizard.py | Invalid Layer 2 header, framing guard defeated |
| Odd decimal position values not handled | decoder.py | Undefined behavior on malformed records |

### Low severity

| Risk | Module | Consequence |
|---|---|---|
| Extension byte chain termination off-by-one | decoder.py | Dropped or duplicated extension data |
| Session state not threaded via SessionState | any | Global state bug if multiple sessions in simulator |
| Journal entry format differs from spec format | formatter.py | Display only; no protocol impact |

### Quality gates enforcing these checks

| Gate | Condition |
|---|---|
| A | No implementation without Orchestrator-authored acceptance criteria |
| B | No merge with failing tests or unresolved high-severity Verifier findings |
| C | No task marked complete unless CLI help strings and docstrings match implementation |
| D | No release claim without fully signed release checklist |
| E | No untracked TODO in production code — every deferred item has a task card |

---

*Document generated by Orchestrator agent, 2026-04-14.*
*Source files: TASK-2.00 through TASK-2.14, explorer-a-report.md, explorer-b-report.md,*
*TECHNICAL_OVERVIEW.md, README.md, mathmodel_by_grok.md.*
