## TASK-2.04: Implement control.py

Goal:                 Implement 8-bit control record encoding/decoding and all eight
                      control record types, including escape payload handling.

Acceptance criteria:  1. encode_control(t, p) returns (t << 4) | p, result in range 0–127
                      2. decode_control(b) raises DecoderError when b & 0x80 (high bit set)
                      3. Round-trip: decode_control(encode_control(t, p)) == (t, p)
                         for all valid 3-bit types × 4-bit payloads
                      4. Escape detection: payload=0b1111 on types 000, 001, 010 signals
                         that next byte carries full parameter value
                      5. ACK/NACK discrimination correct for type 011:
                         payload bit 0 (first payload bit) = 0 → ACK, 1 → NACK
                      6. Layer 2 short-form detected: type=110, payload=0b1111
                      7. All 8 type codes handled without error
                      8. python -m pytest tests/test_control.py passes

Write scope:          bitledger/control.py
                      tests/test_control.py

Tests required:       python -m pytest tests/test_control.py
                      python -m pytest tests/

Rollback:             git checkout bitledger/control.py tests/test_control.py

Fragility:            The leading-0 bit is what distinguishes control records from
                      transaction records (transaction records start with 1 in a valid
                      session). If encode_control produces a value with bit 7 set (≥128),
                      the record will be misidentified by the decoder.

Risk notes:           (Orchestrator) ACK/NACK: type field is 011, but the discriminator
                      is the first payload bit (bit 5 of the full byte), not a separate
                      type. This is a common implementation error — make it explicit in
                      tests.

Status:               pending
