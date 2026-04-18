"""models.py and errors.py smoke tests."""

import pytest

from bitledger.errors import EncoderError, ProtocolError
from bitledger.models import Layer1Config, Layer2Config, SessionState, TransactionRecord


def test_errors_distinct():
    assert issubclass(EncoderError, Exception)
    with pytest.raises(ProtocolError):
        raise ProtocolError("x")


def test_layer1_defaults():
    l1 = Layer1Config()
    assert l1.protocol_version == 1
    assert l1.perm_read is True
    assert l1.checksum is None


def test_layer2_defaults():
    l2 = Layer2Config()
    assert l2.transmission_type == 1
    assert l2.optimal_split == 8
    assert l2.decimal_position == 2
    assert l2.reserved == 1
    assert l2.compound_prefix == 0


def test_transaction_record_extensions_fresh():
    a = TransactionRecord()
    b = TransactionRecord()
    a.extensions.append(1)
    assert b.extensions == []


def test_session_state_split():
    s = SessionState()
    assert s.current_split == 8
