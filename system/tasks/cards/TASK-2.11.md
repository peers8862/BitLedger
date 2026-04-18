## TASK-2.11: Implement simulator.py

Goal:                 Implement the full sender/receiver session simulation mode
                      (`bitledger simulate`) that encodes a batch of transactions,
                      transmits them, and decodes them at the receiver end with
                      error reporting.

Acceptance criteria:  1. run_simulation(profile_name, transactions) encodes each
                         transaction in the list using encoder.py, then decodes each
                         encoded record using decoder.py, and reports results
                      2. Simulation output includes for each transaction:
                         - input values (amount, direction, account pair)
                         - encoded binary (40-bit hex + bit string)
                         - decoded journal entry
                         - PASS/FAIL status and any DecoderError messages
                      3. Layer 1 and Layer 2 headers encoded at session/batch start and
                         CRC-15 verified at receive end — CRC failure reported as FAIL
                      4. Rounding events logged: any record where rounding_flag=1 shows
                         the original value and the encoded approximation
                      5. Summary line at end: N transactions, M encoded, K decoded OK,
                         J errors
                      6. run_simulation() returns a SimulationResult dataclass (not
                         just prints)
                      7. python -m pytest tests/test_simulator.py passes

Write scope:          bitledger/simulator.py
                      tests/test_simulator.py

Tests required:       python -m pytest tests/test_simulator.py
                      python -m pytest tests/test_roundtrip.py
                      python -m pytest tests/

Rollback:             git checkout bitledger/simulator.py tests/test_simulator.py

Fragility:            The simulator is the primary integration test harness for the full
                      encode → transmit → decode loop. If encoder.py or decoder.py have
                      silent precision errors, the simulator is the most likely place
                      they surface. Any FAIL in simulation output that cannot be explained
                      by a known EncoderError or DecoderError must be escalated to
                      Orchestrator before proceeding.

Risk notes:           (Orchestrator) Read BitLedger_Technical_Overview.docx for the
                      simulator output format spec if one is defined. If the docx does
                      not specify format, use the acceptance criteria above as the design.
                      SimulationResult must be a dataclass (not dict) per Python standards.

Depends on:           TASK-2.05 (encoder value core), TASK-2.06 (encoder serialise),
                      TASK-2.07 (decoder.py), TASK-2.08 (profiles.py),
                      TASK-2.09 (formatter.py)

Status:               pending

