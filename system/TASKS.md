# TASKS.md — BitLedger

Canonical task board. Orchestrator-managed. Single source of truth for all open work.

Task cards live in `tasks/cards/`. This file is the scannable index.

---

## Active Tasks

<!-- Orchestrator appends new task entries here -->

---

## Completed Tasks

<!-- Completed tasks move here after Verifier sign-off and Docs closure -->

---

## Backlog / Not Yet Scheduled

- Phase 1: Explorer A — audit protocol spec against Technical Overview for contradictions
- Phase 1: Explorer B — map all 11 source modules to acceptance criteria
- Phase 1: Author task cards for all Phase 2 implementation work

---

## Dependency Waves

```
Wave 0 (setup):  CLAUDE.md, project scaffold, git init
Wave 1 (models): models.py, errors.py, currencies.py
Wave 2 (core):   encoder.py, decoder.py, control.py
Wave 3 (io):     profiles.py, formatter.py
Wave 4 (ui):     setup_wizard.py, simulator.py
Wave 5 (entry):  bitledger.py (entry point wiring)
Wave 6 (tests):  test_encoder, test_decoder, test_roundtrip, test_control, test_values
```
