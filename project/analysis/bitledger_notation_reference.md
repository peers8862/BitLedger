# BitLedger notation and symbols

**Purpose:** standalone symbol table for formulas in value encoding, CLI planning, and Layer 1–3 references.  
**Companion:** narrative and design rationale live in [`value_encoding_scaling_factor_reference.md`](./value_encoding_scaling_factor_reference.md).

---

## 1. Monetary value and decode

| Symbol | Meaning | Code / wire |
|--------|---------|----------------|
| \(v\) | True economic amount (natural units, e.g. dollars) at encode input | `true_value`, `--amount` → `Decimal` |
| \(\hat{v}\) | Amount implied by limbs after decode (wire value) | `decode_value` result |
| \(\Delta\) | Typed minus decoded: \(v - \hat{v}\) (CLI “delta”) | `delta` in `make` / `check-amount` reports |
| \(D\) | Decimal scale exponent: decode divides by \(10^{D}\) | Wire `decimal_position` for codes `000`–`110`; `_wire_dp_to_d` / `decode_value` use same integer \(D\) |

---

## 2. Scaling factor ladder

| Symbol | Meaning | Code / wire |
|--------|---------|----------------|
| \(k\) | Scaling factor **index** on the ladder | `sf_index`, `scaling_factor_index`, `--sf` |
| \(K\) | Count of table entries (\(k \in \{0,\ldots,K-1\}\)) | `len(SCALING_FACTORS)`; here \(K=128\) |
| \(\textsf{SF}_k\) | Monetary scale at index \(k\): \(\textsf{SF}_k = 10^{k}\) | `SCALING_FACTORS[k]` |
| \(\textsf{SF}\) | Same as \(\textsf{SF}_k\) when \(k\) is fixed | `SF` in local variables |
| \(k_{\min}, k_{\max}\) | User / CLI search interval for auto-SF | `--min-sf`, `--max-sf`; `lo`, `hi` in `find_smallest_sf` |

---

## 3. Integer pipeline (non-quantity path)

| Symbol | Meaning | Code / wire |
|--------|---------|----------------|
| \(R\) or \(R_k(v)\) | Scaled value before rounding to integer: \(v \cdot 10^{D-k}\) | `R` in CLI printouts; `true_value * 10**D / SF` |
| \(N\) | Stored **wire integer** (25-bit semantic range) | Composed from `A`, `r`, `S`; checked \(\le 33\,554\,431\) |
| \(N_{\max}\) | Maximum wire integer: \(2^{25}-1 = 33\,554\,431\) | Hard cap in `encode_value` / `decompose` |
| \(S\) | **Optimal split**: low part width in bits | `optimal_split` (Layer 2); `S` in `encode_value` |
| \(A\) | **Multiplicand**: high part \(N \gg S\) | `multiplicand`, `TransactionRecord.multiplicand` |
| \(r\) | **Multiplier** / remainder: low \(S\) bits of \(N\) | `multiplier`, `TransactionRecord.multiplier` |
| \(q\) | Quantity flag; when true, \(N = A \cdot r\) at decode | `quantity_present` |

**Decomposition (non-quantity):** \(N = A \cdot 2^{S} + r\), \(0 \le r < 2^{S}\).

**Quantity path decode:** \(N = A \cdot r\) when `quantity_present` is true.

---

## 4. Rounding disclosure (Layer 3 bits 26–27)

| Symbol | Meaning | Code / wire |
|--------|---------|----------------|
| \(\textsf{rf}\) | **Rounding flag:** \(1\) iff \(R\) was not an integer and \(N\) was rounded | `rounding_flag` |
| \(\textsf{rd}\) | **Rounding direction** bit (interpret with \(\textsf{rf}\)) | `rounding_dir` |
| \(p\) | **Account pair** nibble \(0\)–\(15\); selects rounding mode | `account_pair` |
| \(\lfloor x \rfloor, \lceil x \rceil\) | Floor, ceiling of \(x\) | `ROUND_DOWN`, `ROUND_UP` (`Decimal`) |
| \(\mathrm{nint}(x)\) | Half-up rounding of \(x\) to integer | `ROUND_HALF_UP` (“nearest”) |

