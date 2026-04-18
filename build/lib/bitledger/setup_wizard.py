"""Interactive setup for Layer 1 / Layer 2 (TASK-2.10 subset)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from bitledger.models import Layer1Config, Layer2Config


def _prompt(input_fn: Callable[[str], str], label: str, default: str) -> str:
    s = input_fn(f"{label} [{default}]: ").strip()
    return s if s else default


def run_wizard(
    input_fn: Callable[[str], str] | None = None,
    initial_l1: Layer1Config | None = None,
    initial_l2: Layer2Config | None = None,
) -> tuple[Layer1Config, Layer2Config]:
    inp = input_fn or input
    l1 = replace(initial_l1 or Layer1Config())
    l2 = replace(initial_l2 or Layer2Config())

    sid = _prompt(inp, "Sender ID (hex32, e.g. 0xDEADBEEF)", f"0x{l1.sender_id:08X}")
    l1.sender_id = int(sid, 0) & 0xFFFFFFFF
    sub = _prompt(inp, "Sub-entity ID (0-31)", str(l1.sub_entity_id))
    l1.sub_entity_id = int(sub) & 0x1F
    cm = _prompt(inp, "Compound mode active session-wide? (0/1)", str(int(l1.compound_mode_active)))
    l1.compound_mode_active = cm not in ("0", "false", "False", "")

    while True:
        tt = _prompt(inp, "Layer2 transmission_type (1=pre 2=copy 3=rep)", str(l2.transmission_type))
        l2.transmission_type = int(tt)
        if l2.transmission_type in (1, 2, 3):
            break
        print("Invalid: transmission_type 00 is forbidden — use 1, 2, or 3.")

    cpfx = _prompt(inp, "Layer2 compound_prefix (0=none 1=max3 2=max7 3=unlim)", str(l2.compound_prefix))
    l2.compound_prefix = int(cpfx) & 3
    if l1.compound_mode_active and l2.compound_prefix == 0:
        print("(warn) compound_prefix=00 forbids 1111 in batch even if session compound is on.")

    return l1, l2
