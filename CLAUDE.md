# CLAUDE.md — BitLedger

This file is the primary context document for all Claude agent sessions working on this project. Read it fully before touching any file.

---

## Project

BitLedger is a Python command-line tool that implements the BitLedger Binary Financial Transmission Protocol. The protocol carries complete double-entry accounting transactions in a compact binary footprint (40 bits per transaction). The tool provides four modes: `setup` (profile wizard), `encode` (transaction entry), `decode` (binary → journal entry), and `simulate` (full session demo).

**Install path:** `/Users/mp/making/bitledger`
**Entry point:** `bitledger/bitledger.py`
**CLI command:** `bitledger`

---

## Directory Map

| Directory/File | Purpose |
|---|---|
| `bitledger/bitledger.py` | Entry point — routes top-level commands |
| `bitledger/encoder.py` | Encodes transaction dict → 40-bit binary record |
| `bitledger/decoder.py` | Decodes binary record → transaction dict + validation |
| `bitledger/setup_wizard.py` | Interactive Layer 1 + Layer 2 configuration wizard |
| `bitledger/simulator.py` | Full sender/receiver session simulation |
| `bitledger/formatter.py` | Renders decoded transactions (binary, hex, journal) |
| `bitledger/models.py` | Dataclasses: Layer1Config, Layer2Config, TransactionRecord, SessionState |
| `bitledger/profiles.py` | Load/save/list/delete named profile JSON files |
| `bitledger/currencies.py` | Seeded 32-currency table |
| `bitledger/control.py` | 8-bit control record encode/decode |
| `bitledger/errors.py` | ProtocolError, EncoderError, DecoderError, ProfileError |
| `bitledger/profiles/` | Saved named profile JSON files |
| `tests/` | pytest test suite |
| `system/` | Dev system — orchestrator control plane. Not shipped. |

---

## Agent Model

| Role | When Active | Core Constraint |
|---|---|---|
| **Orchestrator** | Always | Owns backlog, contracts, merge decisions. Never writes production code. Never self-approves. |
| **Builder** | Implementation tasks | Works within explicit write scope. Produces risk brief before touching any file. |
| **Verifier** | After every implementation | Adversarial test execution. Produces signed checklist. Never implements. |
| **Docs** | Task closure | Updates CLAUDE.md, docstrings, help strings. Runs after merge. |
| **Explorer** | Audit phases, high-risk analysis | Read-only. Produces risk briefs or audit outputs. |

Handoff: Orchestrator (contract) → Builder (implement) → Verifier (validate) → Docs (close).

---

## Python Standards

Every module in this project must follow these rules:

- **Python 3.10+** — use `match` statements and modern type hints
- **Dataclasses** for all data models — no raw dicts passed between modules
- **Type annotations** on all function signatures
- **`raise` with typed exceptions** — use classes from `errors.py`, not bare `Exception`
- **No global mutable state** — pass `SessionState` explicitly
- **Exit codes:** 0 = success, 1 = user error, 2 = protocol/internal error

---

## Testing Requirements

```bash
python -m pytest tests/
```

| Change type | Required tests |
|---|---|
| `encoder.py` | `tests/test_encoder.py` + `tests/test_roundtrip.py` |
| `decoder.py` | `tests/test_decoder.py` + `tests/test_roundtrip.py` |
| `control.py` | `tests/test_control.py` |
| Value/SF tables | `tests/test_values.py` |
| Any change | Full suite: `python -m pytest tests/` |

Every change that adds or modifies behavior requires a new or updated test. No exceptions — this is Gate B.

---

## Hard Quality Gates

| Gate | Condition |
|---|---|
| **A** | No implementation without Orchestrator-authored acceptance criteria on the task card |
| **B** | No merge with failing tests or unresolved high-severity Verifier findings |
| **C** | No task marked "complete" unless CLI help strings and docstrings match the implementation |
| **D** | No release claim without a fully signed release checklist |
| **E** | No untracked TODO in any production code — every deferred item has a TASKS.md card |

---

## Fragility Markers

### HIGH FRAGILITY — Require Orchestrator approval + extended risk brief

| File(s) | Reason |
|---|---|
| `bitledger/encoder.py` | Bit-precise encoding; any error corrupts all records |
| `bitledger/decoder.py` | Cross-layer validation; silently wrong decode is undetectable |
| `bitledger/models.py` | All modules depend on dataclass field layout |

### SERIALIZED — One writer at a time, never parallel

| File | Reason |
|---|---|
| `bitledger/bitledger.py` | All command routing passes through here |

### NEVER COMMIT

```
.DS_Store
bitledger/profiles/*.json  (except default.json template)
__pycache__/
*.pyc
.pytest_cache/
```

---

## Canonical Task Source

`system/TASKS.md` is the only source of truth for open work.

- Orchestrator is the only agent that updates status fields
- New tasks are only added by the Orchestrator after Gate A is satisfied
- Every deferred TODO in production code must have a corresponding TASKS.md card (Gate E)
