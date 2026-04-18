"""setup_wizard.py — scripted input."""

from bitledger.models import Layer1Config, Layer2Config
from bitledger.setup_wizard import run_wizard


def test_wizard_scripted():
    lines = iter(
        [
            "",  # sender default
            "7",  # sub-entity
            "1",  # compound
            "1",  # txtype ok
            "3",  # compound prefix unlimited
        ]
    )

    def fake_input(_: str) -> str:
        return next(lines)

    l1, l2 = run_wizard(input_fn=fake_input)
    assert l1.sub_entity_id == 7
    assert l1.compound_mode_active is True
    assert l2.transmission_type == 1
    assert l2.compound_prefix == 3


def test_wizard_edit_mode():
    l1 = Layer1Config(sender_id=0x10)
    l2 = Layer2Config(record_sep=2)
    lines = iter(["0x20", "", "", "1", "0"])

    def fake_input(_: str) -> str:
        return next(lines)

    o1, o2 = run_wizard(input_fn=fake_input, initial_l1=l1, initial_l2=l2)
    assert o1.sender_id == 0x20
    assert o2.record_sep == 2
