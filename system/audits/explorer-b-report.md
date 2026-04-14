# Explorer B Report: Module Coverage Map

Explorer: Explorer B (Claude Sonnet 4.6)
Date: 2026-04-14
Files read:
- `/Users/mp/making/bitledger/TECHNICAL_OVERVIEW.md` (condensed implementation reference, all spec content)
- `/Users/mp/making/bitledger/README.md`
- `/Users/mp/making/bitledger/system/CLAUDE.md`
- `/Users/mp/making/bitledger/system/TASKS.md`
- `/Users/mp/making/bitledger/system/fragility-register.md`
- `/Users/mp/making/bitledger/system/logs/decisions.md`
- `/Users/mp/making/bitledger/system/context/working-conventions.md`
- `/Users/mp/making/bitledger/system/config/test-baseline.yaml`
- `/Users/mp/making/bitledger/system/templates/explorer-b-output.md`
- `/Users/mp/making/bitledger/system/templates/task-card.md`
- `/Users/mp/making/bitledger/system/roles/explorer.md`
- `/Users/mp/making/bitledger/system/workflows/phase1.md`

Note: `BitLedger_Technical_Overview.docx` and `BitLedger_Protocol_v3.docx` could not be read via Bash (access denied). `TECHNICAL_OVERVIEW.md` is the condensed markdown rendition of the Technical Overview and contains all algorithmically-relevant content. The docx files should be read directly when Bash access is available, to verify setup wizard question sequences and simulator design not reproduced in the markdown.

---

## Summary

Total modules: 11
HIGH complexity: 4 (encoder.py, decoder.py, simulator.py, setup_wizard.py)
MEDIUM complexity: 4 (bitledger.py, control.py, formatter.py, models.py)
LOW complexity: 3 (errors.py, currencies.py, profiles.py)
Test files needed: 8
Estimated task cards needed (Phase 2): 14

---

## Module Analysis

### bitledger/models.py

- Complexity: MEDIUM
- Key behaviors:
  - Define `Layer1Config` dataclass with all 13 fields as specified (sender_id, sender_name, sub_entity_id, sub_entity_name, protocol_version, perm_read, perm_write, perm_correct, perm_represent, default_split_order, opposing_account_explicit, compound_mode_active, bitledger_optional, checksum)
  - Define `Layer2Config` dataclass with all 15 fields (transmission_type, scaling_factor_index, optimal_split, decimal_position, enquiry_bell, acknowledge_bell, group_sep, record_sep, file_sep, entity_id, entity_name, currency_code, rounding_balance, compound_prefix, reserved)
  - Define `TransactionRecord` dataclass with all 19 fields including extensions list
  - Define `SessionState` dataclass with all 10 fields tracking mutable session state
  - Define `ControlRecord` dataclass (not shown in markdown but referenced in CLAUDE.md directory map)
  - All fields must carry correct default values matching protocol defaults (split=8, decimal_position=2, transmission_type=1, reserved=1)
  - Field `extensions` on TransactionRecord must use `field(default_factory=list)` — not a mutable default
  - All types must be precise: bool for flags, int for indices and codes, float for monetary decoded values
- Dependencies: `errors.py` (for type validation if any), otherwise none — this is the base module
- Test requirements:
  - Instantiation with all defaults produces correct field values (spot-check all defaults against spec)
  - `Layer1Config` `checksum` defaults to `None` (not 0 — distinguishable from a computed checksum)
  - `Layer2Config` `reserved` field defaults to `1` (spec: bit 48 always 1)
  - `Layer2Config` `transmission_type` defaults to `1` (code 00 is INVALID per spec)
  - `SessionState.current_split` defaults to `8` (matches Layer 2 default optimal_split)
  - Mutation of one `SessionState` instance does not affect another (no shared mutable defaults)
  - `TransactionRecord.extensions` is a new list per instance (factory, not shared)
- Fragility concerns:
  - **ALL other modules import from this file.** A field rename, type change, or default value change silently breaks callers without import errors. The decoder, encoder, formatter, simulator, and wizard all read specific field names.
  - `TransactionRecord.true_value` is `float` but TECHNICAL_OVERVIEW.md warns never to use float for monetary values — this is a latent precision issue if `true_value` is used in arithmetic rather than just display.
  - `ControlRecord` dataclass is in CLAUDE.md directory map but not in the TECHNICAL_OVERVIEW.md Python Data Models section — its exact field layout is unspecified in available markdown. Requires docx for authoritative definition.

---

### bitledger/errors.py

- Complexity: LOW
- Key behaviors:
  - Define `ProtocolError(Exception)` — raised on protocol constraint violations (bit validation failures, CRC mismatch, invalid compound state)
  - Define `EncoderError(Exception)` — raised on encoding failures (overflow, invalid rounding state, invalid field values)
  - Define `DecoderError(Exception)` — raised on decoding failures (high bit set on control record when not expected, malformed records)
  - Define `ProfileError(Exception)` — raised on profile I/O failures (file not found, JSON parse error, permission denied)
  - Each exception class should carry a human-readable message
  - Exception hierarchy should allow catching `ProtocolError` separately from `EncoderError` and `DecoderError` (they model different failure domains)
- Dependencies: none
- Test requirements:
  - Each exception can be raised and caught by its specific type
  - Each exception can be caught by its base `Exception` type
  - Error messages are non-empty strings
  - `ProtocolError` and `EncoderError` are distinct (cannot catch one when the other is raised)
- Fragility concerns: none — pure exception hierarchy, no logic

---

### bitledger/currencies.py

- Complexity: LOW
- Key behaviors:
  - Provide a seeded table of exactly 32 currencies indexed 0–31 (6-bit currency code field supports 64, but seeded set is 32)
  - Each entry carries at minimum: index (int), code (str, e.g. "USD"), name (str), symbol (str)
  - Index 0 must mean "session default" — not a named currency
  - Provide lookup functions: by index → currency dict/object, by code string → index
  - Invalid index or unknown code must raise `ProfileError` or return a sentinel (decision needed; raising is safer for encoding)
  - Currency code 0 in Layer 2 means "inherit from session default" — this semantic must be preserved, not mapped to a real currency at the table level
