"""CLI --rounding-report and rounding_report.format_aggregate."""

import json
from decimal import Decimal
from pathlib import Path

from bitledger import rounding_report
from bitledger.cli import main


def test_format_aggregate_single_exact() -> None:
    obs = rounding_report.observation_from_encode_amount(
        Decimal("4.53"),
        A=1,
        r=197,
        S=8,
        sf_index=0,
        dp_wire=2,
        rf=0,
        rd=0,
        account_pair=4,
        quantity_present=False,
    )
    s = rounding_report.format_aggregate([obs])
    assert "Δ sum" in s
    assert "1 exact" in s


def test_encode_rounding_report_with_amount(tmp_path: Path, capsys) -> None:
    bl = tmp_path / "r.bl"
    code = main(
        [
            "encode",
            "--quiet",
            "--rounding-report",
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
    out = capsys.readouterr().out
    assert "Rounding report" in out
    assert "k=0" in out
    assert "Δ sum" in out


def test_decode_rounding_report_compare(tmp_path: Path, capsys) -> None:
    bl = tmp_path / "x.bl"
    assert (
        main(
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
        == 0
    )
    code = main(
        [
            "decode",
            "--quiet",
            "--in",
            str(bl),
            "--rounding-report",
            "--compare-amount",
            "10.005",
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "Rounding report" in out
    assert "10.005" in out


def test_make_rounding_report_not_with_json(capsys) -> None:
    main(
        [
            "make",
            "--amount",
            "4.53",
            "--dp",
            "2",
            "--account-pair",
            "4",
            "--rounding-report",
        ]
    )
    out = capsys.readouterr().out
    assert "Rounding report" in out


def test_make_json_rounding_observation_embedded(capsys) -> None:
    main(
        [
            "make",
            "--json",
            "--rounding-report",
            "--amount",
            "4.53",
            "--dp",
            "2",
            "--account-pair",
            "4",
        ]
    )
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["sf_index"] == 0
    assert "Rounding report" not in out
    ro = data["rounding_observation"]
    assert ro["sf_index"] == 0
    assert ro["delta_typed_minus_wire"] in ("0", "0.00")
    assert ro["quantity_present"] is False


def test_decode_rounding_report_stderr_hint_without_compare(capsys, tmp_path: Path) -> None:
    bl = tmp_path / "y.bl"
    assert (
        main(
            [
                "encode",
                "--quiet",
                "--amount",
                "4.53",
                "--out",
                str(bl),
            ]
        )
        == 0
    )
    main(["decode", "--quiet", "--in", str(bl), "--rounding-report"])
    err = capsys.readouterr().err
    assert "compare-amount" in err.lower()
