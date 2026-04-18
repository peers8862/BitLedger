"""CLI encode → file → decode path."""

from pathlib import Path

from bitledger import encoder
from bitledger.bitledger import main
from bitledger.models import Layer1Config, Layer2Config, TransactionRecord


def test_encode_decode_roundtrip_file(tmp_path: Path) -> None:
    l1 = Layer1Config(sender_id=0xCAFEBABE, sub_entity_id=3)
    l2 = Layer2Config(entity_id=3, record_sep=5)
    rec = TransactionRecord(
        multiplicand=1,
        multiplier=197,
        account_pair=4,
        direction=0,
        status=0,
        debit_credit=0,
        completeness=0,
    )
    blob = encoder.encode_layer1_bytes(l1)
    blob += encoder.encode_layer2_bytes(l2)
    blob += encoder.serialise(rec, 8, l1, l2).to_bytes(5, "big")
    p = tmp_path / "x.bl"
    p.write_bytes(blob)
    code = main(["decode", "--in", str(p), "--quiet"])
    assert code == 0
