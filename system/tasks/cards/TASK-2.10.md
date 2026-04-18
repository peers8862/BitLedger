## TASK-2.10: Implement setup_wizard.py

Goal:                 Implement the interactive Layer 1 and Layer 2 profile configuration
                      wizard for the `bitledger setup` command mode.

Acceptance criteria:  1. run_wizard() prompts for all Layer 1 fields in the order
                         specified in BitLedger_Technical_Overview.docx Section on setup:
                         protocol_version, permissions (perm_read/write/correct/represent),
                         default_split_order, opposing_account_explicit,
                         compound_mode_active, bitledger_optional
                      2. run_wizard() then prompts for all Layer 2 fields:
                         transmission_type, optimal_split, decimal_position,
                         compound_prefix
                      3. Each prompt displays: field name, valid range, current/default
                         value, and accepts Enter to keep the default
                      4. Invalid input (out of range, wrong type) re-prompts with an
                         error message — does not crash
                      5. wizard returns (Layer1Config, Layer2Config) on completion
                      6. wizard accepts a pre-populated (Layer1Config, Layer2Config) for
                         edit mode (re-running setup on an existing profile)
                      7. run_wizard() is testable with dependency injection for input
                         (accepts an optional input_fn: Callable[[str], str] parameter
                         defaulting to input())
                      8. python -m pytest tests/test_wizard.py passes (mocked input)

Write scope:          bitledger/setup_wizard.py
                      tests/test_wizard.py

Tests required:       python -m pytest tests/test_wizard.py
                      python -m pytest tests/

Rollback:             git checkout bitledger/setup_wizard.py tests/test_wizard.py

Fragility:            transmission_type=0b00 is INVALID — the wizard must not allow it.
                      Valid values: 0b01, 0b10, 0b11. An off-by-one or missing validation
                      here produces an invalid Layer 2 header with no encoder-level error.
                      compound_prefix is only meaningful when compound_mode_active=True —
                      wizard should warn (not error) if user sets compound_prefix != 0b00
                      when compound_mode_active=False.

Risk notes:           (Orchestrator) Read BitLedger_Technical_Overview.docx for the
                      authoritative field order, valid ranges, and display labels before
                      implementing prompts. The wizard field order must match the spec —
                      users will cross-reference the docx during setup.
                      Use dependency injection for input() so tests can exercise all
                      validation branches without interactive prompts.

Depends on:           TASK-2.03 (models.py), TASK-2.08 (profiles.py)

Status:               pending

