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

| ID | Title | Status |
|---|---|---|
| — | No tasks yet. Run `bin/blctl new-task TASK-001 "..."` to create the first. | — |
