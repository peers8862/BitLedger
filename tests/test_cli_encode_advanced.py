"""encode --auto-sf, --accept-rounding; make --json."""

import json
from pathlib import Path

from bitledger.cli import main


def test_encode_rejects_rounding_without_accept(tmp_path: Path) -> None:
    bl = tmp_path / "x.bl"
    # Pair 4 rounds down; 10.005 at dp=2 sf=0 → non-integral R
    code = main(
        [
            "encode",
            "--quiet",
            "--amount",
            "10.005",
            "--dp",
            "2",
            "--sf",
            "0",
            "--account-pair",
            "4",
            "--out",
            str(bl),
        ]
    )
    assert code == 2
    assert not bl.is_file()


def test_encode_accepts_rounding_flag(tmp_path: Path) -> None:
    bl = tmp_path / "x.bl"
    code = main(
        [
            "encode",
            "--quiet",
            "--amount",
            "10.005",
            "--dp",
            "2",
            "--sf",
            "0",
            "--account-pair",
            "4",
            "--accept-rounding",
            "--out",
            str(bl),
        ]
    )
    assert code == 0
    assert bl.is_file() and len(bl.read_bytes()) >= 14


def test_encode_auto_sf(tmp_path: Path) -> None:
    bl = tmp_path / "y.bl"
    code = main(
        [
            "encode",
            "--quiet",
            "--amount",
            "2500000000",
            "--auto-sf",
            "--dp",
            "2",
            "--account-pair",
            "4",
            "--out",
            str(bl),
        ]
    )
    assert code == 0
    assert bl.is_file()


def test_make_json(capsys) -> None:
    code = main(
        [
            "make",
            "--json",
            "--amount",
            "4.53",
            "--dp",
            "2",
            "--account-pair",
            "4",
        ]
    )
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["N"] == 453
    assert data["sf_index"] == 0
    assert "suggested_encode_argv" in data
