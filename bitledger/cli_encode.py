"""Apply argparse namespace fields to Layer1/Layer2 (BitPads-aligned flags)."""

from __future__ import annotations

from bitledger.errors import EncoderError
from bitledger.models import Layer1Config, Layer2Config


def apply_encode_overrides(ns: object, l1: Layer1Config, l2: Layer2Config) -> None:
    """Mutate l1/l2 from CLI flags when provided."""
    if getattr(ns, "sender", None) is not None:
        l1.sender_id = int(ns.sender, 0) & 0xFFFFFFFF
    if getattr(ns, "subentity", None) is not None:
        l1.sub_entity_id = int(ns.subentity) & 0x1F
    if getattr(ns, "compound_session", None) is not None:
        l1.compound_mode_active = bool(int(ns.compound_session))
    if getattr(ns, "perms", None) is not None:
        p = int(ns.perms) & 0xF
        l1.perm_read = bool((p >> 3) & 1)
        l1.perm_write = bool((p >> 2) & 1)
        l1.perm_correct = bool((p >> 1) & 1)
        l1.perm_represent = bool(p & 1)
    if getattr(ns, "sf", None) is not None:
        l2.scaling_factor_index = int(ns.sf) & 0x7F
    if getattr(ns, "currency", None) is not None:
        l2.currency_code = int(ns.currency) & 0x3F
    if getattr(ns, "txtype", None) is not None:
        l2.transmission_type = int(ns.txtype) & 3
        if l2.transmission_type == 0:
            raise EncoderError("transmission_type 00 is invalid")
    if getattr(ns, "compound_prefix", None) is not None:
        l2.compound_prefix = int(ns.compound_prefix) & 3
    if getattr(ns, "sep_group", None) is not None:
        l2.group_sep = int(ns.sep_group) & 0xF
    if getattr(ns, "sep_record", None) is not None:
        l2.record_sep = int(ns.sep_record) & 0x1F
    if getattr(ns, "sep_file", None) is not None:
        l2.file_sep = int(ns.sep_file) & 7
    if getattr(ns, "optimal_split", None) is not None:
        l2.optimal_split = int(ns.optimal_split) & 0xF
    if getattr(ns, "dp", None) is not None:
        l2.decimal_position = int(ns.dp) & 7
