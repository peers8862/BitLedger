# BitLedger — Developer Guide

**Audience:** You, as the primary developer and Orchestrator of this project.

This document explains how to approach ongoing development: version decisions, daily workflow, how to direct AI assistants effectively, and what decisions are yours to make vs. delegated.

---

## Your role

You are the **Orchestrator** — the role defined in CLAUDE.md that owns the backlog, contracts, and merge decisions. You never need to implement yourself if you don't want to, but you control what gets built, accepted, and released.

In practice this means:
- You decide what the next feature or fix is
- You define acceptance criteria (what "done" looks like) before implementation starts
- You review diffs and test results before accepting
- You are the only one who marks tasks complete in `system/TASKS.md`
- You sign release checklogs in `RELEASE.md`

The AI roles (Builder, Verifier, Docs, Explorer) exist to do implementation and validation on your behalf. You direct them; they execute.

---

## Version bump workflow

This project uses **semantic versioning** (`MAJOR.MINOR.PATCH`).

| Bump | When |
|------|------|
| **PATCH** (1.0.x) | Bug fixes, test additions, doc corrections — no new CLI flags or protocol changes |
| **MINOR** (1.x.0) | New CLI flags, new commands, new config options — backward-compatible additions |
| **MAJOR** (x.0.0) | Protocol changes, breaking CLI changes (removed flags, changed wire format), new layer definitions |

### Steps for any version bump

1. **Confirm tests pass:** `python3 -m pytest tests/`
2. **Edit `pyproject.toml`:** change the `version` field
3. **Update `RELEASE.md`:** add a new section at the top for the new version with date, gate checklist, and what changed. Keep old versions below.
4. **Commit:** `git commit -m "v1.x.x: <one-line summary>"`
5. **Tag:** `git tag v1.x.x`
6. **Push tag when ready:** `git push && git push --tags`

### Current version
`1.0.0` — stable for personal use, tagged 2026-04-18.

### Next expected bumps
- Any new command or flag → `1.1.0`
- Any bug fix in encoder/decoder with no new surface → `1.0.x`
- BitPads integration or multi-record CLI → discuss before deciding MAJOR vs MINOR

---

## Daily development workflow

### Starting a new feature

1. Decide what you want and write it down — even one sentence of acceptance criteria. Add it to `system/TASKS.md` as an Active Task.
2. Open Claude Code and describe the task. Reference the acceptance criteria you just wrote.
3. Claude Code reads the relevant files, proposes an approach, and asks if there are questions. Answer them.
4. Implementation runs. Review the diff.
5. Run tests: `python3 -m pytest tests/`
6. If tests pass and diff looks right: accept. If not: push back with specific feedback.

### Before touching HIGH FRAGILITY files

The three files that require extra caution are `encoder.py`, `decoder.py`, and `models.py`. Before any change to these:

- State exactly what bit or rule is changing
- Ask for a risk brief from the Builder before any edit happens
- Run the full test suite before and after: `python3 -m pytest tests/`
- For any protocol rule change, check README.md to confirm the spec backing the change

### Committing

Separate commits by concern:
- **Implementation** (`.py` changes): one commit per logical change
- **Docs** (`cli_readme.md`, `README.md`, analysis files): one commit
- **Tests** added for a new feature: can go with implementation or separate

Never commit:
- `__pycache__/`, `*.pyc`, `.pytest_cache/`
- Real profile JSONs in `bitledger/profiles/` (except a template)
- `*.bl` binary output files
- `project/scratch/` contents

### Running tests

```bash
# Full suite — always run this before accepting any change
python3 -m pytest tests/

# Quick smoke test
python3 -m pytest tests/ -q --tb=no

# One module
python3 -m pytest tests/test_encoder.py -v

# After encoder or decoder changes, always run roundtrip too
python3 -m pytest tests/test_encoder.py tests/test_decoder.py tests/test_roundtrip.py
```

---

## How to direct Claude Code effectively

