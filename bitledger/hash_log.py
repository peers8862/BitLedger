"""JSONL hash log for BitLedger encode/decode history.

Log location: ~/.config/bitledger/hash_log.jsonl (or config override).
Format: one JSON object per line, append-only.

Each entry records wire_id (exact blob identity) and semantic_id (transaction
identity) so duplicates can be detected at two levels:
  wire_id match    → same bytes transmitted twice (replay/re-send)
  semantic_id match → same transaction content, possibly re-encoded
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


def default_log_path() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME", "")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "bitledger" / "hash_log.jsonl"


@dataclass
class LogEntry:
    wire_id: str
    semantic_id: str
    timestamp: str           # ISO-8601 UTC
    log_direction: str       # "encode" or "decode"
    wire_bytes_hex: str
    amount: str
    account_pair: int
    tx_direction: int
    tx_status: int
    currency: int
    session_id: str = ""
    template_id: str | None = None
    instance: int | None = None
    parent_wire_id: str | None = None

    @staticmethod
    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def append_log(entry: LogEntry, path: Path | None = None) -> None:
    """Append one entry to the JSONL log. Creates file and parent dirs if needed."""
    p = path or default_log_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(asdict(entry), ensure_ascii=False)
    with p.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def _load_entries(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return entries


def check_log(
    wire_id: str,
    semantic_id: str,
    template_id: str | None = None,
    path: Path | None = None,
) -> dict[str, list[dict]]:
    """Check for duplicate wire_id or semantic_id in the log.

    Returns {"wire": [...matching wire_id entries], "semantic": [...matching semantic_id entries]}.
    semantic matches with the same template_id are NOT included (recurring = intentional).
    """
    p = path or default_log_path()
    entries = _load_entries(p)
    wire_matches = [e for e in entries if e.get("wire_id") == wire_id]
    semantic_matches = [
        e for e in entries
        if e.get("semantic_id") == semantic_id
        and e.get("template_id") != template_id   # same template = expected recurrence
        and e.get("template_id") is None           # non-template semantic match = warn
    ]
    # If template_id is provided and matches, these are intentional recurrences — suppress
    if template_id is not None:
        semantic_matches = []
    return {"wire": wire_matches, "semantic": semantic_matches}


def search_log(
    path: Path | None = None,
    *,
    amount: str | None = None,
    account_pair: int | None = None,
    since: str | None = None,
    template_id: str | None = None,
    partial_id: str | None = None,
    last: int | None = None,
    log_direction: str | None = None,
) -> list[dict]:
    """Search log entries by optional filters. Returns newest-first."""
    p = path or default_log_path()
    entries = _load_entries(p)
    if since:
        entries = [e for e in entries if e.get("timestamp", "") >= since]
    if amount is not None:
        entries = [e for e in entries if e.get("amount") == amount]
    if account_pair is not None:
        entries = [e for e in entries if e.get("account_pair") == account_pair]
    if template_id is not None:
        entries = [e for e in entries if e.get("template_id") == template_id]
    if log_direction is not None:
        entries = [e for e in entries if e.get("log_direction") == log_direction]
    if partial_id is not None:
        pid = partial_id.lower()
        entries = [
            e for e in entries
            if (e.get("wire_id", "").startswith(pid) or e.get("semantic_id", "").startswith(pid))
        ]
    entries = list(reversed(entries))  # newest first
    if last is not None:
        entries = entries[:last]
    return entries


def log_stats(path: Path | None = None) -> dict:
    """Return basic statistics about the log."""
    p = path or default_log_path()
    entries = _load_entries(p)
    if not entries:
        return {"count": 0, "encodes": 0, "decodes": 0, "earliest": None, "latest": None}
    timestamps = [e.get("timestamp", "") for e in entries if e.get("timestamp")]
    return {
        "count": len(entries),
        "encodes": sum(1 for e in entries if e.get("log_direction") == "encode"),
        "decodes": sum(1 for e in entries if e.get("log_direction") == "decode"),
        "earliest": min(timestamps) if timestamps else None,
        "latest": max(timestamps) if timestamps else None,
    }
