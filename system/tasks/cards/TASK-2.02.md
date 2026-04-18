## TASK-2.02: Implement currencies.py

Goal:                 Provide the seeded currency table and lookup functions so that
                      encoder, decoder, wizard, and formatter can resolve currency codes.

Acceptance criteria:  1. Table has exactly 32 entries: index 0 = session default sentinel
                         (not a named currency), indices 1–31 = standard world currencies
                      2. Each named entry has non-empty fields: index (int), code (str, e.g.
                         "USD"), name (str), symbol (str)
                      3. lookup_by_index(0) returns the session default sentinel
                      4. lookup_by_index(n) for n in 1–31 returns correct currency dict
                      5. lookup_by_code("USD") returns correct index (case-insensitive)
                      6. lookup_by_index(out_of_range) raises ProfileError
                      7. lookup_by_code("INVALID") raises ProfileError
                      8. python -m pytest tests/test_values.py passes

Write scope:          bitledger/currencies.py
                      tests/test_values.py

Tests required:       python -m pytest tests/test_values.py
                      python -m pytest tests/

Rollback:             git checkout bitledger/currencies.py tests/test_values.py

Fragility:            The index-to-currency assignment is wire-format data. The 31 standard
                      currency indices must match the sequence defined in
                      BitLedger_Technical_Overview.docx Section on currencies.py.
                      Do not invent the order — read the docx for the canonical list.
                      Changing the order after any records are encoded invalidates them.

Risk notes:           (Orchestrator) The authoritative currency list is in
                      BitLedger_Technical_Overview.docx. Use the Python XML extraction
                      method to read it if needed. Codes 32–62 are user-defined
                      (pass-through); code 63 = multi-currency batch sentinel.
                      Do not validate codes 32–63 — encoder/decoder pass them through.

Status:               pending
