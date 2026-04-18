## TASK-2.08: Implement profiles.py

Goal:                 Implement named profile persistence: save/load/list/delete JSON
                      files for Layer 1 and Layer 2 configuration, and resolve the
                      active profile at session start.

Acceptance criteria:  1. save_profile(name, layer1, layer2) writes a JSON file to
                         bitledger/profiles/<name>.json containing all fields from
                         both dataclasses
                      2. load_profile(name) returns (Layer1Config, Layer2Config)
                         with all fields populated; raises ProfileError if not found
                      3. list_profiles() returns a sorted list of profile name strings
                         (filenames without .json extension)
                      4. delete_profile(name) removes the file; raises ProfileError
                         if not found; raises ProfileError if name == "default" (the
                         default profile is protected)
                      5. get_default_profile() returns the "default" profile if it
                         exists; returns factory defaults (Layer1Config(), Layer2Config())
                         if not
                      6. Profile JSON round-trip: save then load produces dataclasses
                         equal to the originals (all fields preserved, types correct)
                      7. Profile directory created automatically if missing
                      8. python -m pytest tests/test_profiles.py passes

Write scope:          bitledger/profiles.py
                      tests/test_profiles.py

Tests required:       python -m pytest tests/test_profiles.py
                      python -m pytest tests/

Rollback:             git checkout bitledger/profiles.py tests/test_profiles.py

Fragility:            Profile JSON must use the same field names as the dataclasses in
                      models.py. Any rename in models.py breaks saved profiles silently
                      (they load with wrong default values, no error raised).
                      If models.py fields change, this module must be updated in the same
                      task card.

Risk notes:           (Orchestrator) The profiles/ directory contains user data — do not
                      delete or overwrite without explicit user intent. The "default" profile
                      protection prevents accidental loss of the primary session config.
                      Use pathlib.Path throughout — no os.path.

Depends on:           TASK-2.03 (models.py)

Status:               pending

