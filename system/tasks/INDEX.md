# Task Index — BitLedger

Scannable manifest of all task cards. Updated by Orchestrator when cards are created or status changes.

Cards live in `tasks/cards/TASK-XXX.md`.

---

## Status Key

| Status | Meaning |
|---|---|
| `pending` | Card complete; not started |
| `in-progress` | Builder actively working |
| `blocked` | Waiting on dependency |
| `in-review` | Verifier running |
| `complete` | Signed off and closed |

---

## Task Cards

| ID | Title | Wave | Status |
|---|---|---|---|
| TASK-2.00 | Python project scaffolding | 0 | pending |
| TASK-2.01 | errors.py — 4 exception classes | 0 | pending |
| TASK-2.14 | Prereq — docx data extraction | 0 | pending |
| TASK-2.02 | currencies.py — 32-entry table | 1 | pending |
| TASK-2.03 | models.py — dataclasses (HIGH FRAGILITY) | 1 | pending |
| TASK-2.04 | control.py — 8-bit control records | 2 | pending |
| TASK-2.05 | encoder.py — value encoding core | 2 | pending |
| TASK-2.06 | encoder.py — serialise + headers | 2 | pending |
| TASK-2.07 | decoder.py | 2 | pending |
| TASK-2.08 | profiles.py — JSON session persistence | 3 | pending |
| TASK-2.09 | formatter.py — ASCII/hex output | 3 | pending |
| TASK-2.10 | setup_wizard.py — interactive Layer 1/2 config | 4 | pending |
| TASK-2.11 | simulator.py — full encode/decode loop | 4 | pending |
| TASK-2.12 | bitledger.py — CLI entry point (SERIALIZED) | 5 | pending |
| TASK-2.13 | Complete test suite — edge cases + integration | 5 | pending |

---

## Blockers

- **CONFLICT-005**: **Resolved 2026-04-18** — logged in `system/logs/decisions.md`. Bits 37–38 carry **sub-type** when `account_pair=1111`; Rules 1–2 **suspended** for that case only; mirrors enforced for all other pairs. Explication: `project/protocol docs/markdown/CONFLICT-005_Explication.md`. TASK-2.06 / TASK-2.07 unblocked pending implementation.

- **TASK-2.14 prerequisite**: Run before TASK-2.02 (currency order) and TASK-2.10 (wizard field sequence).
