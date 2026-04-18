"""profiles JSON."""

from pathlib import Path

import pytest

from bitledger.errors import ProfileError
from bitledger.models import Layer1Config, Layer2Config
from bitledger.profiles import load_profile, save_profile


def test_save_load_roundtrip(tmp_path: Path):
    p = tmp_path / "p.json"
    l1 = Layer1Config(sender_id=42)
    l2 = Layer2Config(record_sep=3)
    save_profile(p, "t", l1, l2)
    a, b = load_profile(p)
    assert a.sender_id == 42
    assert b.record_sep == 3


def test_missing(tmp_path: Path):
    with pytest.raises(ProfileError):
        load_profile(tmp_path / "none.json")


def test_default_name_overwrite_requires_force(tmp_path: Path):
    p = tmp_path / "x.json"
    l1, l2 = Layer1Config(), Layer2Config()
    save_profile(p, "default", l1, l2)
    with pytest.raises(ProfileError, match="default"):
        save_profile(p, "default", l1, l2, force=False)
    save_profile(p, "default", l1, l2, force=True)
