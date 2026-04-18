## TASK-2.06: Implement encoder.py — serialise + Layer 1/2 headers

Goal:                 Implement bit packing (serialise), output formatters, CRC-15
                      computation, and Layer 1/2 header encoding.

Acceptance criteria:  1. serialise(record, S) produces correct 40-bit integer for all
                         spec test record vectors
                      2. to_bit_string(n) groups bits as: 17 | 8 | 7 | 4 | 1 | 1 | 1 | 1
                      3. to_hex(n) returns exactly 10 uppercase hex characters (5 bytes)
                      4. CRC-15 verification: crc15(all_64_bits, 64) == 0 for valid
                         Layer 1 header (encode then verify passes)
                      5. CRC-15 single-bit flip: any 1-bit change to bits 1–49 produces
                         non-zero remainder (error detected)
                      6. Layer 2 short-form (0b01101111) emitted when all Layer 2 values
                         equal session defaults
                      7. account_pair=0b1111 rejected when compound_mode_active=False
                      8. account_pair=0b1111 rejected when compound_prefix=0b00 even if
                         compound_mode_active=True
                      9. python -m pytest tests/test_encoder.py passes (all tests)

Write scope:          bitledger/encoder.py
                      tests/test_encoder.py

Tests required:       python -m pytest tests/test_encoder.py
                      python -m pytest tests/test_roundtrip.py
                      python -m pytest tests/

Rollback:             git checkout bitledger/encoder.py tests/test_encoder.py

Fragility:            HIGH FRAGILITY: encoder.py — Orchestrator approval confirmed 2026-04-14.
                      CONFLICT-005 resolved 2026-04-18 — see `system/logs/decisions.md` and
                      `project/protocol docs/markdown/CONFLICT-005_Explication.md`.

Risk notes:           (Orchestrator) Bit layout is 1-indexed in spec, 0-indexed in Python.
                      Off-by-one errors in the serialise() shift constants are the most
                      likely silent failure mode. Use explicit constants with comments
                      mapping each field to its spec bit position.

Status:               pending
