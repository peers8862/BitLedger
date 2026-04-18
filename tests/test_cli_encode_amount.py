"""CLI encode --amount integration."""

from pathlib import Path

from bitledger.cli import main


def test_encode_amount_writes_bl(tmp_path: Path) -> None:
    bl = tmp_path / "out.bl"
    code = main(
        [
            "encode",
            "--amount",
            "4.53",
            "--currency",
            "1",
            "--quiet",
            "--out",
            str(bl),
        ]
    )
    assert code == 0
    raw = bl.read_bytes()
    assert len(raw) >= 8 + 1 + 5
