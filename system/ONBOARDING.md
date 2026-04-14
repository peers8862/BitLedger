# ONBOARDING.md — BitLedger Agent Entry Point

**Read this file first.** It tells you everything you need to orient to this project and start work.

---

## What This Project Is

BitLedger is a Python CLI tool implementing the BitLedger Binary Financial Transmission Protocol — a compact binary format for double-entry accounting records. A complete transaction (both sides, full accounting classification, direction, status, value, currency) fits in 40 bits. The tool encodes, decodes, and simulates protocol sessions.

**Project path:** `/Users/mp/making/bitledger`
**Protocol spec:** `BitLedger_Protocol_v3.docx`
**Technical spec:** `BitLedger_Technical_Overview.docx`

---

## Read These Files Next (in order)

| File | What it gives you |
|---|---|
| `system/CLAUDE.md` | Full project context: directory map, agent model, Python standards, fragility markers, testing, hard gates |
| `system/TASKS.md` | Current task board: what's done, what's pending, dispatch queue |
| `system/context/working-conventions.md` | Operator preferences, response style, multi-agent norms |
| `system/logs/decisions.md` | Architectural decisions — read before touching encoder, decoder, or models |

---

## Current State

- **Phase:** Phase 1 — project setup
- **Status:** System initialized. No production code yet.
- **Next step:** Explorer A (spec audit) → Explorer B (implementation map) → task card authoring

---

## The Control Plane

Everything governing how work is done lives in `system/`. It is not shipped with the product.

```
system/
  ONBOARDING.md          ← you are here
  CLAUDE.md              ← full project + agent rules
  TASKS.md               ← canonical task board
  fragility-register.md  ← file-by-file access policy
  logs/decisions.md      ← architectural decision log
  context/
    working-conventions.md
  roles/                 ← Orchestrator, Builder, Verifier, Explorer, Docs
  workflows/             ← feature-delivery, phase1, high-fragility
  gates/                 ← Gates A–E with checklists
  templates/             ← task-card, verifier-signoff, builder-risk-brief
  tasks/
    INDEX.md             ← scannable manifest of all task cards
    cards/               ← individual task cards (TASK-XXX.md)
  audits/                ← Explorer A/B report outputs
  outputs/               ← alternative Explorer output dir
  reports/               ← Verifier sign-off outputs
  config/
    gates.yaml
    roles.yaml
    test-baseline.yaml
  scripts/               ← blctl CLI, dispatch, new-task, health checks
  bin/blctl              ← dev system CLI entrypoint
```

---

## Hard Rules (non-negotiable)

1. **Read before editing** — another agent may have modified the file since your last session.
2. **`system/` is the memory store** — decisions go to `system/logs/decisions.md`, task state to `system/TASKS.md`.
3. **SERIALIZED files** (`bitledger/bitledger.py`) — one writer at a time, never parallel.
4. **HIGH FRAGILITY files** (`encoder.py`, `decoder.py`, `models.py`) — require Orchestrator approval before any Builder touches them.
5. **Never commit profile JSON files** — `bitledger/profiles/` contains user data, not source code.

---

## How Work Gets Done

Handoff: **Orchestrator** (authors task card) → **Builder** (implements within write scope) → **Verifier** (adversarial review) → **Docs** (closes task).

```bash
cd /Users/mp/making/bitledger/system
bin/blctl status          # confirm system state
bin/blctl new-task TASK-001 "goal"
bin/blctl dispatch builder <topic> tasks/cards/TASK-001.md
```