- Dependencies: `errors.py` (for lookup failures)
- Test requirements:
  - Table has exactly the seeded currencies at expected indices
  - Lookup by index returns correct currency data
  - Lookup by code string is case-insensitive or consistently-cased
  - Index 0 is handled correctly (session default sentinel, not a named currency)
  - Out-of-range index raises appropriate error
  - Unknown currency code raises appropriate error
  - All seeded currencies have non-empty code, name, symbol
- Fragility concerns:
  - The exact 32 currencies and their assigned indices are not specified in available markdown — requires `BitLedger_Technical_Overview.docx` for the authoritative seeded list. If the index assignments change, all encoded records using currency codes become invalid.
  - Index-to-currency mapping must be stable across versions (it is part of the wire format).

---

### bitledger/control.py

- Complexity: MEDIUM
- Key behaviors:
  - `encode_control(type_bits: int, payload: int) -> int` — pack 3-bit type + 4-bit payload into 7-bit value (high bit always 0)
  - `decode_control(byte: int) -> tuple[int, int]` — unpack byte into (type, payload); raise `DecoderError` if high bit is 1
  - Handle all 8 control record types (000–111) with their semantic meanings:
    - Type 000: Scaling Factor change — payload 0–9 = SF index, 10–14 = user-defined, 15 = escape
    - Type 001: Currency change — payload 0–14 = currency index, 15 = escape
    - Type 010: Batch close — payload 0–14 = record count, 15 = escape (next byte carries full count)
    - Type 011: ACK/NACK — bit 5 = 0 for ACK / 1 for NACK, bits 6–8 = batch sequence reference
    - Type 100: Compound group open — payload = record count 1–14
    - Type 101: Optimal Split update — payload = new split value 0–15; reverts at batch close
    - Type 110: Layer 2 short-form — payload 1111 = all defaults
    - Type 111: Reserved — payload must be 1111
  - Escape handling: when payload = 1111 on types 000, 001, 010, next byte provides the full value
  - The `encode_control` formula: `(type_bits << 4) | payload` — note this is a 7-bit result in an 8-bit byte; the high bit is always 0 by the leading-zero rule
- Dependencies: `errors.py`, `models.py` (for ControlRecord if used as return type)
- Test requirements:
  - `encode_control(0b000, 0b0101)` produces correct byte (SF change, index 5)
  - `encode_control(0b010, 0b0000)` produces correct batch-close byte with count 0
  - `decode_control(byte)` where high bit = 1 raises `DecoderError`
  - Round-trip: `decode_control(encode_control(t, p)) == (t, p)` for all valid type/payload combos
  - Type 011 ACK: payload 0b0000 = ACK batch 0; payload 0b1000 = NACK batch 0
  - Type 111 reserved: any payload other than 0b1111 should be handled (spec says "transmit as 1111" — decoder behaviour TBD)
  - Escape payload (0b1111) on types 000, 001, 010 — signals that next byte carries full value
  - Layer 2 short-form detection: type=110, payload=1111
  - Optimal Split update reverts to Layer 2 value at batch close (this is SessionState logic, not pure control.py, but the control module must signal the revert)
- Fragility concerns:
  - The encode formula `(type_bits << 4) | payload` produces a 7-bit value occupying bits 1–7 of the byte; the leading 0 in the high bit position is what distinguishes control records from transaction records (whose first bit is always 1 for valid transactions). If the shift is wrong, control records are misidentified.
  - ACK/NACK encoding is asymmetric: the type field is 011 (3 bits), but the ACK/NACK discriminator is at bit 5 of the full byte (the first payload bit), not a separate type. Misreading which bit carries the ACK/NACK flag is a common implementation error.

---

### bitledger/encoder.py

- Complexity: HIGH
- Key behaviors:
  - `encode_value(true_value: Decimal, sf_index: int, decimal_position: int, account_pair: int) -> tuple` — returns `(A, r, rounding_flag, rounding_dir)` using the algorithm in TECHNICAL_OVERVIEW.md
  - `decompose(N: int, S: int) -> tuple[int, int]` — split N into `(A, r)` using `N >> S` and `N & ((1 << S) - 1)`
  - `rounding_mode(account_pair: int) -> str` — returns 'up', 'down', or 'nearest' based on account pair set membership
  - `serialise(record: TransactionRecord, S: int = 8) -> int` — pack all 40 bits per the layout in TECHNICAL_OVERVIEW.md
  - `to_bit_string(n: int) -> str` — format as spaced 40-bit binary string
  - `to_hex(n: int) -> str` — format as 5-byte uppercase hex
  - Rounding mode sets:
    - ROUND_UP_PAIRS: `{0b0001, 0b0011, 0b0101, 0b0111, 0b1000, 0b1100}` (liability-side entries round up)
    - ROUND_DOWN_PAIRS: `{0b0100, 0b0110, 0b1001, 0b1011}` (income/asset entries round down)
    - All others: ROUND_HALF_UP
  - Must use `decimal.Decimal` throughout — never Python `float` for monetary arithmetic
  - MAX_N = 33,554,431 — assert overflow before encoding
  - Enforce rounding state invariant: bit 26 = 0 implies bit 27 = 0; if violated, raise `EncoderError`
  - Validate that `bl_direction == direction` and `bl_status == status` before serialising (cross-layer mirror constraint)
  - Compound mode: require both `Layer1Config.compound_mode_active == True` AND `Layer2Config.compound_prefix != 0b00` before allowing account_pair = 0b1111
  - Encode Layer 1 header (64 bits) including CRC-15 at bits 50–64
  - Encode Layer 2 header (48 bits) or short-form (8 bits)
