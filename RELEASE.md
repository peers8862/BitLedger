# BitLedger v1.0.0 — Release Checklist

**Status:** Stable for personal use — 2026-04-18

## Gate checklist (per CLAUDE.md)

- [x] Gate A — All implemented features have acceptance criteria (backlog_april18.md, PLAN_value_cli_ux.md)
- [x] Gate B — Test suite passes: `python3 -m pytest tests/` (193+ tests, 0 failures)
- [x] Gate C — CLI help strings and docstrings match implementation; `cli_readme.md` updated
- [x] Gate D — This checklist (signed below)
- [x] Gate E — No untracked TODO in production code

## Feature completeness

- [x] `setup` — Layer 1/2 wizard, profile save
- [x] `encode` — --amount, --auto-sf, --min/max-sf, --accept-rounding, --rounding-report, --emit-l2, --description
- [x] `decode` — hex + .bl, --rounding-report, --compare-amount, --profile (short-form mismatch)
- [x] `make` / `suggest-sf` — exact-first SF search, --json, --quantity-present, --rounding-report
- [x] `check-amount` — verification printout, same flags as make
- [x] `profile list | use | show` — active pointer, XDG config, BITLEDGER_PROFILE env
- [x] `simulate` — encode/decode smoke test
- [x] `help` / `help --extra` — command listing + full protocol guide
- [x] `DecoderWarning` — non-fatal anomaly class with compact formatting
- [x] Short-form mismatch detection — warns when 0x6F + profile conflict
- [x] Master config — ~/.config/bitledger/config.json with warn_short_form_mismatch toggle

## Protocol compliance

- [x] Layer 1: CRC-15, SOH marker, sender ID, protocol version
- [x] Layer 2: full 6-byte header, 0x6F short form, SF indices 0–127
- [x] Layer 3: 40-bit record, Rules 1–3, Rule 5 (library), Rule 6 (compound)
- [x] CONFLICT-005: resolved 2026-04-18; 1111 account_pair suspends Rules 1–2

## Known deferred items (not v1 blockers)

- Rule 5 (batch integrity): library helper available; no CLI batch session subcommand
- Multi-record / control stream orchestration
- Extension bytes and decimal code 111
- Decoder for compound sessions (multi-record)

## Signed

Orchestrator sign-off: 2026-04-18
