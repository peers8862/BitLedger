# BitLedger — Condensed Technical Overview

**Protocol Specification v3.0 | Implementation Reference**

This document is a condensed technical reference for the BitLedger binary financial transmission protocol. For the complete specification including full worked examples, value range tables, and CRC-15 implementation, see `BitLedger_Protocol_v3.docx`.

**Python reference monographs (this repo):** [value encoding & SF ladder](../analysis/value_encoding_scaling_factor_reference.md) · [notation & rounding observability](../analysis/bitledger_notation_reference.md).

---

## Table of Contents

1. [Layer 1 — Session Initialisation](#layer-1)
2. [Layer 2 — Batch Header](#layer-2)
3. [Layer 3 — Transaction Record](#layer-3)
4. [Value Encoding Formula](#value-encoding)
5. [Flags Reference](#flags)
6. [Account Pair Table](#account-pairs)
7. [Control Records](#control-records)
8. [Compound Transactions](#compound-transactions)
9. [Extension Bytes](#extension-bytes)
10. [Error Detection Rules](#error-detection)
11. [Encoder Decision Algorithm](#encoder-algorithm)
12. [Value Range Quick Reference](#value-ranges)
13. [Journal Entry Format](#journal-format)
14. [Python Data Models](#data-models)

---

## Layer 1 — Session Initialisation {#layer-1}

**64 bits / 8 bytes. Transmitted once per session.**

```
Bit  1        SOH Marker          Always 1. Self-framing.
Bits 2–4      Protocol Version    000–111 (8 versions)
Bits 5–8      Core Permissions    Read / Write / Correct / Represent
Bits 9–12     Session Defaults    Split order / Opposing account / Compound / BL optional
Bits 13–44    Sender ID           32-bit integer (up to 4,294,967,295 senders)
Bits 45–49    Sub-Entity ID       5-bit (31 sub-divisions)
Bits 50–64    CRC-15 Checksum     Over bits 1–49, polynomial x^15 + x + 1
```

### Session Default Bits 9–12

| Bit | Convention | 0 | 1 |
|---|---|---|---|
| 9 | Split order default | Multiplicand first | Multiplier first |
| 10 | Opposing account | Inferred | Always explicit in ext byte |
| 11 | Compound mode | Off | Active — 1111 markers valid |
| 12 | BitLedger block | Always present | Optional |

### CRC-15

```python
CRC15_POLY = 0x8003  # x^15 + x + 1

def crc15(data_bits: int, num_bits: int = 49) -> int:
    reg  = (data_bits << 15) & ((1 << (num_bits + 15)) - 1)
    poly = CRC15_POLY << (num_bits - 1)
    for i in range(num_bits):
        if reg & (1 << (num_bits + 14 - i)):
            reg ^= poly
        poly >>= 1
    return reg & 0x7FFF

# Encoder: append crc15(payload_49, 49) as bits 50–64
# Decoder: crc15(all_64_bits, 64) == 0 means valid
```

---

## Layer 2 — Batch Header {#layer-2}

**48 bits / 6 bytes. Transmitted once per batch.**

```
Bits 1–2      Transmission Type     01=pre-converted  10=copy  11=represented
              Code 00 is INVALID — ensures first byte is never all zeros
Bits 3–9      Scaling Factor        7-bit index, see table below
Bits 10–13    Optimal Split         4-bit, default 8
Bits 14–16    Decimal Position      000=integer  010=2 places  100=4 places  110=6 places
Bit  17       Enquiry Bell          1 = request ACK before next batch
Bit  18       Acknowledge Bell      1 = confirm previous batch received
Bits 19–22    Group Separator       4-bit (15 groups)
Bits 23–27    Record Separator      5-bit (31 records) — compound group identity
Bits 28–30    File Separator        3-bit (7 files)
Bits 31–35    Entity ID             5-bit (31 sub-entities)
Bits 36–41    Currency Code         6-bit (64 currencies, 0=session default)
Bits 42–45    Rounding Balance      4-bit sign-magnitude, see below
Bits 46–47    Compound Prefix       00=none  01=≤3 groups  10=≤7 groups  11=unlimited
Bit  48       Reserved              Always 1
```

### Scaling Factor Index

| Index | SF | Step at D=2 | Max at D=2 |
|---|---|---|---|
| 0000000 | × 1 | $0.01 | $335,544.31 |
| 0000001 | × 10 | $0.10 | $3,355,443.10 |
| 0000010 | × 100 | $1.00 | $33,554,431.00 |
| 0000011 | × 1,000 | $10.00 | $335,544,310.00 |
| 0000100 | × 10,000 | $100.00 | $3,355,443,100.00 |
| 0000101 | × 100,000 | $1,000.00 | $33,554,431,000.00 |
| 0000110 | × 1,000,000 | $10,000.00 | $335,544,310,000.00 |
| 0000111 | × 10,000,000 | $100,000.00 | $3,355,443,100,000.00 |
| 0001000 | × 100,000,000 | $1,000,000.00 | $33,554,431,000,000.00 |
| 0001001 | × 1,000,000,000 | $10,000,000.00 | $335,544,310,000,000.00 |

### Rounding Balance (bits 42–45)

Sign-magnitude encoding. High bit = sign (0=up, 1=down). Lower 3 bits = magnitude 0–7.

```
0000 = exactly balanced
0001–0111 = net +1 to +7 units rounded up
1000 = ESCAPE — see batch-close control record
1001–1111 = net -1 to -7 units rounded down
```

### Layer 2 Short-Form

When all Layer 2 values equal session defaults, replace 48-bit header with one byte:

```
0  110  1111    (control type 110, payload 1111 = all defaults)
```

---

## Layer 3 — Transaction Record {#layer-3}

**40 bits / 5 bytes. Transmitted once per transaction.**

```
Bits 1–17     Multiplicand         Upper value bits (17 bits at default split)
Bits 18–25    Multiplier           Lower value bits / quantity (8 bits at default split)
Bit  26       Rounding Flag        0=exact  1=rounded
Bit  27       Rounding Direction   0=down  1=up  (valid only when bit 26=1)
Bit  28       Split Order          0=follow session default  1=reverse
Bit  29       Direction            0=In  1=Out   ← MUST EQUAL BIT 37
Bit  30       Status               0=Paid  1=Debt ← MUST EQUAL BIT 38
Bit  31       Debit/Credit         0=Credit  1=Debit
Bit  32       Quantity Present     0=flat value  1=split active
Bits 33–36    Account Pair         4-bit code, see table
Bit  37       Direction (BL)       Mirror of bit 29
Bit  38       Status (BL)          Mirror of bit 30
Bit  39       Completeness         0=Full  1=Partial
Bit  40       Extension Flag       0=complete  1=extension byte follows
```

---

## Value Encoding Formula {#value-encoding}

```
N  =  A × (2^S) + r

Where:
  S = Optimal Split (default 8, from Layer 2)
  A = floor(N / 2^S)   — Multiplicand field
  r = N mod (2^S)      — Multiplier field

For any N in 0..33,554,431: A and r are unique, always whole integers.
No gaps. Every integer is reachable.

Decode formula:
  Real Value  =  (N × Scaling Factor) / 10^DecimalPosition

When bit 32 = 1 (Quantity Present):
  Price    = A field
  Quantity = r field
  N        = Price × Quantity
  Real Value = (N × SF) / 10^D

When bit 32 = 0 (flat value):
  N = (A << S) | r
  Real Value = (N × SF) / 10^D
```

### Decode Examples

```
$4.53     SF=×1  D=2  N=453    A=1    r=197
$98,765.43 SF=×1  D=2  N=9,876,543  A=38,580  r=63
24 units @ $2.49  bit32=1  A=249  r=24  N=249×24=5,976  Real=$59.76
$2,450,000 SF=×100 D=2  N=24,500  A=95  r=180
```

---

## Flags Reference {#flags}

### Bits 26–27 — Rounding Signal (read as a pair)

| 26–27 | Meaning | Action |
|---|---|---|
| `00` | Exact | Decode normally |
| `10` | Rounded down | Log direction, decode |
| `11` | Rounded up | Log direction, decode |
| `01` | **Invalid** | **Raise ProtocolError** |

### Bits 27 and 32 Interaction

When `bit 32 = 1`, Optimal Split is **always** taken from Layer 2 `current_split`. Bit 27 is always free for Rounding Direction regardless of bit 32.

### Cross-Layer Validation

```python
if record[29] != record[37]:
    raise ProtocolError('Direction mismatch: bit29 != bit37')
if record[30] != record[38]:
    raise ProtocolError('Status mismatch: bit30 != bit38')
if record[26] == 0 and record[27] == 1:
    raise ProtocolError('Invalid rounding state: bit26=0 bit27=1')
```

---

## Account Pair Table {#account-pairs}

| Code | Pair | Dir=0 (In) | Dir=1 (Out) |
|---|---|---|---|
| `0000` | Op Expense / Asset | Expense incurred | Expense reversed |
| `0001` | Op Expense / Liability | Expense on credit | Liability reduces |
| `0010` | Non-Op Expense / Asset | Non-core expense | Non-core reversal |
| `0011` | Non-Op Expense / Liability | Non-core on credit | Non-core liability |
| `0100` | Op Income / Asset | Revenue received | Revenue reversed |
| `0101` | Op Income / Liability | Revenue accrued | Accrued reversed |
| `0110` | Non-Op Income / Asset | One-time income | One-time reversed |
| `0111` | Non-Op Income / Liability | One-time accrued | One-time liability |
| `1000` | Asset / Liability | Asset on credit | Liability repaid |
| `1001` | Asset / Equity | Owner contributes | Asset distributed |
| `1010` | Liability / Equity | Equity to liability | Liability to equity |
| `1011` | Asset / Asset | Asset transfer in | Asset transfer out |
| `1100` | Liability / Liability | Liability assumed | Liability transferred |
| `1101` | Equity / Equity | Equity in | Equity out |
| `1110` | Correction | Inference suspended | Inference suspended |
| `1111` | **Continuation** | **See compound section** | **See compound section** |

---

## Control Records {#control-records}

**8 bits / 1 byte. Leading 0 distinguishes from transaction records.**

```
Structure:  0  [TTT]  [PPPP]
            |   type   payload
            leading 0

Type 000  Scaling Factor change
          Payload 0000–1001: SF index (powers of 10 ×1 to ×1,000,000,000)
          Payload 1010–1110: user-defined
          Payload 1111: escape — next byte carries full 7-bit SF

Type 001  Currency change
          Payload 0000–1110: currency index
          Payload 1111: escape — next byte carries 6-bit code

Type 010  Batch close
          Payload: record count (0–14)
          Payload 1111: escape — next byte carries full count

Type 011  ACK / NACK
          Bit 5 = 0 ACK, 1 NACK
          Bits 6–8: batch sequence reference (0–7)

Type 100  Compound group open
          Payload: record count (1–14)

Type 101  Optimal Split update
          Payload: new Optimal Split (0–15)
          Reverts to Layer 2 value at batch close

Type 110  Layer 2 short-form
          Payload 1111: all defaults apply

Type 111  Reserved — transmit payload as 1111
```

### Python Control Record Functions

```python
def encode_control(type_bits: int, payload: int) -> int:
    return (type_bits << 4) | payload   # 0-127, high bit always 0

def decode_control(byte: int) -> tuple[int, int]:
    if byte & 0x80:
        raise DecoderError('Not a control record: high bit is 1')
    return (byte >> 4) & 0x7, byte & 0xF
```

---

## Compound Transactions {#compound-transactions}

Linked multi-entry records using the `1111` continuation marker (Model B).

### How It Works

1. First record is a complete standard 40-bit record with a valid account pair
2. Its `bit 39 = 1` (Partial — continuation follows)
3. Next record sets `bits 33–36 = 1111` — compound continuation signal
4. Bits 37–38 of the continuation record carry **sub-type**, not direction/status mirrors:

| Sub-type (bits 37–38) | Meaning |
|---|---|
| `00` | Standard linked entry (COGS, contra, paired leg) |
| `01` | Correcting entry for the preceding record |
| `10` | Reversal of the preceding record |
| `11` | Cross-batch continuation |

5. Continuation `bit 39 = 0` closes the compound group
6. Compound group identity = Record Separator value at time of group open

### Compound Example — Sale + COGS

```
Record 1:  pair=0100  dir=0  status=0  complete=1(Partial)
           Op Income / Asset. Revenue $499.90. Continuation follows.

Record 2:  pair=1111  bits37-38=00  complete=0(Full)
           COGS $180.00. Standard continuation. Compound closed.
```

### Compound Prefix in Layer 2

| Bits 46–47 | Meaning | Violation Action |
|---|---|---|
| `00` | No compounds. 1111 is a protocol error. | NACK, reject batch |
| `01` | Up to 3 compound groups | NACK after 3rd group closes |
| `10` | Up to 7 compound groups | NACK after 7th group closes |
| `11` | Unlimited | No ceiling |

---

## Extension Bytes {#extension-bytes}

Present when `bit 40 = 1`. Chainable — bit 8 of each extension triggers the next.

| Use | Bits | Range | Notes |
|---|---|---|---|
| Quantity | 8 of 8 | 0–255 units | When bit 32=0 and quantity needed |
| Subcategory | 3 of 8 | 0–7 | 8 sub-types per account pair |
| Opposing Account | 4 of 8 | 0–15 | When Layer 1 bit 10=1 |
| Currency Override | 6 of 8 | 0–63 | Per-record currency |
| Timestamp Offset | 8 of 8 | 0–255 | Units from session epoch |
| Precision Anchor | 8 of 8 | 0–255 | Sub-SF remainder for high-denomination records |
| Party Type | 2 of 8 | 0–3 | 00=Internal 01=Customer 10=Vendor 11=Other |

---

## Error Detection Rules {#error-detection}

Three independent mechanisms. All must pass for a record to be accepted.

```
Rule 1 (Cross-layer Direction):  bit 29  ==  bit 37
Rule 2 (Cross-layer Status):     bit 30  ==  bit 38
Rule 3 (Rounding State):         NOT (bit26=0 AND bit27=1)
Rule 4 (Session Integrity):      CRC-15 over Layer 1 bits 1–49 == 0
Rule 5 (Batch Integrity):        Batch close count == records received
Rule 6 (Compound Integrity):     1111 markers only when compound_prefix != 00
                                  and Layer 1 bit 11 == 1
```

Any violation raises `ProtocolError`. Records are not posted to ledger on error.

---

## Encoder Decision Algorithm {#encoder-algorithm}

```python
from decimal import Decimal, ROUND_UP, ROUND_DOWN, ROUND_HALF_UP

MAX_N = (2 ** 25) - 1  # 33,554,431

def encode_value(true_value: Decimal, sf_index: int,
                 decimal_position: int, account_pair: int) -> tuple:
    """Returns (A, r, rounding_flag, rounding_dir)"""
    SF = Decimal(SCALING_FACTORS[sf_index])
    D  = decimal_position

    # Step 1: raw integer
    R = true_value * Decimal(10 ** D) / SF

    # Step 2: exact?
    if R == R.to_integral_value():
        N = int(R)
        assert N <= MAX_N, f'Overflow: use higher SF index'
        return decompose(N, S), False, 0

    # Step 3: rounding direction by account type
    mode = rounding_mode(account_pair)
    if mode == 'up':
        N = int(R.to_integral_value(rounding=ROUND_UP));   rd = 1
    elif mode == 'down':
        N = int(R.to_integral_value(rounding=ROUND_DOWN)); rd = 0
    else:
        N = int(R.to_integral_value(rounding=ROUND_HALF_UP))
        rd = 1 if N > R else 0

    assert N <= MAX_N, 'Rounded value still overflows'
    return decompose(N, S), True, rd

def decompose(N: int, S: int) -> tuple[int, int]:
    """Split N into (A, r) using Optimal Split S."""
    return N >> S, N & ((1 << S) - 1)

# Rounding mode by account pair group
ROUND_UP_PAIRS   = {0b0001, 0b0011, 0b0101, 0b0111, 0b1000, 0b1100}
ROUND_DOWN_PAIRS = {0b0100, 0b0110, 0b1001, 0b1011}

def rounding_mode(account_pair: int) -> str:
    if account_pair in ROUND_UP_PAIRS:   return 'up'
    if account_pair in ROUND_DOWN_PAIRS: return 'down'
    return 'nearest'
```

---

## Value Range Quick Reference {#value-ranges}

Maximum expressible value at each SF / Decimal Position combination (abbreviated).

| SF | D=0 | D=2 (standard) | D=4 | D=6 |
|---|---|---|---|---|
| × 1 | $33,554,431 | $335,544.31 | $3,355.44 | $33.55 |
| × 100 | $3,355,443,100 | $33,554,431 | $335,544.31 | $3,355.44 |
| × 10,000 | $335,544,310,000 | $3,355,443,100 | $33,554,431 | $335,544.31 |
| × 1,000,000 | $33,554,431,000,000 | $335,544,310,000 | $3,355,443,100 | $33,554,431 |
| × 1,000,000,000 | $33,554,431,000,000,000 | $335,544,310,000,000 | $3,355,443,100,000 | $33,554,431,000 |

**Precision Step** = SF / 10^D. Every integer multiple of this step from 0 to max is exactly reachable.

**Diagonal invariant:** increasing SF by one power of 10 while increasing D by 1 produces identical range and precision. Use the lowest SF that keeps N ≤ 33,554,431.

---

## Journal Entry Format {#journal-format}

```
─────────────────────────────────────────────────────────────────
BITLEDGER JOURNAL ENTRY
Session : {sender_name}  /  {sub_entity_name}  (sub-entity {id})
Batch   : Group {group_sep}  /  Record {n}  /  Currency: {code}
─────────────────────────────────────────────────────────────────
DEBIT    {debit_account:<30}  {ccy} {value:>14,.2f}
CREDIT   {credit_account:<30}  {ccy} {value:>14,.2f}
─────────────────────────────────────────────────────────────────
Description : {narrative}
Status      : Accrued — not yet settled | Settled
Precision   : Exact | Rounded DOWN | Rounded UP
─────────────────────────────────────────────────────────────────
Binary  : {bit_string_with_spaces}
Hex     : {5_hex_bytes_space_separated}
─────────────────────────────────────────────────────────────────
```

---

## Python Data Models {#data-models}

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Layer1Config:
    sender_id:                 int
    sender_name:               str
    sub_entity_id:             int
    sub_entity_name:           str
    protocol_version:          int  = 1
    perm_read:                 bool = True
    perm_write:                bool = True
    perm_correct:              bool = False
    perm_represent:            bool = False
    default_split_order:       int  = 0
    opposing_account_explicit: bool = False
    compound_mode_active:      bool = False
    bitledger_optional:        bool = False
    checksum:          Optional[int] = None

@dataclass
class Layer2Config:
    transmission_type:    int  = 1
    scaling_factor_index: int  = 0
    optimal_split:        int  = 8
    decimal_position:     int  = 2
    enquiry_bell:         bool = False
    acknowledge_bell:     bool = False
    group_sep:            int  = 0
    record_sep:           int  = 0
    file_sep:             int  = 0
    entity_id:            int  = 0
    entity_name:          str  = ''
    currency_code:        int  = 0
    rounding_balance:     int  = 0
    compound_prefix:      int  = 0
    reserved:             int  = 1

@dataclass
class TransactionRecord:
    multiplicand:         int
    multiplier:           int
    rounding_flag:        bool = False
    rounding_dir:         int  = 0
    split_order:          int  = 0
    direction:            int  = 0
    status:               int  = 0
    debit_credit:         int  = 0
    quantity_present:     bool = False
    account_pair:         int  = 0
    bl_direction:         int  = 0
    bl_status:            int  = 0
    completeness:         int  = 0
    extension_flag:       bool = False
    extensions:           list = field(default_factory=list)
    true_value:           float = 0.0
    decoded_value:        float = 0.0
    quantity:             int   = 1
    is_continuation:      bool  = False
    continuation_subtype: int   = 0

@dataclass
class SessionState:
    layer1:             Layer1Config
    layer2:             Layer2Config
    current_sf_index:   int  = 0
    current_currency:   int  = 0
    current_split:      int  = 8
    compound_open:      bool = False
    compound_group_id:  int  = 0
    records_received:   int  = 0
    enquiry_pending:    bool = False
    batch_rounding_sum: float = 0.0
```

---

## Serialisation

```python
def serialise(record: TransactionRecord, S: int = 8) -> int:
    """Pack TransactionRecord to 40-bit integer."""
    # Value block: bits 1–25
    A = record.multiplicand & ((1 << (25-S)) - 1)
    r = record.multiplier   & ((1 << S) - 1)
    value_25 = (A << S) | r

    # Flags: bits 26–32
    flags = (
        (int(record.rounding_flag) << 6) |
        (record.rounding_dir       << 5) |
        (record.split_order        << 4) |
        (record.direction          << 3) |
        (record.status             << 2) |
        (record.debit_credit       << 1) |
        int(record.quantity_present)
    )

    # Validate rounding state
    if not record.rounding_flag and record.rounding_dir:
        raise EncoderError('Invalid: bit26=0 but bit27=1')

    # BitLedger byte: bits 33–40
    bl = (
        ((record.account_pair & 0xF) << 4) |
        (record.bl_direction          << 3) |
        (record.bl_status             << 2) |
        (record.completeness          << 1) |
        int(record.extension_flag)
    )

    return (value_25 << 15) | (flags << 8) | bl

def to_bit_string(n: int) -> str:
    b = format(n, '040b')
    return f'{b[0:17]} {b[17:25]} {b[25:32]} {b[32:36]} {b[36]} {b[37]} {b[38]} {b[39]}'

def to_hex(n: int) -> str:
    return n.to_bytes(5, 'big').hex().upper()
```

---

## Transmission Efficiency

```
100 records, all defaults, no extensions:
  Layer 1:         64 bits  (once per session)
  Layer 2 (short):  8 bits  (1 control byte)
  100 × Layer 3: 4,000 bits
  ─────────────────────────
  Total:         4,072 bits  =  509 bytes

1,000 records across 10 batches:
  Layer 1:              64 bits
  10 × Layer 2 (full): 480 bits
  1,000 × Layer 3:  40,000 bits
  ──────────────────────────────
  Total:            40,544 bits  =  5,068 bytes  =  4.95 KB
```

---

## Critical Implementation Notes

> **NEVER use Python `float` for monetary values.** Always use `decimal.Decimal`. Float arithmetic at values like $4.53 produces 4.529999999... which causes rounding flag errors.

> **Bit 27 must always be 0 when bit 26 is 0.** This is a protocol error state. The encoder must enforce it. Tests must verify it.

> **When bit 32 = 1, Optimal Split is always from `session.current_split`.** Bit 27 does not influence split selection when Quantity Present is active.

> **Compound mode requires both Layer 1 bit 11 = 1 AND Layer 2 compound prefix ≠ 00.** Either alone is insufficient. The encoder must check both before allowing 1111 markers.

---

*BitLedger Protocol Specification v3.0 — See full documentation for complete worked examples, value range tables, CRC-15 implementation, and setup wizard specification.*
