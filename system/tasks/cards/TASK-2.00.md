## TASK-2.00: Python project scaffolding

Goal:                 Create the project directory structure, pyproject.toml, and empty
                      module files so all subsequent Builder tasks have a valid Python
                      package to work within.

Acceptance criteria:  1. `bitledger/` directory exists with `__init__.py`
                      2. `tests/` directory exists with `__init__.py` and `conftest.py`
                      3. `bitledger/profiles/` directory exists
                      4. All 11 module files exist as empty stubs:
                         bitledger.py, encoder.py, decoder.py, setup_wizard.py,
                         simulator.py, formatter.py, models.py, profiles.py,
                         currencies.py, control.py, errors.py
                      5. `pyproject.toml` exists with project name, Python 3.10+
                         requirement, and pytest as test dependency
                      6. `python -m pytest tests/` exits 0 (no tests yet = pass)

Write scope:          bitledger/__init__.py
                      bitledger/bitledger.py (stub only)
                      bitledger/encoder.py (stub only)
                      bitledger/decoder.py (stub only)
                      bitledger/setup_wizard.py (stub only)
                      bitledger/simulator.py (stub only)
                      bitledger/formatter.py (stub only)
                      bitledger/models.py (stub only)
                      bitledger/profiles.py (stub only)
                      bitledger/currencies.py (stub only)
                      bitledger/control.py (stub only)
                      bitledger/errors.py (stub only)
                      bitledger/profiles/.gitkeep
                      tests/__init__.py
                      tests/conftest.py
                      pyproject.toml

Tests required:       python -m pytest tests/
                      Manual: python -c "import bitledger" exits 0

Rollback:             rm -rf bitledger/ tests/ pyproject.toml

Fragility:            None

Risk notes:           (Orchestrator) Stub files must contain only a module-level docstring
                      and a pass statement — no placeholder logic. The actual implementations
                      come in subsequent task cards.

Status:               pending
