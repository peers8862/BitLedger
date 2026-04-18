## TASK-2.09: Implement formatter.py

Goal:                 Implement output formatters that render encoded records and decoded
                      transactions in human-readable form for the CLI.

Acceptance criteria:  1. format_binary(n) returns a string grouping the 40 bits as
                         spec section headers dictate: "17 | 8 | 7 | 4 | 1 | 1 | 1 | 1"
                         (same grouping as to_bit_string in encoder.py)
                      2. format_hex(n) returns 10 uppercase hex characters with "0x" prefix
                      3. format_journal(record: TransactionRecord, session: SessionState)
                         returns a multi-line human-readable journal entry with:
                         - debit/credit labels derived from direction bit
                         - amount in decimal with currency symbol
                         - rounding flag annotation if rounding_flag == 1
                         - account pair label
                      4. format_layer1_header(config: Layer1Config) returns a readable
                         summary of session configuration fields
                      5. format_layer2_header(config: Layer2Config) returns a readable
                         summary of batch configuration fields
                      6. All formatters return str (never print directly)
                      7. python -m pytest tests/test_formatter.py passes

Write scope:          bitledger/formatter.py
                      tests/test_formatter.py

Tests required:       python -m pytest tests/test_formatter.py
                      python -m pytest tests/

Rollback:             git checkout bitledger/formatter.py tests/test_formatter.py

Fragility:            format_journal must use currencies.py for currency symbol lookup,
                      not hardcoded strings. Decimal formatting must not reintroduce
                      float — use Decimal.quantize() for display rounding.

Risk notes:           (Orchestrator) The journal entry format is not specified in the
                      docx — design it to be readable for double-entry bookkeeping
                      practitioners. Debit/credit convention: bit 29 = 1 means debit
                      (Out from sender perspective). Include spec bit positions in
                      inline comments for future maintainers.

Depends on:           TASK-2.03 (models.py), TASK-2.02 (currencies.py),
                      TASK-2.05 (encoder value core — for field semantics)

Status:               pending

