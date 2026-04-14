# Task Card Template

Copy this template for every new task. All 8 fields are required before a Builder can be dispatched (Gate A).

Orchestrator fills in all fields before dispatch. Builder fills in `Risk notes` before touching any file. Orchestrator updates `Status`.

---

```
## TASK-XXX: [Title — verb phrase, specific]

Goal:                 [One sentence. What problem does this solve or what capability does it add?]

Acceptance criteria:  [Measurable conditions. Each one must be verifiable as pass/fail.
                      Use numbered list for multiple criteria:
                      1. [criterion]
                      2. [criterion]
                      Use specific commands, file checks, or behavior descriptions.]

Write scope:          [Exact files the Builder is permitted to modify. One per line.
                      No glob patterns unless genuinely required — be specific.
                      /path/to/file1
                      /path/to/file2]

Tests required:       [Specific test commands to run, not categories.
                      python -m pytest tests/test_foo.py
                      python -m pytest tests/test_roundtrip.py
                      Manual: bitledger <command> and verify output]

Rollback:             [Exact steps to undo this change if it fails.
                      git checkout <files>
                      git rm --cached <files>
                      Restore from backup at <location>]

Fragility:            [None / or list relevant fragility flags:
                      HIGH FRAGILITY: <files> — requires Orchestrator approval
                      SERIALIZED: <files> — confirm no parallel active task touches these]

Risk notes:           [ORCHESTRATOR fills in: known risks from Explorer output or prior knowledge.
                      BUILDER fills in: pre-flight risk brief before touching any file.
                      Format:
                      - Existing behavior affected: [describe]
                      - Tests currently covering write scope: [list]
                      - Rollback verification: [how you confirmed rollback works]]

Status:               pending
```

---

## Status Values

| Value | Meaning |
|---|---|
| `pending` | Task card complete; not yet started |
| `in-progress` | Builder is actively working |
| `blocked` | Waiting on another task or external dependency |
| `in-review` | Verifier is running; awaiting sign-off |
| `complete` | Verifier signed off; Docs agent closed; Orchestrator confirmed |

---

## Sizing Guidelines

A well-sized task:
- Has a write scope of 1–5 files
- Can be completed in a single agent session
- Has acceptance criteria that can be verified in under 10 minutes
- Has a clear rollback that doesn't require reconstructing lost work

If a task has 10+ files in write scope or acceptance criteria that take >30 min to verify, split it.

---

## Example: Well-Formed Task Card

```
## TASK-005: Implement CRC-15 checksum in encoder

Goal:                 Implement the Layer 1 CRC-15 checksum computation so that encoded
                      session headers carry valid integrity data per protocol spec Section 2.3.

Acceptance criteria:  1. encoder.compute_crc15(payload_bits) returns the correct 15-bit
                         remainder for all test vectors in spec Section 2.3
                      2. Decoder rejects sessions with non-zero CRC remainder and raises
                         ProtocolError with message "CRC-15 integrity check failed"
                      3. python -m pytest tests/test_encoder.py tests/test_roundtrip.py passes
                      4. Manual: bitledger encode produces a valid 64-bit Layer 1 header

Write scope:          bitledger/encoder.py
                      bitledger/decoder.py
                      tests/test_encoder.py

Tests required:       python -m pytest tests/test_encoder.py tests/test_roundtrip.py
                      python -m pytest tests/
                      Manual: bitledger encode, verify Layer 1 header hex output

Rollback:             git checkout bitledger/encoder.py bitledger/decoder.py

Fragility:            HIGH FRAGILITY: bitledger/encoder.py, bitledger/decoder.py
                        Orchestrator approval confirmed 2026-04-14
                      SERIALIZED: none

Risk notes:           (Orchestrator) Spec Section 2.3 gives exact XOR-shift algorithm and
                      test vectors — use them as test cases directly.
                      (Builder pre-flight) encoder.py build_layer1_header() currently has a
                      placeholder at line 34; CRC must be appended as bits 50-64.
                      Rollback confirmed: git checkout reverts both files cleanly.

Status:               pending
```