### Be specific about scope

Tell Claude exactly which files can be touched. For high-fragility work, say explicitly: "only modify `cli.py` — do not touch `encoder.py` or `decoder.py`."

### Establish acceptance criteria first

Before saying "implement X," say "when X is done: (a) `bitledger make --foo` outputs Y, (b) tests pass, (c) cli_readme.md documents the new flag." This prevents scope creep and gives the Verifier role a clear checklist.

### Use the agent model vocabulary

- "Explorer pass on X" — read-only audit; report findings, do not edit
- "Builder task: implement X per these criteria" — implementation only
- "Verifier pass on the last change" — adversarial test run, signed checklist
- "Docs closure for the last task" — update CLAUDE.md docstrings and help strings

### For large tasks

Break them into phases (as done in the v1.0.0 sweep). Give Claude Code the full phase list up front so it can execute without stopping to ask at each step. Reserve the ask-before-proceeding behavior for decisions that genuinely need your input (scope choices, naming, protocol interpretation).

### When Claude Code makes a mistake

Push back with the specific test case or the exact wrong output. "The test `test_quantity_basic_N` fails because A=8, r=3, quantity=True should give N=24 not N=131" is much more useful than "the tests are failing."

---

## Quality gates in practice

These are the gates from CLAUDE.md, translated to daily use:

**Gate A** — Before you ask for implementation: write the acceptance criteria.
**Gate B** — After implementation: `python3 -m pytest tests/`. Do not accept a PR if tests fail.
**Gate C** — Before closing a task: run `bitledger <command> --help` and confirm it matches what `cli_readme.md` says.
**Gate D** — Before a version tag: update and sign `RELEASE.md`.
**Gate E** — Before committing: grep for TODO in production code. If any, create a task card or remove the TODO first.

```bash
# Gate E check
grep -r "TODO\|FIXME\|HACK\|XXX" bitledger/ --include="*.py"
```

---

## Protocol change discipline

If you need to change how bits are packed, rules are validated, or layers are structured:

1. Update `README.md` (the protocol spec) first
2. Open a CONFLICT-style resolution doc in `project/protocol docs/markdown/` if there's ambiguity
3. Update `models.py` (HIGH FRAGILITY) carefully — all other modules depend on field layout
4. Update `encoder.py` and `decoder.py` in lockstep — never one without the other
5. Add roundtrip tests that exercise the exact bits changed
6. Bump MINOR or MAJOR version accordingly

---

## TASKS.md as your control surface

`system/TASKS.md` is the only place open work is tracked. Keep it up to date:

- Add tasks before asking for implementation
- Mark tasks complete only after Gate B and Gate C pass
- Deferred items stay as tasks — never delete them, just note why they're deferred
- Use the wave numbering for dependency ordering when adding new tasks

---

## Master config and profile management

**Master config** (`~/.config/bitledger/config.json`):
- Session-wide toggles that survive across profile changes
- Currently: `warn_short_form_mismatch` (bool, default true)
- Edit manually as JSON; no CLI yet for this

**Active profile** (`~/.config/bitledger/active.json`):
- Set with `bitledger profile use <name>`
- Contains the resolved path to the active profile JSON
- Override per-command with `--profile` or `BITLEDGER_PROFILE`

**Profile store** (convention: `./profiles/` in your working directory):
- Created by `bitledger setup --out profiles/name.json`
- Never committed to git unless it's a template with safe defaults

---

## Reference

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Agent model, Python standards, fragility markers, quality gates |
| `README.md` | Protocol specification v3.0 (primary reference) |
| `cli_readme.md` | Full CLI flag reference |
| `RELEASE.md` | Version history and release checklists |
| `system/TASKS.md` | Canonical open task board |
| `backlog_april18.md` | Phase 1 implementation review (solid vs deferred) |
| `project/analysis/` | Value encoding, notation, SF reference papers |
| `project/scratch/` | Working notes — not committed |
