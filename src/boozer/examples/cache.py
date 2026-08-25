"""On-disk cache for example lookups, keyed by (formula name, version)
so an upgrade invalidates stale entries automatically.

Not a provider itself — CachingProvider (in __init__.py) wraps another
provider with this, so any provider can be made cache-backed by
composition rather than by re-implementing caching in each one.
"""

from __future__ import annotations

import os
from pathlib import Path

import orjson

from ..models import Formula
from .types import Example

CACHE_DIR = Path(
    os.environ.get("BOOZER_CACHE_DIR", str(Path.home() / ".cache" / "boozer" / "examples"))
)


def _cache_path(formula: Formula) -> Path:
    # Slashes in full_name (e.g. "fluxcd/tap/flux") aren't safe filename
    # characters — key on the short name + version instead.
    key = f"{formula.name}-{formula.version or 'unknown'}"
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in key)
    return CACHE_DIR / f"{safe}.json"


def read(formula: Formula) -> list[Example] | None:
    path = _cache_path(formula)
    try:
        raw = orjson.loads(path.read_bytes())
    except (FileNotFoundError, orjson.JSONDecodeError, OSError):
        return None
    if not isinstance(raw, list):
        return None
    try:
        return [Example(label=item["label"], command=item["command"]) for item in raw]
    except (KeyError, TypeError):
        return None


def write(formula: Formula, examples: list[Example]) -> None:
    """Best-effort — a cache write failing (disk full, read-only home,
    ...) should never surface as an error to the user."""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        payload = orjson.dumps([{"label": e.label, "command": e.command} for e in examples])
        _cache_path(formula).write_bytes(payload)
    except OSError:
        pass
