# BitLedger Dev System

Orchestrator-based development control plane for the BitLedger CLI project.

Adapted from the Workwarrior devsystem (claude/v2 + codex/v2). Generic framework structure retained; all project-specific content replaced for BitLedger.

---

## Core Rules (Non-Negotiable)

- Hard gates A–E are mandatory merge/release blockers
- No self-approval — implementing role ≠ approving role
- Parallel work only on disjoint write sets
- `TASKS.md` is the summary index; `tasks/cards/<ID>.md` are per-task source of truth
- `config/command-syntax.yaml` is the canonical CLI contract (CSSOT) — create this once CLI shape is settled

---

## Structure

```
system/
├── README.md                   ← you are here
├── CLAUDE.md                   ← primary project context for all agents
├── ONBOARDING.md               ← agent entry point
├── TASKS.md                    ← summary task board
├── fragility-register.md       ← file-by-file access policy
│
├── bin/
│   └── blctl                   ← CLI: status, health, new-task, dispatch
│
├── config/
│   ├── gates.yaml              ← Gates A–E (machine-parseable)
│   ├── roles.yaml              ← Role definitions + phase profiles
│   ├── test-baseline.yaml      ← Required tests by change type
│   └── serialization-paths.txt ← Files requiring serialized ownership
│
├── scripts/
│   ├── common.sh               ← Shared utilities
│   ├── dispatch-worktree.sh    ← Creates git worktree on agent/<role>/<topic>
│   ├── new-task.sh             ← Generates task card + updates TASKS.md
│   ├── system-status.sh        ← System health check
│   ├── health.sh               ← Composite health: tests, TODOs, worktrees
│   ├── todo-scan.sh            ← Scan for untracked TODOs (Gate E)
│   ├── diff-summary.sh         ← Summarise what changed
│   ├── release-check.sh        ← Gate D release readiness
│   └── check-artifacts.sh      ← Verify required artifacts exist
│
├── roles/
│   ├── orchestrator.md
│   ├── builder.md
│   ├── verifier.md
│   ├── explorer.md
│   └── docs-agent.md
│
├── gates/
│   ├── all-gates.md            ← A–E with concrete checklists
│   └── release-checklist.md    ← Gate D sign-off form
│
├── templates/
│   ├── task-card.md
│   ├── builder-risk-brief.md
│   ├── explorer-a-output.md
│   ├── explorer-b-output.md
│   └── verifier-signoff.md
│
├── tasks/
│   ├── INDEX.md                ← Scannable manifest of all task cards
│   └── cards/                  ← Individual task card files (TASK-XXX.md)
│
├── workflows/
│   ├── phase1.md
│   ├── feature-delivery.md
│   └── high-fragility.md
│
├── context/
│   └── working-conventions.md
│
├── audits/                     ← Explorer A/B outputs (preferred location)
├── outputs/                    ← Alternative Explorer output dir
├── reports/                    ← Verifier sign-off outputs
└── logs/
    └── decisions.md            ← Architectural decision log
```

---

## Quick Start

```bash
cd /Users/mp/making/bitledger/system
chmod +x bin/blctl scripts/*.sh

# Check system readiness
bin/blctl status

# Create a new task card
bin/blctl new-task TASK-001 "Initialize Python project structure"

# Dispatch a builder in an isolated worktree
bin/blctl dispatch builder init-structure tasks/cards/TASK-001.md
```
