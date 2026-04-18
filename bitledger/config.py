"""Master configuration for BitLedger.

Config file: ~/.config/bitledger/config.json (or $XDG_CONFIG_HOME/bitledger/config.json)
Profile config takes precedence over master config for session-level settings.

Fields:
    warn_short_form_mismatch (bool, default True):
        Emit DecoderWarning when 0x6F short-form is decoded but the loaded
        profile's Layer 2 settings differ from 0x6F defaults.
        Set false to suppress if you intentionally use 0x6F with non-default profiles.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path


_DEFAULTS: dict[str, object] = {
    "warn_short_form_mismatch": True,
}


def _config_path() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME", "")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "bitledger" / "config.json"


@dataclass
class MasterConfig:
    warn_short_form_mismatch: bool = True


def load_master_config(path: Path | None = None) -> MasterConfig:
    """Load master config from disk; missing keys fall back to defaults."""
    p = path or _config_path()
    data: dict[str, object] = {}
    if p.is_file():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass  # silent fallback to defaults
    return MasterConfig(
        warn_short_form_mismatch=bool(data.get("warn_short_form_mismatch", True)),
    )


def save_master_config(cfg: MasterConfig, path: Path | None = None) -> None:
    """Persist master config to disk."""
    p = path or _config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(
            {"warn_short_form_mismatch": cfg.warn_short_form_mismatch},
            indent=2,
        ),
        encoding="utf-8",
    )
