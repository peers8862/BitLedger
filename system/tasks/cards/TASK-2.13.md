## TASK-2.13: Complete test suite — edge cases and integration

Goal:                 Fill remaining test coverage gaps: overflow/underflow, malformed
                      input, cross-layer rule violations, CRC bit-flip detection, and
                      full roundtrip fidelity for all spec test vectors.

Acceptance criteria:  1. tests/test_values.py: all 4 spec test vectors from TASK-2.05
                         pass with exact Decimal equality (no float comparison)
                      2. tests/test_roundtrip.py: encode → decode roundtrip for
                         minimum, maximum, and mid-range values in all SF indices 0–17
                      3. tests/test_encoder.py: CRC-15 single-bit flip test — flip each
                         of bits 1–49 in a valid Layer 1 header; all 49 produce
                         non-zero remainder
                      4. tests/test_decoder.py: all 6 error detection rules tested
                         with explicit rule-violating inputs
                      5. tests/test_values.py: overflow test — N > 33,554,431 raises
                         EncoderError
                      6. tests/test_control.py: all 8 type codes round-trip; escape
                         payload detection for types 000/001/010; ACK/NACK discrimination
                      7. tests/test_profiles.py: default profile protection test;
                         missing profile raises ProfileError
                      8. No test uses assertEqual on float — all monetary comparisons
                         use Decimal or integer assertions
                      9. python -m pytest tests/ --tb=short shows 0 failures, 0 errors

Write scope:          tests/test_values.py (extend)
                      tests/test_roundtrip.py (extend)
                      tests/test_encoder.py (extend)
                      tests/test_decoder.py (extend)
                      Any other test file needing gap coverage

Tests required:       python -m pytest tests/ --tb=short

Rollback:             git checkout tests/

Fragility:            The CRC-15 bit-flip test (criterion 3) is the most likely false-
                      negative: if the test only flips one bit and happens to pick a bit
                      that the CRC polynomial doesn't protect (which should be impossible
                      for a correctly implemented CRC), the test will pass even with a
                      wrong polynomial. Test ALL 49 bits to be safe.
                      Do not add assert True or skip any criterion — Verifier will flag
                      incomplete coverage as a Gate B violation.

Risk notes:           (Orchestrator) This task is the final quality gate before
                      TASK-2.12 (CLI entry point). A passing suite here is the merge
                      prerequisite for bitledger.py. Any test added here that reveals
                      a bug in a prior module must be fixed in that module's task card
                      before this task can be marked complete.

Depends on:           All implementation tasks TASK-2.01 through TASK-2.11

Status:               pending

