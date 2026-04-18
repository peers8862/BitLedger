"""formatter.py (TASK-2.09)."""

from decimal import Decimal

from bitledger import decoder, formatter
from bitledger.models import Layer1Config, Layer2Config, SessionState, TransactionRecord


def test_format_binary_hex():
    n = 0x123456789A
    b = formatter.format_binary(n)
    assert " | " in b
    assert formatter.format_hex(n).startswith("0x")


def test_format_layer_headers():
    l1 = Layer1Config(sender_id=0xABCD, sub_entity_id=2)
    l2 = Layer2Config(currency_code=1, scaling_factor_index=0)
    assert "0x0000ABCD" in formatter.format_layer1_header(l1)
    assert "LAYER 2" in formatter.format_layer2_header(l2)


def test_format_journal_amount():
    l2 = Layer2Config(scaling_factor_index=0, decimal_position=2, currency_code=1)
    ss = SessionState(layer1=Layer1Config(), layer2=l2, current_split=8, current_sf_index=0)
    rec = TransactionRecord(
        multiplicand=1,
        multiplier=197,
        direction=0,
        status=0,
        account_pair=4,
        quantity_present=False,
    )
    txt = formatter.format_journal(rec, ss)
    assert "4.53" in txt or "4.5300" in txt
    assert "BITLEDGER JOURNAL ENTRY" in txt
    assert "DEBIT" in txt or "CREDIT" in txt
    assert "Op Income" in txt or "Asset" in txt


def test_format_journal_quantity():
    l2 = Layer2Config(scaling_factor_index=0, decimal_position=2, currency_code=1)
    ss = SessionState(layer1=Layer1Config(), layer2=l2, current_split=8)
    rec = TransactionRecord(
        multiplicand=249,
        multiplier=24,
        direction=0,
        status=0,
        account_pair=4,
        quantity_present=True,
    )
    amt = decoder.decode_value(249, 24, 8, 0, 2, True)
    assert amt == Decimal("59.76")
