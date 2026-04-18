## TASK-2.05: Implement encoder.py — value encoding core

Goal:                 Implement the value encoding functions: decompose, rounding mode
                      lookup, and encode_value. These are the numerically precise core
                      of the encoder — no bit packing yet.

Acceptance criteria:  1. decompose(N, S) returns (A, r) = (N >> S, N & ((1 << S) - 1))
                         for all N in 0..33,554,431 and all S in 0..17
                      2. rounding_mode(account_pair) returns:
                         'up' for pairs in {0001, 0011, 0101, 0111, 1000, 1100}
                         'down' for pairs in {0100, 0110, 1001, 1011}
                         'nearest' for all others
                      3. encode_value(true_value, sf_index, decimal_position, account_pair)
                         returns (A, r, rounding_flag, rounding_dir) using Decimal arithmetic
                      4. All 4 spec test vectors pass:
                         - $4.53, SF=×1, D=2 → N=453, A=1, r=197
                         - $98,765.43, SF=×1, D=2 → N=9,876,543, A=38,580, r=63
                         - 24 units @ $2.49 (quantity mode) → A=249, r=24, N=5,976
                         - $2,450,000, SF=×100, D=2 → N=24,500, A=95, r=180
                      5. Overflow: N > 33,554,431 raises EncoderError
                      6. Float input raises EncoderError or is converted to Decimal safely
                      7. rounding_flag=0 for exactly representable values
                      8. python -m pytest tests/test_encoder.py passes (value tests only)

Write scope:          bitledger/encoder.py
                      tests/test_encoder.py

Tests required:       python -m pytest tests/test_encoder.py
                      python -m pytest tests/

Rollback:             git checkout bitledger/encoder.py tests/test_encoder.py

Fragility:            HIGH FRAGILITY: encoder.py — Orchestrator approval confirmed 2026-04-14.
                      Using Python float instead of Decimal for $4.53 produces 4.529999...
                      which incorrectly sets rounding_flag=1 for an exact value.
                      NEVER use float for monetary arithmetic.

Risk notes:           (Orchestrator) The rounding mode sets are specified in
                      TECHNICAL_OVERVIEW.md. Verify the sets are exactly correct before
                      committing — an account pair in the wrong set produces wrong
                      rounding direction with no error raised.

Status:               pending
