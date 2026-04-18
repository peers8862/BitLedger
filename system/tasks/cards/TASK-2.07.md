## TASK-2.07: Implement decoder.py

Goal:                 Implement the inverse of encoder.py: parse 40-bit integers back
                      into TransactionRecord, validate cross-layer rules, detect CRC-15
                      errors, and handle Layer 2 short-form.

Acceptance criteria:  1. unpack(n) extracts all fields from a 40-bit integer using the
                         same shift constants as serialise() — a roundtrip
                         serialise(unpack(n)) == n for all valid records
                      2. decode_value(A, r, sf_index, decimal_position) reconstructs
                         true_value as Decimal: true_value = (A * (1 << S) + r) / 10^D
                      3. Cross-layer Rule 1: bit 37 == bit 29 (direction mirror) for all
                         records where account_pair != 0b1111
                      4. Cross-layer Rule 2: bit 38 == bit 30 (status mirror) for all
                         records where account_pair != 0b1111
                      5. Rule 3: rounding_flag consistent with r != 0
                      6. CRC-15 check: crc15(all_64_bits, 64) == 0 on valid Layer 1 header
                      7. Layer 2 short-form (0b01101111) decoded as: all Layer 2 values
                         equal current session defaults (no Layer 2 field parse needed)
                      8. DecoderError raised on any rule violation with field name in message
                      9. python -m pytest tests/test_decoder.py passes
                     10. python -m pytest tests/test_roundtrip.py passes

Write scope:          bitledger/decoder.py
                      tests/test_decoder.py
                      tests/test_roundtrip.py

Tests required:       python -m pytest tests/test_decoder.py
                      python -m pytest tests/test_roundtrip.py
                      python -m pytest tests/

Rollback:             git checkout bitledger/decoder.py tests/test_decoder.py tests/test_roundtrip.py

Fragility:            HIGH FRAGILITY: decoder.py — Orchestrator approval confirmed 2026-04-14.
                      Mirror rule suspension for account_pair=1111 must match encoder.py
                      exactly — see CONFLICT-005 resolution in TASK-2.06.
                      The shift constants in unpack() must be the bitwise inverse of
                      serialise() in encoder.py. Any asymmetry silently produces wrong
                      field values that pass unit tests but fail roundtrip.

Risk notes:           (Orchestrator) decode_value reconstructs Decimal from integer fields —
                      never reconstruct via float intermediate. Use
                      Decimal(A * (1 << S) + r) / Decimal(10**D) with integer arithmetic
                      only in the numerator.
                      The rounding_flag bit in the encoded record is informational — the
                      decoder should surface it but cannot re-derive the original rounding
                      direction from the packed bits alone.

Depends on:           TASK-2.03 (models.py), TASK-2.05 (encoder value core),
                      TASK-2.06 (serialise + headers), CONFLICT-005 resolution (done 2026-04-18)

Status:               pending