- Dependencies: `models.py`, `errors.py`, `currencies.py` (for currency code validation)
- Test requirements:
  - **Spec decode examples (from TECHNICAL_OVERVIEW.md) as test vectors:**
    - `$4.53`, SF=×1, D=2 → N=453, A=1, r=197 (at default split S=8)
    - `$98,765.43`, SF=×1, D=2 → N=9,876,543, A=38,580, r=63
    - 24 units @ $2.49, bit32=1 → A=249, r=24, N=5,976
    - `$2,450,000`, SF=×100, D=2 → N=24,500, A=95, r=180
  - Rounding flag = 0 for exactly representable values
  - Rounding flag = 1 (rounded down) for income account pairs with fractional cents
  - Rounding flag = 1 (rounded up) for liability account pairs with fractional cents
  - `encode_value` with non-Decimal input raises `EncoderError` (type safety)
  - Overflow: N > 33,554,431 raises `EncoderError` with clear message
  - Invalid rounding state (bit26=0, bit27=1) raises `EncoderError`
  - `serialise` produces correct 40-bit integer for known test records
  - `to_bit_string` groups: 17 bits | 8 bits | 7 bits | 4 bits | 1 | 1 | 1 | 1
  - `to_hex` returns exactly 10 uppercase hex chars (5 bytes, no separators)
  - CRC-15 calculation: `crc15(all_64_bits, 64) == 0` for valid Layer 1 header
  - Layer 2 short-form is emitted when all Layer 2 values equal session defaults
  - Compound pair 1111 rejected when compound_mode_active=False
  - Compound pair 1111 rejected when compound_prefix=00 even if compound_mode_active=True
- Fragility concerns:
  - **Bit layout is specified in two different framings (1-indexed in spec, 0-indexed in Python).** Off-by-one errors in bit positions are the most likely silent failure mode.
  - The `serialise` function assembles 40 bits as `(value_25 << 15) | (flags << 8) | bl`. If `flags` is constructed incorrectly (wrong shift offsets within the 7-bit flags block), the rounding/direction/status fields are silently wrong.
  - `decompose(N, S)`: when S changes mid-batch via an Optimal Split update control record, the encoder must use `session.current_split` not the Layer 2 default. Stale split value is a silent correctness error.
  - `float` vs `Decimal`: using `float` for `true_value` will produce wrong rounding flag for values like $4.53 (4.529999...). The spec explicitly warns about this.
  - Rounding mode set membership: the ROUND_UP and ROUND_DOWN sets must be exactly correct. An account pair in the wrong set produces wrong rounding direction flag silently.

---

### bitledger/decoder.py

- Complexity: HIGH
- Key behaviors:
  - `deserialise(raw_40: int, session: SessionState) -> TransactionRecord` — unpack all 40 bits using the same layout as `serialise`
  - Cross-layer validation (mandatory, raises ProtocolError on failure):
    - Rule 1: bit 29 == bit 37 (direction mirror)
    - Rule 2: bit 30 == bit 38 (status mirror)
    - Rule 3: NOT (bit26=0 AND bit27=1) (invalid rounding state)
  - Session validation:
    - Rule 4: CRC-15 over Layer 1 bits 1–49 produces 0 when appended with bits 50–64
    - Rule 5: batch close count == records received (batch integrity)
    - Rule 6: 1111 markers only when compound_prefix != 00 AND Layer 1 bit 11 == 1
  - Reconstruct `real_value` from (N, SF, D) — using `Decimal` arithmetic
  - Handle quantity_present=1: N = A × r (price × quantity), real_value = (N × SF) / 10^D
  - Handle quantity_present=0: N = (A << S) | r, real_value = (N × SF) / 10^D
  - Parse extension bytes when bit 40 = 1; chain if extension byte's bit 8 = 1
  - Decode Layer 1 header (64 bits) with CRC-15 verification
  - Decode Layer 2 header (48 bits) or short-form (8 bits)
  - Rounding balance decode: sign-magnitude, escape code 1000
  - Continuation record handling: when account_pair = 1111, bits 37–38 carry sub-type (not direction/status mirrors)
- Dependencies: `models.py`, `errors.py`, `currencies.py`
- Test requirements:
  - Round-trip: `deserialise(serialise(record)) == record` for all field combinations
  - Each of the 6 error detection rules triggers `ProtocolError` with appropriate message
  - Decode of spec example values matches expected real_value:
    - Raw integer for $4.53 (N=453, SF=1, D=2) → decoded value = Decimal('4.53')
    - Raw integer for 24×$2.49 (N=5976, SF=1, D=2) → decoded value = Decimal('59.76')
  - Extension byte parsing: single extension, chained extensions
  - Short-form Layer 2 detection (byte = 0b01101111)
  - CRC-15 verification: known-good Layer 1 header passes; 1-bit flip fails
  - Batch close count mismatch raises `ProtocolError`
  - Continuation record (1111) when compound_mode_active=False raises `ProtocolError`
  - Rounding balance escape code (1000) is flagged for batch-close control record lookup
  - `deserialise` never returns a record when any validation rule fails
- Fragility concerns:
  - **Wrong decode produces plausible-looking wrong output** — a direction bit in the wrong position produces a transaction that is valid-looking but records the wrong accounting entry.
  - Continuation record (1111) has asymmetric field semantics: bits 37–38 carry sub-type, NOT direction/status mirrors. The cross-layer validation rules must be suspended for continuation records, but ONLY for bits 37–38. Getting this conditional wrong silently accepts malformed continuations or silently rejects valid ones.
  - Quantity reconstruction: when bit 32 = 1, N = A × r. If the decoder reconstructs N via `(A << S) | r` instead, the value is wrong and not obviously so.
  - Extension byte chaining: bit 8 of each extension byte triggers the next. Off-by-one in the chain termination logic either drops or duplicates extension data.

---

### bitledger/formatter.py

- Complexity: MEDIUM
- Key behaviors:
  - Render a `TransactionRecord` + `SessionState` as a journal entry in the exact format specified:
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
  - Determine debit_account and credit_account labels from account_pair code and debit_credit flag
  - Currency display: resolve currency_code → symbol/code string via `currencies.py`
  - Value formatting: `{value:>14,.2f}` — right-aligned, comma-separated thousands, 2 decimal places
  - Status line: `status=0` → "Settled", `status=1` → "Accrued — not yet settled"
  - Precision line: rounding_flag=0 → "Exact"; flag=1 + dir=0 → "Rounded DOWN"; flag=1 + dir=1 → "Rounded UP"
  - Binary line: uses `to_bit_string()` from encoder.py (or duplicate the function here)
  - Hex line: 5 bytes space-separated (not the 10-char run from `to_hex`)
  - Separator line is exactly 65 dashes
  - Sub-entity ID formatted as 2-digit zero-padded integer
  - Group and Record separators formatted as zero-padded integers
