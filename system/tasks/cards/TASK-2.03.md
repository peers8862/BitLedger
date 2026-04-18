## TASK-2.03: Implement models.py

Goal:                 Define the four typed dataclasses (Layer1Config, Layer2Config,
                      TransactionRecord, SessionState) and ControlRecord that form the
                      data contract for all other modules.

Acceptance criteria:  1. Layer1Config instantiates with all 13 fields at correct defaults:
                         protocol_version=1, perm_read=True, perm_write=True,
                         perm_correct=False, perm_represent=False, default_split_order=0,
                         opposing_account_explicit=False, compound_mode_active=False,
                         bitledger_optional=False, checksum=None
                      2. Layer2Config instantiates with correct defaults:
                         transmission_type=1 (NOT 0 — 00 is INVALID),
                         optimal_split=8, decimal_position=2, reserved=1,
                         compound_prefix=0
                      3. SessionState.current_split defaults to 8
                      4. TransactionRecord.extensions is a fresh list per instance
                         (field(default_factory=list) — not a shared mutable default)
                      5. Mutating one SessionState instance does not affect another
                      6. ControlRecord dataclass defined with appropriate fields
                      7. TransactionRecord.true_value typed as Decimal (not float) —
                         see fragility note
                      8. python -m pytest tests/test_models.py passes

Write scope:          bitledger/models.py
                      tests/test_models.py

Tests required:       python -m pytest tests/test_models.py
                      python -m pytest tests/

Rollback:             git checkout bitledger/models.py tests/test_models.py

Fragility:            HIGH FRAGILITY: models.py — Orchestrator approval confirmed 2026-04-14.
                      All 11 other modules import from this file. A field rename, type
                      change, or default value change silently breaks callers with no
                      import error — just wrong values. Any post-Task-2.03 change to
                      field names or defaults requires Orchestrator approval and a new
                      task card.

Risk notes:           (Orchestrator) The spec data model specifies TransactionRecord.true_value
                      as float, but the spec also prohibits float for monetary arithmetic.
                      Decision: type true_value as decimal.Decimal to prevent precision
                      errors. This is an override of the spec's field type — log this
                      decision in system/logs/decisions.md.
                      ControlRecord field layout: read BitLedger_Technical_Overview.docx
                      for the authoritative definition if not in TECHNICAL_OVERVIEW.md.

Status:               pending
