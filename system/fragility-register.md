# Fragility Register — BitLedger

Per-file access policy. Referenced from CLAUDE.md. Updated by Orchestrator only.

---

## HIGH FRAGILITY — Require Orchestrator approval + integration tests before any Builder change

| File | Reason | Required pre-conditions |
|---|---|---|
| `bitledger/encoder.py` | Bit-precise encoding. Any off-by-one corrupts all encoded records silently. | Orchestrator approval in task card + roundtrip test coverage before and after |
| `bitledger/decoder.py` | Cross-layer validation (flag redundancy checks). Wrong decode produces plausible-looking wrong output. | Orchestrator approval + Explorer B coverage map showing tests for every validation rule |
| `bitledger/models.py` | All other modules import and depend on field layout. Changing a field name or default silently breaks callers. | Orchestrator approval + grep to confirm all field references updated |

---

## SERIALIZED — One writer at a time, never parallel

| File | Reason |
|---|---|
| `bitledger/bitledger.py` | All command routing passes through here. Parallel edits cause merge conflicts that are hard to resolve correctly. |

---

## STANDARD — Normal Builder workflow

All other files in `bitledger/` follow the standard task card → Builder → Verifier → Docs cycle.

---

## NEVER COMMIT

```
.DS_Store
bitledger/profiles/*.json   (user data — except checked-in example templates)
__pycache__/
*.pyc
.pytest_cache/
*.egg-info/
dist/
build/
```