- Dependencies: `models.py`, `currencies.py`, `encoder.py` (for `to_bit_string`, `to_hex`)
- Test requirements:
  - Complete journal entry matches exact format from TECHNICAL_OVERVIEW.md spec for the worked example
  - Separator line is exactly 65 characters
  - Debit/credit labels are correct for each of the 14 non-compound account pairs across both direction values
  - Status line text is exact string match
  - Precision line text is exact string match for all three states
  - Value is formatted to 2 decimal places regardless of `decimal_position` in Layer 2 (display is always human-readable)
  - Hex line uses space-separated bytes, not run-together hex
  - Compound continuation records (pair=1111) have special label handling
- Fragility concerns:
  - Account pair label lookup: 16 pairs × 2 directions = 32 label combinations. A label table error produces wrong account names without any validation error.
  - The hex display format (space-separated bytes) is different from `to_hex()` output (no spaces). If `to_hex` is reused directly without reformatting, the output silently fails the spec format.
  - `decimal_position` affects the precision of the decoded value but the display is always `,.2f`. If the formatter applies D-based scaling instead of showing the human-readable value, output is wrong.

---

### bitledger/profiles.py

- Complexity: LOW
- Key behaviors:
  - `save_profile(name: str, layer1: Layer1Config, layer2: Layer2Config) -> None` — write named JSON file to `bitledger/profiles/{name}.json`
  - `load_profile(name: str) -> tuple[Layer1Config, Layer2Config]` — read and deserialise named profile
  - `list_profiles() -> list[str]` — return names of all saved profiles (filenames without `.json`)
  - `delete_profile(name: str) -> None` — remove named profile file
  - Raise `ProfileError` for: file not found on load/delete, JSON parse failure, permission denied, invalid name (path traversal, empty name)
  - Profile directory: `bitledger/profiles/` — must be created if missing
  - JSON serialisation must handle all dataclass fields; use `dataclasses.asdict()` or manual serialisation
  - Profile name sanitisation: reject names containing `/`, `..`, null bytes
  - Do not save `checksum` field as part of a profile (it is session-computed, not a configuration value) — or at minimum note the decision
- Dependencies: `models.py`, `errors.py`
- Test requirements:
  - Save then load round-trip: all Layer1Config and Layer2Config fields survive JSON round-trip with correct types
  - List returns empty list when no profiles exist
  - List returns correct names after saves
  - Delete removes the file and the name disappears from list
  - Load non-existent profile raises `ProfileError`
  - Delete non-existent profile raises `ProfileError`
  - Malformed JSON raises `ProfileError` (not bare `json.JSONDecodeError`)
  - Profile name with `..` raises `ProfileError` (path traversal prevention)
  - Profile name with `/` raises `ProfileError`
  - Profiles directory is auto-created if missing
- Fragility concerns:
  - JSON round-trip of bool fields: Python's `json` module serialises `True/False` correctly, but deserialisation produces Python booleans only if the loader maps them back to the correct field type. If `dataclasses.asdict()` is used for save but manual dict construction for load, type mismatches (int vs bool) can occur silently.
  - Path traversal: `profiles/../../../etc/passwd` must be caught. If name sanitisation is naive (only checks for `/`), `..` alone could still traverse.

---

### bitledger/setup_wizard.py

- Complexity: HIGH
- Key behaviors:
  - Interactive Layer 1 configuration questions (exact sequence from Technical Overview):
    - Sender name (string, required)
    - Sender ID (32-bit integer, required, 1–4,294,967,295)
    - Sub-entity name (string, optional, default blank)
    - Sub-entity ID (5-bit integer, 0–31)
    - Protocol version (1–7, default 1)
    - Permissions: read, write, correct, represent (bool each, defaults: read=True, write=True, correct=False, represent=False)
    - Session defaults: split_order (0 or 1), opposing_account_explicit (bool), compound_mode (bool), bitledger_optional (bool)
  - Interactive Layer 2 configuration questions:
    - Transmission type (1–3, cannot be 0 — code 00 is INVALID)
    - Scaling factor index (0–9, or user-defined 10–14)
    - Optimal split (0–15, default 8)
    - Decimal position (0, 2, 4, or 6 only — not any integer)
    - Enquiry bell / Acknowledge bell (bools)
    - Group/Record/File separator values
    - Entity ID and entity name
    - Currency code (0–63, 0 = session default)
    - Rounding balance (sign-magnitude 4-bit)
    - Compound prefix (0–3)
  - Validate all inputs inline; re-prompt on invalid input rather than raising to caller
  - Offer to save profile by name after configuration
  - Allow profile loading at wizard start ("load existing?")
  - Display summary of configured values before saving
  - `run_wizard() -> tuple[Layer1Config, Layer2Config]` — main entry point
- Dependencies: `models.py`, `profiles.py`, `currencies.py`, `errors.py`
- Test requirements:
  - Wizard produces correct `Layer1Config` and `Layer2Config` for a known input sequence (use stdin mocking)
  - Invalid sender ID (0, negative, > 4,294,967,295) is re-prompted, not raised
  - Invalid decimal_position (e.g. 1, 3, 5) is rejected and re-prompted
  - Transmission type 0 is rejected (INVALID per spec)
  - Compound_prefix != 00 is only accepted when compound_mode = True (or wizard warns)
  - Profile save is called when user opts to save
  - Loaded profile populates defaults for wizard questions
  - CRC-15 is NOT computed in the wizard — it is computed at encode time (wizard builds config, not the encoded header)
- Fragility concerns:
  - The exact wizard question sequence is defined in `BitLedger_Technical_Overview.docx` and is NOT reproduced in `TECHNICAL_OVERVIEW.md`. This is the primary gap in available source material. The sequence must be verified against the docx before implementing.
  - Decimal position must be one of `{0, 2, 4, 6}` — arbitrary even-number validation is not sufficient (8 would be invalid). If validation is `value % 2 == 0`, this is wrong.
  - Interactive input makes this module untestable without stdin mocking. The wizard logic should be separated from `input()` calls to allow unit testing.

