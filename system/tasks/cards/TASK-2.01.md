## TASK-2.01: Implement errors.py

Goal:                 Define the four typed exception classes used throughout the project
                      so all other modules can import and raise them correctly.

Acceptance criteria:  1. ProtocolError, EncoderError, DecoderError, ProfileError are each
                         a distinct subclass of Exception
                      2. Each can be raised with a string message: `raise ProtocolError("msg")`
                         and the message is accessible via str(e)
                      3. All four are importable from `bitledger.errors`
                      4. ProtocolError cannot be caught by except EncoderError (distinct types)
                      5. python -m pytest tests/ passes

Write scope:          bitledger/errors.py
                      tests/test_models.py (create with error import tests)

Tests required:       python -m pytest tests/test_models.py
                      python -m pytest tests/

Rollback:             git checkout bitledger/errors.py tests/test_models.py

Fragility:            None

Risk notes:           (Orchestrator) No logic in this file — pure exception hierarchy.
                      Keep it minimal. Do not add fields, codes, or extra attributes
                      beyond what is needed to carry a message string.

Status:               pending
