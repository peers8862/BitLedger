# Workflow: High-Fragility Changes

Use this workflow for any task whose write scope includes HIGH FRAGILITY files. This supplements the standard feature-delivery workflow — all standard steps still apply. This workflow adds additional gates and requirements on top.

HIGH FRAGILITY files are defined in `system/fragility-register.md`. Currently:
- `bitledger/encoder.py`
- `bitledger/decoder.py`
- `bitledger/models.py`

---

## Additional Pre-Conditions (Orchestrator)

Before a task card for a HIGH FRAGILITY file can be dispatched:

```
[ ] Orchestrator has explicitly authorized this change in the task card
    (add to Risk notes: "Orchestrator approval: [date] — [reason change is needed]")
[ ] The specific high-fragility concern is named in the task card Fragility field
[ ] python -m pytest tests/test_roundtrip.py passes clean BEFORE the change
    (run this first; if it fails, fix that before opening this task)
[ ] A rollback path is confirmed: git checkout <files> is sufficient
```

If roundtrip tests fail before the change: do not proceed. Create a task card to fix the pre-existing failure first.

---

## Extended Risk Brief Requirements (Builder)

For HIGH FRAGILITY files, the risk brief must include:

1. **Current bit-level behavior:** Describe exactly what the file does for the specific bits/fields being changed. Cite specific functions and line numbers.
2. **Cross-layer dependency map:** Which other modules read fields this file writes? Which fields does this file read from other modules?
3. **Silent failure scenarios:** Identify any code path where a bug could produce a plausible-but-wrong encoded value (no exception raised, wrong bits set).
4. **Test vector coverage:** Which spec Section 2.3 / 10 test vectors currently test the changed code path?
5. **Error handling coverage:** For each new code path, what happens on out-of-range input? Does it raise ProtocolError or EncoderError correctly?

---

## Implementation Constraints (Builder)

In addition to standard constraints:

- **No changes to bit-field logic without a corresponding test in `tests/test_encoder.py` or `tests/test_decoder.py`.**
- **No changes to `models.py` field names or defaults without updating all callers.**
- **Every new encoder path must be reachable by a decoder roundtrip test.**
- **No silent failure modes.** Every error path must raise a typed exception from `errors.py`.

---

## Verifier Additional Steps (after standard verification)

After completing the standard verifier checklist, add:

### Step 9: Encode/Decode Sign-Off

```
[ ] python -m pytest tests/test_roundtrip.py passes (after the change)
[ ] python -m pytest tests/test_values.py passes (all SF/D combinations)
[ ] python -m pytest tests/test_encoder.py passes
[ ] python -m pytest tests/test_decoder.py passes

[ ] No previously-passing roundtrip test now produces different output
[ ] All spec Section 2.3 CRC test vectors produce correct results (if encoder.py was changed)

Encode/decode sign-off statement:
"I have verified that [describe specific encoding behavior changed] is correct at the bit level.
 All roundtrip and values tests pass. No previously-correct encodings now produce different output."

Sign-off: _______________
```

---

## Rollback Procedure

If a high-fragility change causes encoding errors after merge:

1. Revert the code change immediately:
   ```bash
   git revert <commit>
   ```

2. Verify roundtrip tests pass again:
   ```bash
   python -m pytest tests/test_roundtrip.py
   ```

3. Create a task card for root cause analysis before re-attempting the change.

---

## Memory After High-Fragility Changes

After a HIGH FRAGILITY task completes successfully, save to `system/logs/decisions.md`:
- What the change did
- What bit-level risks were identified and how they were mitigated
- Any new fragility patterns discovered
- Test results before and after