---

### bitledger/simulator.py

- Complexity: HIGH
- Key behaviors:
  - `run_simulation(profile_name: str | None, options: dict) -> None` — orchestrate a full sender/receiver session demo
  - Build a `SessionState` from a loaded profile (or defaults if no profile)
  - Encode Layer 1 header (CRC-15 computed)
  - Encode Layer 2 header or short-form
  - Encode a sequence of sample `TransactionRecord` objects demonstrating:
    - Simple flat value transaction
    - Quantity×price transaction (bit 32 = 1)
    - Rounded transaction with rounding flag set
    - Compound transaction (pair=1111, if `--compound` flag active)
    - Control records: SF change, currency change, ACK/NACK, batch close
  - Decode each encoded record back and verify (receiver side)
  - Render each decoded record as a journal entry via `formatter.py`
  - Print binary and hex output for each record
  - Handle `--enquiry` flag: emit enquiry bell, await ACK simulation
  - Handle `--compound` flag: include compound transaction demo
  - Session round-trip must produce zero validation errors
- Dependencies: `models.py`, `encoder.py`, `decoder.py`, `formatter.py`, `control.py`, `profiles.py`, `currencies.py`, `errors.py`
- Test requirements:
  - Simulator runs to completion without exceptions for default configuration
  - Simulator with `--compound` produces compound transaction records with account_pair=1111
  - Simulator with `--enquiry` emits a batch with enquiry_bell=True
  - Each encoded record is decodable (round-trip with zero errors)
  - Simulator output contains the journal entry separator lines
  - Simulator with a named profile loads that profile's Layer1 and Layer2 config
  - Batch close control record is emitted with correct record count
- Fragility concerns:
  - Simulator touches every module — it is the most integration-sensitive component. A bug in any dependency surfaces here but may be attributed to the wrong module.
  - The exact sample transactions used in simulation are specified in the Technical Overview docx (not reproduced in markdown) — the demo output must match the expected worked examples.
  - If simulator constructs `TransactionRecord` objects with hardcoded field values, any change to `models.py` defaults or field names silently breaks the demo.

---

### bitledger/bitledger.py

- Complexity: MEDIUM
- Key behaviors:
  - Parse top-level CLI commands: `setup`, `encode`, `decode`, `simulate`
  - Route to correct module function:
    - `setup` → `setup_wizard.run_wizard()`
    - `encode` → interactive encode flow (calls encoder after wizard-like prompts)
    - `decode <hex_bytes>` → `decoder.deserialise()` + `formatter.format_journal()`
    - `simulate` → `simulator.run_simulation()` with optional `--profile`, `--compound`, `--enquiry` flags
  - Exit codes: 0 = success, 1 = user error (bad input, unknown command), 2 = protocol/internal error
  - `--help` on all commands produces accurate help text
  - Accept hex input for `decode` as space-separated bytes or as a single run (e.g., `04D00518 14` or `04D0051814`)
  - No global mutable state — all state passed through SessionState
- Dependencies: `setup_wizard.py`, `encoder.py`, `decoder.py`, `simulator.py`, `formatter.py`, `profiles.py`, `errors.py`
- Test requirements:
  - `bitledger setup` invokes wizard (integration test with mocked stdin)
  - `bitledger decode 04D00518 14` produces expected journal entry
  - `bitledger simulate` exits 0 on success
  - Unknown command exits 1
  - Protocol error in decode exits 2
  - `--help` produces output containing command names
  - `bitledger decode` with malformed hex exits 1 (user error, not protocol error)
- Fragility concerns:
  - SERIALIZED — one writer at a time. Parallel task edits cause merge conflicts that are hard to resolve.
  - Exit code mapping: user errors (bad hex input) must exit 1, not 2. Protocol errors (CRC failure on decode) must exit 2, not 1. Conflating these makes scripted use unreliable.

---

## Build Order (Dependency Waves)

```
Wave 0 — Foundation (no dependencies):
  errors.py
  currencies.py      (only depends on errors.py)

Wave 1 — Data Models (depends on Wave 0):
  models.py          (imports errors.py if validating; otherwise standalone)

Wave 2 — Core Protocol (depends on Wave 0 + Wave 1):
  control.py         (imports models.py, errors.py)
  encoder.py         (imports models.py, errors.py, currencies.py)
  decoder.py         (imports models.py, errors.py, currencies.py)

Wave 3 — I/O Layer (depends on Wave 0–2):
  profiles.py        (imports models.py, errors.py)
  formatter.py       (imports models.py, currencies.py, encoder.py)

Wave 4 — User Interface (depends on Wave 0–3):
  setup_wizard.py    (imports models.py, profiles.py, currencies.py, errors.py)
  simulator.py       (imports all Wave 0–3 modules)

Wave 5 — Entry Point (depends on all):
  bitledger.py       (imports setup_wizard, encoder, decoder, simulator, formatter, profiles, errors)
```

Note: `currencies.py` is placed in Wave 0 because it has no dependencies beyond `errors.py`. It should be built before Wave 1 to avoid circular imports if `models.py` ever needs to reference currency types.

---

## Test File Map

| Test file | Covers | Key test cases |
|---|---|---|
| `tests/test_models.py` | `models.py` | Default values correct, mutations isolated, factory defaults, field types |
| `tests/test_encoder.py` | `encoder.py` | Spec decode examples as vectors, rounding mode logic, overflow, invalid rounding state, `serialise` bit layout, `to_bit_string`, `to_hex`, CRC-15, Layer 2 short-form |
| `tests/test_decoder.py` | `decoder.py` | All 6 error detection rules, round-trip fidelity, extension byte parsing, continuation record semantics, quantity_present decode path |
| `tests/test_roundtrip.py` | `encoder.py` + `decoder.py` | Exhaustive round-trip: `deserialise(serialise(r, S), session) == r` for sampled field combinations; CRC-15 round-trip |
| `tests/test_control.py` | `control.py` | All 8 type codes, escape payloads, ACK/NACK discrimination, round-trip, high-bit error |
| `tests/test_values.py` | `currencies.py` + value tables | All seeded currencies at correct indices, index 0 = session default, lookup by code, out-of-range, SF/D max-value table spot-checks |
| `tests/test_profiles.py` | `profiles.py` | Save/load round-trip, list, delete, path traversal rejection, missing file error, malformed JSON error |
| `tests/test_formatter.py` | `formatter.py` | Exact output format match, account pair label table, separator length, all precision states, hex display format |

