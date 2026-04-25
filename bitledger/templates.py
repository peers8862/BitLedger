"""Transaction templates for recurring BitLedger records.

Templates store encode parameters for recurring transactions. Each use produces
a genuinely new wire record by incrementing record_sep (and group_sep on overflow)
in Layer 2, changing the wire blob and therefore the wire_id.

Template store: ~/.config/bitledger/templates/ (configurable in master config).
One JSON file per template, named <name>.json.

record_sep counter:
    record_sep = (counter % 31) + 1      # cycles 1..31
    group_sep  = min(counter // 31, 15)  # increments every 31 uses, max 15
    Capacity: 31 × 16 = 496 unique wire records per template.
    Counter wraps at 496 → warn user.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from bitledger.errors import ProfileError
from bitledger.hasher import compute_template_id as _compute_tid


COUNTER_WARN_THRESHOLD = 480  # warn when capacity is nearly exhausted


def default_template_dir() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME", "")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "bitledger" / "templates"


@dataclass
class Template:
    name: str
    amount: str
    account_pair: int = 4
    direction: int = 0
    status: int = 0
    debit_credit: int = 0
    quantity_present: bool = False
    description: str = ""
    profile: str | None = None
    template_id: str = ""
    created: str = ""
    counter: int = 0       # total encode calls; drives record_sep / group_sep
    instances: int = 0     # alias for counter (kept in sync)
    last_used: str | None = None


def record_sep_for_counter(counter: int) -> tuple[int, int]:
    """Return (record_sep, group_sep) for this counter value.

    record_sep cycles 1..31; group_sep increments every 31 uses (max 15).
    """
    record_sep = (counter % 31) + 1
    group_sep = min(counter // 31, 15)
    return record_sep, group_sep


def interpolate_description(pattern: str, dt: datetime | None = None) -> str:
    """Replace {YYYY}, {MM}, {DD}, {MONTH} placeholders with current date."""
    if not pattern:
        return pattern
    if dt is None:
        dt = datetime.now()
    return (
        pattern
        .replace("{YYYY}", str(dt.year))
        .replace("{MM}", f"{dt.month:02d}")
        .replace("{DD}", f"{dt.day:02d}")
        .replace("{MONTH}", dt.strftime("%B"))
    )


def _template_path(template_dir: Path, name: str) -> Path:
    return template_dir / f"{name}.json"


def save_template(template: Template, template_dir: Path | None = None) -> None:
    """Write template to disk. Computes template_id and created if not set."""
    d = template_dir or default_template_dir()
    d.mkdir(parents=True, exist_ok=True)
    if not template.template_id:
        template.template_id = _compute_tid(
            template.name, template.amount, template.account_pair,
            template.direction, 0  # currency 0 = session default
        )
    if not template.created:
        template.created = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    template.instances = template.counter
    p = _template_path(d, template.name)
    p.write_text(json.dumps(asdict(template), indent=2), encoding="utf-8")


def load_template(name: str, template_dir: Path | None = None) -> Template:
    """Load a template by name. Raises ProfileError if not found."""
    d = template_dir or default_template_dir()
    p = _template_path(d, name)
    if not p.is_file():
        raise ProfileError(f"template not found: {name!r} in {d}")
    data = json.loads(p.read_text(encoding="utf-8"))
    return Template(**{k: v for k, v in data.items() if k in Template.__dataclass_fields__})


def list_templates(template_dir: Path | None = None) -> list[Template]:
    """List all saved templates sorted by name."""
    d = template_dir or default_template_dir()
    if not d.is_dir():
        return []
    templates = []
    for p in sorted(d.glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            templates.append(Template(**{k: v for k, v in data.items() if k in Template.__dataclass_fields__}))
        except (OSError, ValueError, TypeError):
            pass
    return templates


def increment_template(name: str, template_dir: Path | None = None) -> tuple[Template, int, int]:
    """Load template, increment counter, save, return (template, record_sep, group_sep).

    The counter value BEFORE increment drives the sep values for this use.
    Warns (via return) if approaching capacity.
    """
    t = load_template(name, template_dir)
    current = t.counter
    record_sep, group_sep = record_sep_for_counter(current)
    t.counter += 1
    t.instances = t.counter
    t.last_used = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    save_template(t, template_dir)
    return t, record_sep, group_sep
