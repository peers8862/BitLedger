"""Named JSON profiles for Layer 1 / Layer 2 defaults."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bitledger.errors import ProfileError
from bitledger.models import Layer1Config, Layer2Config


def _as_l1(d: dict[str, Any]) -> Layer1Config:
    return Layer1Config(**{k: v for k, v in d.items() if k in Layer1Config.__dataclass_fields__})


def _as_l2(d: dict[str, Any]) -> Layer2Config:
    return Layer2Config(**{k: v for k, v in d.items() if k in Layer2Config.__dataclass_fields__})


def save_profile(
    path: Path, name: str, l1: Layer1Config, l2: Layer2Config, *, force: bool = False
) -> None:
    if path.is_file() and not force and name.strip().lower() == "default":
        raise ProfileError(
            'profile name "default" already exists at this path; pass force=True to overwrite'
        )
    payload = {
        "name": name,
        "layer1": l1.__dict__.copy(),
        "layer2": l2.__dict__.copy(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_profile(path: Path) -> tuple[Layer1Config, Layer2Config]:
    if not path.is_file():
        raise ProfileError(f"profile not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return _as_l1(data["layer1"]), _as_l2(data["layer2"])