---

## Top Regression-Risk Hotspots

| # | Module | Behavior | Why it's high risk |
|---|---|---|---|
| 1 | `encoder.py` | `serialise()` bit packing: `(value_25 << 15) \| (flags << 8) \| bl` | A single wrong shift constant silently corrupts every encoded record. The three-segment assembly is error-prone and has no unit checksum. |
| 2 | `decoder.py` | Continuation record (account_pair=1111): bits 37–38 carry sub-type, not direction/status mirrors | Cross-layer validation rules must be conditionally bypassed for exactly this case. Getting the condition wrong either silently accepts malformed records or silently rejects valid ones. |
| 3 | `encoder.py` | `rounding_mode(account_pair)` set membership: ROUND_UP_PAIRS vs ROUND_DOWN_PAIRS | An account pair in the wrong set produces wrong rounding direction flag with no error raised. Will cause reconciliation failures in downstream systems. |
| 4 | `decoder.py` | Quantity decode path: when `bit32=1`, use `N = A × r` not `N = (A << S) \| r` | Two valid-looking formulas; one is for flat value, one is for quantity×price. Wrong path produces silently wrong monetary values. |
| 5 | `encoder.py` | `decompose(N, S)` with non-default Optimal Split | When an Optimal Split update control record has fired, `session.current_split` differs from `layer2.optimal_split`. Using the wrong one produces wrong A/r decomposition. |
| 6 | `models.py` | Field names and defaults in `TransactionRecord` | All other modules reference specific field names. Renaming or changing a default (e.g. `quantity=1` to `quantity=0`) breaks callers silently — no import error, just wrong values. |
| 7 | `currencies.py` | Index-to-currency assignment for the seeded 32 currencies | Index values are part of the wire format (Layer 2 bits 36–41). If the table order changes, all previously-encoded records decode to the wrong currency. |
| 8 | `control.py` | ACK/NACK discrimination within Type 011 | The ACK/NACK bit is the first payload bit (bit 5 of the full byte), not a separate type. Confusing the discriminator position causes all ACKs to be read as NACKs. |
| 9 | `formatter.py` | Account pair label lookup for all 16 pairs × 2 directions | 32 label combinations; no runtime check that the label is correct. Wrong account name in journal output is not a crash — it is a silent, user-visible error. |
| 10 | `encoder.py` | `decimal.Decimal` enforcement | Using Python `float` for monetary values like $4.53 produces 4.529999... which sets the rounding flag incorrectly for exact values. No type error is raised; only wrong output is produced. |

---

## Specific Implementation Requirements (from Technical Overview)

The following requirements are detailed enough to serve as acceptance criteria for task cards.

### Layer 1 Header (64 bits)

- Bit 1: always 1 (SOH marker, self-framing)
- Bits 2–4: protocol version, 3-bit integer 0–7
- Bits 5–8: permissions (read, write, correct, represent) — 4 independent booleans
- Bits 9–12: session defaults (split_order, opposing_account_explicit, compound_mode_active, bitledger_optional)
- Bits 13–44: sender_id, 32-bit integer
- Bits 45–49: sub_entity_id, 5-bit integer (0–31)
- Bits 50–64: CRC-15 checksum over bits 1–49 using polynomial x^15 + x + 1 (0x8003)
- CRC-15 verification: `crc15(all_64_bits, 64) == 0` is the valid condition
- CRC-15 algorithm is provided verbatim in TECHNICAL_OVERVIEW.md — implement exactly as shown

### Layer 2 Header (48 bits)

- Bits 1–2: transmission_type, values 01, 10, 11 only — code 00 is INVALID (ensures first byte is never all zeros)
- Bits 3–9: scaling_factor_index, 7-bit (0–127, of which 0–9 are protocol-defined, 10–14 user-defined, 15 = escape)
- Bits 10–13: optimal_split, 4-bit, default 8
- Bits 14–16: decimal_position, values 000=0, 010=2, 100=4, 110=6 only (not arbitrary)
- Bit 17: enquiry_bell
- Bit 18: acknowledge_bell
- Bits 19–22: group_sep, 4-bit (0–15)
- Bits 23–27: record_sep, 5-bit (0–31)
- Bits 28–30: file_sep, 3-bit (0–7)
- Bits 31–35: entity_id, 5-bit (0–31)
- Bits 36–41: currency_code, 6-bit (0–63; 0 = session default)
- Bits 42–45: rounding_balance, sign-magnitude: bit 42 = sign (0=up, 1=down), bits 43–45 = magnitude 0–7; code 1000 = ESCAPE
- Bits 46–47: compound_prefix (00=none, 01=≤3 groups, 10=≤7 groups, 11=unlimited)
- Bit 48: reserved, always 1
- Short-form: if all Layer 2 values equal session defaults, replace 48-bit header with control byte `0 110 1111`

### Layer 3 Transaction Record (40 bits)

- Bits 1–17: multiplicand (17 bits at default split S=8; actual width = 25-S)
- Bits 18–25: multiplier (8 bits at default split S=8; actual width = S)
- Bit 26: rounding_flag (0=exact, 1=rounded)
- Bit 27: rounding_dir (0=down, 1=up) — MUST be 0 when bit 26 = 0
- Bit 28: split_order (0=follow session default, 1=reverse)
- Bit 29: direction (0=In, 1=Out) — MUST EQUAL bit 37
- Bit 30: status (0=Paid, 1=Debt) — MUST EQUAL bit 38
- Bit 31: debit_credit (0=Credit, 1=Debit)
- Bit 32: quantity_present (0=flat value, 1=split active)
- Bits 33–36: account_pair, 4-bit code (0000–1111)
- Bit 37: bl_direction — mirror of bit 29
- Bit 38: bl_status — mirror of bit 30
- Bit 39: completeness (0=Full, 1=Partial — continuation follows)
- Bit 40: extension_flag (0=complete, 1=extension byte follows)

