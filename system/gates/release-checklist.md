# Release Checklist — BitLedger vX.Y.Z

Fill in the version, date, and role before checking any item.
Save the completed checklist to `system/reports/releases/vX.Y.Z-checklist.md` before tagging.

---

Version: _______________
Date: _______________
Checked by: _______________

---

## Criterion 1 — `bitledger --help` clean output

[ ] `bitledger --help` produces no errors, no garbled output, no "command not found" messages | Evidence: ___ | Checked by: Verifier on ___

## Criterion 2 — All four modes respond correctly

[ ] `bitledger setup --help`, `bitledger encode --help`, `bitledger decode --help`, `bitledger simulate --help` all exit 0 with correct usage output | Evidence: ___ | Checked by: Verifier on ___

## Criterion 3 — Full pytest suite passes

[ ] `python -m pytest tests/` passes with 0 failures | Evidence: ___ | Checked by: Verifier on ___

## Criterion 4 — Encode/decode roundtrip is lossless

[ ] `tests/test_roundtrip.py` passes for all 32 currency codes, all 6 decimal positions, all standard account pairs | Evidence: ___ | Checked by: Verifier on ___

## Criterion 5 — Setup wizard creates a valid profile

[ ] `bitledger setup --profile test` creates a valid JSON profile that encoder and decoder accept without errors | Evidence: ___ | Checked by: Verifier on ___

---

## Sign-Off

All five criteria satisfied (evidence gathered + code correct): **YES / NO**

If NO — list blocking items, assign task cards, do not tag:
1.
2.
3.

Orchestrator sign-off: _______________ Date: _______________

---

Completed checklists are saved to `system/reports/releases/vX.Y.Z-checklist.md` before tagging.
