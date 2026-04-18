# TASKS.md — BitLedger

Canonical task board. Orchestrator-managed.

---

## Phase 1 Status

- [x] TASK-1.1: Deploy root CLAUDE.md ✓
- [x] TASK-1.3a: Explorer A — spec/docs drift audit ✓ (report: system/audits/explorer-a-report.md)
- [x] TASK-1.3b: Explorer B — module coverage map ✓ (report: system/audits/explorer-b-report.md)
- [ ] TASK-1.4: Build canonical TASKS.md (this file) — in-progress
- [x] TASK-1.5: Git init + artifact hygiene ✓

**CONFLICT-005:** Resolved 2026-04-18 — see `system/logs/decisions.md` and `project/protocol docs/markdown/CONFLICT-005_Explication.md`. TASK-2.06 / TASK-2.07 may proceed.

**TASK-1.5 closed** — Git init + artifact hygiene complete (2026-04-18).

---

## Active Tasks

<!-- New tasks appended here by blctl new-task -->

---

## Phase 2 — Implementation

**Phase 2 note (2026-04-18):** All Wave 0–6 tasks implemented via Cursor sessions outside the formal task model. Test suite passes (193 tests). CONFLICT-005 resolved; TASK-2.06 and TASK-2.07 covered by existing test suite. Formal Verifier pass for 2.06/2.07 deferred to upcoming test cycle. TASK-1.5 closed.

Task cards in `tasks/cards/`. Build in wave order.

| ID | Title | Wave | Status | Fragility |
|---|---|---|---|---|
| TASK-2.00 | Python project scaffolding | 0 | pending | none |
| TASK-2.01 | Implement errors.py | 0 | pending | none |
| TASK-2.02 | Implement currencies.py | 0 | pending | none |
| TASK-2.03 | Implement models.py | 1 | pending | HIGH |
| TASK-2.04 | Implement control.py | 2 | pending | none |
| TASK-2.05 | Implement encoder.py — value encoding core | 2 | pending | HIGH |
| TASK-2.06 | Implement encoder.py — serialise + headers | 2 | **BLOCKED** on CONFLICT-005 | HIGH |
| TASK-2.07 | Implement decoder.py | 2 | **BLOCKED** on CONFLICT-005 | HIGH |
| TASK-2.08 | Implement profiles.py | 3 | pending | none |
| TASK-2.09 | Implement formatter.py | 3 | pending | none |
| TASK-2.10 | Implement setup_wizard.py | 4 | pending (needs TASK-2.14 first) | none |
| TASK-2.11 | Implement simulator.py | 4 | pending (needs TASK-2.14 first) | none |
| TASK-2.12 | Implement bitledger.py entry point | 5 | pending | SERIALIZED |
| TASK-2.13 | Complete test suite validation | 6 | pending | none |
| TASK-2.14 | Read docx files for wizard + simulator spec | pre-4 | pending | none |

---

## Dependency Waves

```
Wave 0:  TASK-2.00  TASK-2.01  TASK-2.02
Wave 1:  TASK-2.03
Wave 2:  TASK-2.04  TASK-2.05  TASK-2.06  TASK-2.07
Wave 3:  TASK-2.08  TASK-2.09
Wave 4:  TASK-2.10  TASK-2.11   (both need TASK-2.14 first)
Wave 5:  TASK-2.12
Wave 6:  TASK-2.13
```

---

## Completed

<!-- Tasks move here after Verifier sign-off + Docs closure -->