### Value Encoding

- Formula: `N = A × (2^S) + r` where S = optimal_split, A = multiplicand, r = multiplier
- Decode: `real_value = (N × SF) / 10^D`
- MAX_N = 33,554,431 (25 bits)
- When quantity_present=1: A = price, r = quantity, N = A × r (NOT the split formula)
- Decompose: `A = N >> S`, `r = N & ((1 << S) - 1)` — exact, no rounding
- Must use `decimal.Decimal` for all monetary arithmetic

### Value Encoding Test Vectors (from spec)

1. $4.53, SF=×1, D=2 → N=453, A=1, r=197 (S=8)
2. $98,765.43, SF=×1, D=2 → N=9,876,543, A=38,580, r=63 (S=8)
3. 24 units @ $2.49, bit32=1 → A=249, r=24, N=5,976, real=$59.76
4. $2,450,000, SF=×100, D=2 → N=24,500, A=95, r=180 (S=8)

### Error Detection Rules (all 6 must be implemented and tested)

1. `record.direction == record.bl_direction` (bit 29 == bit 37)
2. `record.status == record.bl_status` (bit 30 == bit 38)
3. `NOT (record.rounding_flag == 0 AND record.rounding_dir == 1)` (bit26=0 implies bit27=0)
4. CRC-15 over Layer 1: `crc15(all_64_bits, 64) == 0`
5. Batch close count == records_received
6. account_pair=1111 only when `compound_mode_active=True` AND `compound_prefix != 0b00`

### Compound Transactions

- First record: valid account_pair, `completeness=1` (Partial)
- Continuation record: `account_pair=1111`, bits 37–38 carry sub-type:
  - 00 = Standard linked entry
  - 01 = Correcting entry for preceding record
  - 10 = Reversal of preceding record
  - 11 = Cross-batch continuation
- Continuation `completeness=0` closes the compound group
- Compound group identity = record_sep value at group open time

### Control Record Encoding

- Formula: `encode_control(t, p) = (t << 4) | p` where t = 3-bit type, p = 4-bit payload
- Result is always in range 0–127 (high bit 0 = control record marker)
- `decode_control(b)` raises `DecoderError` if `b & 0x80` (high bit set)
- Escape convention: payload=1111 on types 000/001/010 means next byte carries full parameter

### Rounding Mode by Account Pair

- ROUND_UP (toward higher liability): pairs 0001, 0011, 0101, 0111, 1000, 1100
- ROUND_DOWN (toward lower revenue): pairs 0100, 0110, 1001, 1011
- ROUND_HALF_UP (nearest): all others (0000, 0010, 1010, 1101, 1110)

### Journal Entry Format (exact spec)

- Header separator: exactly 65 dashes (`─` U+2500)
- Session line: `Session : {sender_name}  /  {sub_entity_name}  (sub-entity {id:02d})`
- Batch line: `Batch   : Group {group_sep:02d}  /  Record {n:03d}  /  Currency: {code}`
- DEBIT line: `DEBIT    {account:<30}  {ccy} {value:>14,.2f}`
- CREDIT line: `CREDIT   {credit_account:<30}  {ccy} {value:>14,.2f}`
- Status: `Status      : Accrued — not yet settled` or `Settled`
- Precision: `Precision   : Exact` / `Rounded DOWN` / `Rounded UP`
- Binary line: spaced groups `{17} {8} {7} {4} {1} {1} {1} {1}`
- Hex line: 5 bytes space-separated (e.g. `04 D0 05 18 14`)

---

## Recommended Task Card Structure for Phase 2

Task cards are ordered by dependency wave. Each card has 1–3 files in write scope.

### TASK-2.01: Implement errors.py

Wave: 0
Write scope: `bitledger/errors.py`, `tests/test_models.py` (error import tests)
Acceptance criteria:
1. `ProtocolError`, `EncoderError`, `DecoderError`, `ProfileError` are each a distinct `Exception` subclass
2. Each can be raised with a string message and the message is accessible via `str(e)`
3. They are importable from `bitledger.errors`

---

### TASK-2.02: Implement currencies.py

Wave: 0 (after TASK-2.01)
Write scope: `bitledger/currencies.py`, `tests/test_values.py`
Acceptance criteria:
1. Table contains exactly 32 seeded currencies
2. Index 0 represents session default (not a named currency)
3. Lookup by index returns correct currency dict with code, name, symbol
4. Lookup by code string returns correct index
5. Out-of-range index raises `ProfileError`
6. Unknown code string raises `ProfileError`
Depends on: TASK-2.01

---

### TASK-2.03: Implement models.py

Wave: 1
Write scope: `bitledger/models.py`, `tests/test_models.py`
Acceptance criteria:
1. All four dataclasses (`Layer1Config`, `Layer2Config`, `TransactionRecord`, `SessionState`) instantiate with correct defaults
2. `ControlRecord` dataclass defined
3. `TransactionRecord.extensions` is a fresh list per instance
4. `Layer2Config.reserved` defaults to 1
5. `Layer2Config.transmission_type` defaults to 1 (not 0)
6. `SessionState.current_split` defaults to 8
Depends on: TASK-2.01

---

### TASK-2.04: Implement control.py

Wave: 2
Write scope: `bitledger/control.py`, `tests/test_control.py`
Acceptance criteria:
1. `encode_control(t, p)` produces `(t << 4) | p`, result in 0–127
2. `decode_control(b)` raises `DecoderError` when `b & 0x80`
3. Round-trip for all 8 type codes × all 16 payloads
4. Escape detection (payload=1111) works for types 000, 001, 010
5. ACK/NACK discrimination correct for type 011
Depends on: TASK-2.01, TASK-2.03

---

### TASK-2.05: Implement encoder.py (core value encoding)

