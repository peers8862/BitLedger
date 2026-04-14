# Working Conventions — BitLedger

Operator preferences and multi-agent norms. Read by all agents before starting work.

---

## Response Style

- Be concise. Lead with the action or answer, not the reasoning.
- No trailing summaries of what you just did — the diff speaks for itself.
- When referencing code, include `file:line` for easy navigation.
- No emojis unless explicitly requested.

---

## Code Style

- Python 3.10+ — use `match` statements, `|` union types, dataclasses with `field()`
- Type annotations on all public functions
- Docstrings only where behaviour is non-obvious — don't document what the name already says
- No defensive error handling for scenarios that can't happen — trust the model layer
- Keep modules focused: `encoder.py` encodes, `decoder.py` decodes, nothing crosses those lines

---

## Multi-Agent Norms

- Orchestrator authors every task card before dispatch
- Builder produces a 3-line risk brief before touching any file: (1) what the current code does, (2) what tests cover it now, (3) rollback plan
- Verifier runs tests adversarially — failing tests are not acceptable with "known baseline" excuses unless explicitly documented
- Explorer agents are read-only: no writes, no suggestions, just facts
- Docs agent runs last, after Verifier sign-off, not during implementation

---

## Path Conventions

- All paths relative to project root: `/Users/mp/making/bitledger`
- Dev system always lives at `system/` — never referenced from production code
- Profile JSON files live in `bitledger/profiles/` — treat as user data, not source
- Tests live in `tests/` at project root, not inside `bitledger/`

---

## Protocol Reference

The protocol spec (`BitLedger_Protocol_v3.docx`) is authoritative for all bit-level decisions.
The technical overview (`BitLedger_Technical_Overview.docx`) is authoritative for implementation structure.
When the two documents conflict, flag it as an Explorer A finding before implementing either interpretation.
