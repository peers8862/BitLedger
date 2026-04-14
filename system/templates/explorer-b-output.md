# Explorer B Output Template — Code/Test Reality Report

Save output to: `system/audits/explorer-b-report.md`

---

```
# Explorer B Report: Code/Test Reality Audit

Explorer: [agent session]
Date: [YYYY-MM-DD]
Files read: [list all files read]

---

## Summary

Modules with full coverage: [N]
Modules with critical gaps: [N]
Modules with important gaps: [N]
TODOs in HIGH FRAGILITY files: [N]
Highest regression-risk hotspot: [file:line]

---

## Test Coverage Map

For each module, classify coverage status and list specific gaps.

| Module | Coverage status | Covered by | Critical gaps |
|---|---|---|---|
| bitledger/encoder.py | covered / gap-critical / gap-important / gap-deferred | [test files] | [specific untested behaviors] |
| bitledger/decoder.py | | | |
| bitledger/models.py | | | |
| bitledger/control.py | | | |
| bitledger/formatter.py | | | |
| bitledger/profiles.py | | | |
| bitledger/currencies.py | | | |
| bitledger/errors.py | | | |
| bitledger/setup_wizard.py | | | |
| bitledger/simulator.py | | | |
| bitledger/bitledger.py | | | |

Coverage gap classification:
- **gap-critical**: must have test before any change to this file
- **gap-important**: should have test added in current sprint
- **gap-deferred**: acceptable gap for now, track in TASKS.md

---

## TODO/FIXME Register — HIGH FRAGILITY Files

All TODO, FIXME, HACK, XXX occurrences in encoder.py, decoder.py, models.py.

| File | Line | Text | Type | Severity | Assessment |
|---|---|---|---|---|---|
| [file] | [line] | [text] | TODO/FIXME/HACK | HIGH/MEDIUM/LOW | [what it means] |

---

## Code-vs-Spec Gap List

Where protocol spec or technical overview claims behavior the code doesn't implement.

### GAP-001: [Short title]
- **Documented in:** [spec section]
- **Claim:** [what spec says]
- **Code reality:** [what code does or doesn't do]
- **File:line:** [location]
- **Severity:** HIGH / MEDIUM / LOW

### GAP-002:
[repeat]

---

## Help String Parity

CLI commands where `--help` output doesn't match actual behavior.

| Command | Help says | Code does | Severity |
|---|---|---|---|
| [command] | [what help claims] | [what code does] | |

---

## Required Baseline Test Suite Per Change Type

[Fill in based on what you found — these update system/config/test-baseline.yaml]

| Change type | Minimum required tests |
|---|---|
| `encoder.py` | `python -m pytest tests/test_encoder.py tests/test_roundtrip.py` |
| `decoder.py` | `python -m pytest tests/test_decoder.py tests/test_roundtrip.py` |
| `models.py` | `python -m pytest tests/` |
| `control.py` | `python -m pytest tests/test_control.py` |
| `currencies.py` | `python -m pytest tests/test_values.py` |
| Any change | `python -m pytest tests/` |

---

## Top Regression-Risk Hotspots

The 5–10 specific locations with highest regression risk if changed without tests.

| # | File:line | Risk description | Current test coverage |
|---|---|---|---|
| 1 | | | |
| 2 | | | |
| 3 | | | |

---

## Recommendations for Orchestrator

[Bullet points for: which coverage gaps are critical for Phase 2, which TODOs need immediate task cards, which hotspots should be noted in system/fragility-register.md. No implementation recommendations.]
```