---

## 5. SF search policies (CLI)

| Name | Meaning |
|------|---------|
| **L** | **Legacy SF search:** smallest \(k\) in ascending order with any successful `encode_value` |
| **E** | **Exact-first SF search:** smallest \(k\) with \(\textsf{rf}=0\) if any; else same as **L** |

---

## 6. Layer and record framing

| Symbol | Meaning | Code / wire |
|--------|---------|----------------|
| \(L1, L2, L3\) | Layer 1 session, Layer 2 transmission/currency, Layer 3 posting record | `Layer1Config`, `Layer2Config`, `TransactionRecord` |
| 40-bit record | Packed transaction / value record | `serialise` → five big-endian bytes |
| \(n_{40}\) | 40-bit record as integer | `n40` in tests / journal |
| 64-bit codeword | Layer 1 MSB-first codeword including CRC | `codeword64` in CRC helpers |
| \(\mathrm{CRC}_{15}\) | 15-bit CRC over 49-bit payload | `crc15_remainder_payload49`, `CRC15_POLY` |
| payload\(_{49}\) | Bits 1–49 of Layer 1 payload as integer | `pack_layer1_payload49` |

---

## 7. Layer 2 rounding balance (wire)

| Name | Meaning | Code / wire |
|------|---------|-------------|
| `rounding_balance` | 4-bit Layer 2 field (sign + magnitude semantics per protocol overview) | `Layer2Config.rounding_balance`, packed in L2 |

This is **session configuration on the wire**, not a running log of per-posting deltas.

---

## 8. Sets (rounding mode lookup)

| Name | Meaning |
|------|---------|
| `ROUND_UP_PAIRS` | Account pair nibbles that use **round up** when \(R \notin \mathbb{Z}\) |
| `ROUND_DOWN_PAIRS` | Nibbles that use **round down** |
| *(complement)* | Remaining nibbles use **half-up** (“nearest”) |

---

## 9. Rounding observability (CLI)

**Scale and residuals:** The CLI can append a **rounding report** block listing, per observation, **SF index \(k\)**, **decimal wire `dp`**, **`rf` / `rd`**, typed amount (when known), wire amount, and **\(\Delta = \text{typed} - \text{wire}\)**. The footer gives **count exact vs non-exact**, and when \(\Delta\) is known: **sum**, **mean**, and counts of \(\Delta \lessgtr 0\).

| Command | Flags | Notes |
|---------|-------|--------|
| `encode` | `--rounding-report` (with `--amount`) | Always prints \(\Delta\) for that encode (works with `--quiet`). |
| `decode` | `--rounding-report` [, `--compare-amount DECIMAL`] | Without compare: wire + scale only; \(\Delta\) / sum / mean need **`--compare-amount`**. |
| `make`, `check-amount`, `suggest-sf` | `--rounding-report` | Same one-row aggregate as encode-from-plan; **`make --json --rounding-report`** adds **`rounding_observation`** to JSON (no human “Rounding report” line). |
| `make` family | `--quantity-present` **0** or **1** | Aligns suggested **`encode`**, JSON **`quantity_present`**, and decode used in **`make`** / **`check-amount`** / rounding row with **\(N=A\times r\)** when **1**. |

**`SessionState.batch_rounding_sum`:** on **`encode`** with **`--amount`** and **`--rounding-report`**, when output is **not** **`--quiet`**, the session object used for the journal gets **`batch_rounding_sum +=`** (typed − wire) for that record. Quiet **`encode`** does not mutate it.

**Still out of scope:** no CSV/DB log, no multi-record `.bl` scan, histograms by \(k\) across a corpus.

Implementation: `bitledger/rounding_report.py` and CLI wiring in `cli.py` / `cli_make.py`.
