## TASK-2.12: Implement bitledger.py — CLI entry point

Goal:                 Implement the top-level argparse CLI that routes the four operating
                      modes (setup, encode, decode, simulate) to their module handlers.

Acceptance criteria:  1. `bitledger --help` prints usage with all four subcommands:
                         setup, encode, decode, simulate
                      2. `bitledger setup` runs setup_wizard and saves the resulting
                         profile; accepts optional `--profile NAME` (default: "default")
                         and `--edit` flag to re-run on an existing profile
                      3. `bitledger encode` accepts transaction input interactively or
                         via `--amount`, `--direction`, `--account-pair` flags; uses
                         `--profile NAME` (default: "default")
                      4. `bitledger decode HEX_OR_BINARY_STRING` decodes and prints
                         the journal entry; uses `--profile NAME`
                      5. `bitledger simulate` runs the simulator with the named profile;
                         accepts optional `--count N` for number of test transactions
                      6. Exit code 0 on success, 1 on user error (bad args, missing
                         profile), 2 on protocol error (EncoderError, DecoderError)
                      7. All error messages go to stderr
                      8. `bitledger --version` prints version from pyproject.toml
                      9. python -m pytest tests/test_cli.py passes

Write scope:          bitledger/bitledger.py
                      tests/test_cli.py

Tests required:       python -m pytest tests/test_cli.py
                      python -m pytest tests/

Rollback:             git checkout bitledger/bitledger.py tests/test_cli.py

Fragility:            SERIALIZED — one writer at a time. All four subcommand routes pass
                      through this file. Merge conflicts here cascade to all modes.
                      Do not add business logic to bitledger.py — it is a thin router
                      only. All protocol logic stays in the module it belongs to.

Risk notes:           (Orchestrator) argparse subparsers: each subcommand gets its own
                      subparser. Use `parser.set_defaults(func=handler)` pattern so the
                      dispatcher is a single `args.func(args)` call.
                      `--profile NAME` must be consistent across all subcommands —
                      define it as a shared parent parser argument.

Depends on:           All prior tasks (TASK-2.00 through TASK-2.11)

Status:               pending