Wave: 2 (HIGH FRAGILITY — requires Orchestrator approval)
Write scope: `bitledger/encoder.py`, `tests/test_encoder.py`
Acceptance criteria:
1. All 4 spec decode examples round-trip correctly as test vectors
2. `decompose(N, S)` correct for all N in 0..MAX_N
3. `rounding_mode()` returns correct mode for all 16 account pairs
4. `encode_value()` sets rounding_flag=0 for exact values, rounding_flag=1 with correct direction for rounded values
5. Overflow (N > 33,554,431) raises `EncoderError`
6. Invalid rounding state (bit26=0, bit27=1) raises `EncoderError`
7. `decimal.Decimal` used throughout — float input rejected or warned
Depends on: TASK-2.01, TASK-2.03, TASK-2.02

---

### TASK-2.06: Implement encoder.py (serialise + Layer 1/2 headers)

Wave: 2 (HIGH FRAGILITY — requires Orchestrator approval, separate card from TASK-2.05)
Write scope: `bitledger/encoder.py`, `tests/test_encoder.py`
Acceptance criteria:
1. `serialise(record, S)` produces correct 40-bit integer for spec test vectors
2. `to_bit_string(n)` groups: `17 8 7 4 1 1 1 1`
3. `to_hex(n)` returns 10-char uppercase hex string
4. Layer 1 CRC-15: `crc15(all_64_bits, 64) == 0` for encoded header
5. Layer 2 short-form emitted when all values equal session defaults
6. Compound pair 1111 rejected when compound_mode_active=False or compound_prefix=00
Depends on: TASK-2.05

---

### TASK-2.07: Implement decoder.py

Wave: 2 (HIGH FRAGILITY — requires Orchestrator approval)
Write scope: `bitledger/decoder.py`, `tests/test_decoder.py`, `tests/test_roundtrip.py`
Acceptance criteria:
1. All 6 error detection rules raise `ProtocolError` with correct message
2. `deserialise(serialise(record))` == original record for all field combinations tested
3. Quantity decode path (`bit32=1`): `N = A × r`, not split formula
4. Continuation record (1111): bits 37–38 treated as sub-type, not direction/status mirrors
5. Extension byte chaining terminates correctly
6. CRC-15 verification: 1-bit flip in Layer 1 raises `ProtocolError`
Depends on: TASK-2.05, TASK-2.06

---

### TASK-2.08: Implement profiles.py

Wave: 3
Write scope: `bitledger/profiles.py`, `tests/test_profiles.py`
Acceptance criteria:
1. Save/load round-trip preserves all Layer1Config and Layer2Config field values and types
2. List returns correct names; empty list when no profiles
3. Delete removes file; raises `ProfileError` on missing
4. Path traversal (name with `..` or `/`) raises `ProfileError`
5. Malformed JSON raises `ProfileError` (not bare exception)
6. Profiles directory auto-created if missing
Depends on: TASK-2.01, TASK-2.03

---

### TASK-2.09: Implement formatter.py

Wave: 3
Write scope: `bitledger/formatter.py`, `tests/test_formatter.py`
Acceptance criteria:
1. Output matches exact journal entry format from spec (separator length, spacing, column alignment)
2. All 16 account pairs × 2 directions produce correct debit/credit account labels
3. Status text exact match for both states
4. Precision text exact match for all three states
5. Hex line is space-separated bytes (not run-together)
6. Binary line groups are `17 8 7 4 1 1 1 1`
7. Separator line is exactly 65 `─` (U+2500) characters
Depends on: TASK-2.01, TASK-2.03, TASK-2.02, TASK-2.06

---

### TASK-2.10: Implement setup_wizard.py

Wave: 4
Write scope: `bitledger/setup_wizard.py`, `tests/test_wizard.py`
Note: Exact question sequence must be verified against `BitLedger_Technical_Overview.docx` before this card is dispatched.
Acceptance criteria:
1. `run_wizard()` returns correct `Layer1Config` and `Layer2Config` for known input sequence
2. Invalid inputs are re-prompted, not raised
3. Transmission type 0 rejected
4. Decimal position values other than {0, 2, 4, 6} rejected
5. Compound_prefix != 00 only accepted when compound_mode_active = True (or explicit warning)
6. Profile save/load integration works
Depends on: TASK-2.01, TASK-2.03, TASK-2.08, TASK-2.02

---

### TASK-2.11: Implement simulator.py

Wave: 4
Write scope: `bitledger/simulator.py`, `tests/test_simulator.py`
Acceptance criteria:
1. `run_simulation()` completes without exceptions for default configuration
2. Produces round-trip-valid encoded/decoded records (zero validation errors)
3. Journal entries appear in output for each simulated record
4. `--compound` flag produces at least one compound transaction pair
5. `--enquiry` flag produces batch with enquiry_bell=True
6. Batch close control record emitted with correct count
Depends on: all Wave 0–3 modules

---

### TASK-2.12: Implement bitledger.py entry point

Wave: 5 (SERIALIZED — one writer only)
Write scope: `bitledger/bitledger.py`
Acceptance criteria:
1. `bitledger setup` invokes wizard and exits 0
2. `bitledger encode` invokes encoder flow and exits 0 on success
3. `bitledger decode <hex>` produces journal entry and exits 0
4. `bitledger simulate` runs simulator and exits 0
5. Unknown command exits 1
6. Protocol error during decode exits 2
7. `--help` on each command describes actual behavior
Depends on: all Wave 0–4 modules

---

### TASK-2.13: Complete test suite validation (test_roundtrip.py + full suite run)

Wave: 6
Write scope: `tests/test_roundtrip.py`
Acceptance criteria:
1. Round-trip tests for all 16 account pairs pass
2. Round-trip with non-default optimal_split (S=4, S=12) passes
3. Round-trip with compound transactions passes
4. `python -m pytest tests/` exits 0 with no failures or errors
Depends on: TASK-2.07 and all prior implementation tasks

---

### TASK-2.14: Read BitLedger_Technical_Overview.docx and BitLedger_Protocol_v3.docx

Wave: Pre-2.10 (blocking for setup_wizard and simulator)
Write scope: none (read-only)
Note: This is a prerequisite research task, not an implementation task. The docx files contain setup wizard question sequences and simulator worked examples not reproduced in TECHNICAL_OVERVIEW.md. Bash access required to extract XML. Findings should update TASKS.md before TASK-2.10 is dispatched.

---

*End of Explorer B Report*
