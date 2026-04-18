"""bitledger profile list|use|show and effective_profile_path."""

from pathlib import Path

import pytest

from bitledger.cli import main
from bitledger.cli_profile import active_profile_file, read_active_profile_path, write_active_profile
from bitledger.models import Layer1Config, Layer2Config
from bitledger.profiles import save_profile


def test_profile_list_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    d = tmp_path / "profiles"
    d.mkdir()
    save_profile(d / "a.json", "alpha", Layer1Config(sender_id=1), Layer2Config(record_sep=2))
    code = main(["profile", "list", "--dir", str(d)])
    assert code == 0


def test_profile_use_show_active(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    xdg = tmp_path / "xdg"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    monkeypatch.chdir(tmp_path)
    d = tmp_path / "profiles"
    d.mkdir()
    p = d / "corp.json"
    save_profile(p, "corp", Layer1Config(sender_id=0xCAFE), Layer2Config(scaling_factor_index=3))

    assert main(["profile", "use", "corp", "--dir", str(d)]) == 0
    assert read_active_profile_path() == p.resolve()

    out_c = main(["profile", "show"])
    assert out_c == 0


def test_encode_resolves_active_profile(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    xdg = tmp_path / "xdg"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    monkeypatch.chdir(tmp_path)
    d = tmp_path / "profiles"
    d.mkdir()
    p = d / "x.json"
    save_profile(p, "x", Layer1Config(sender_id=0xBEEF), Layer2Config(decimal_position=2))
    write_active_profile(p)
    bl = tmp_path / "out.bl"
    code = main(
        [
            "encode",
            "--quiet",
            "--amount",
            "4.53",
            "--out",
            str(bl),
        ]
    )
    assert code == 0
    assert bl.is_file()
