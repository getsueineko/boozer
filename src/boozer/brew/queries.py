"""One function per `brew` (or `du`) invocation. Each function owns
exactly one command and how to fall back in mock mode — info.py
orchestrates these into the enriched Formula objects the UI wants.
"""

from __future__ import annotations

import os

import orjson

from . import mock
from .cli import du_kb, format_size, run


def get_leaves() -> list[str]:
    """Only formulae installed on request (not pulled in as a dependency)."""
    if mock.is_mock():
        return mock.leaf_names()
    out = run(["brew", "leaves", "--installed-on-request"])
    return [line.strip() for line in out.splitlines() if line.strip()]


def get_installed_json() -> dict:
    """Bulk `brew info` for every installed formula in one call. This is
    the fast path — see info.py for why it's sometimes not trusted for
    a specific formula's description/homepage/etc."""
    if mock.is_mock():
        return mock.info_json()
    out = run(["brew", "info", "--json=v2", "--installed"])
    return orjson.loads(out)


def get_formula_info_by_full_name(full_name: str) -> dict | None:
    """Fetch a single formula's info by its exact tap-qualified name.
    Unambiguous by construction — used as a targeted re-fetch when the
    bulk lookup above turns out to have resolved a short name to the
    wrong tap (see info.py)."""
    try:
        out = run(["brew", "info", "--json=v2", full_name])
        raw = orjson.loads(out)
    except Exception:
        return None
    items = raw.get("formulae", [])
    return items[0] if items else None


def get_full_name_map() -> dict[str, str]:
    """short name -> tap-qualified full name, read straight from Cellar
    receipts via `brew list`. This is the ground truth for "what is
    actually installed" — used to detect when the bulk `--installed`
    lookup resolved a short name to the wrong tap.
    """
    if mock.is_mock():
        return {}
    try:
        out = run(["brew", "list", "--formula", "--full-name"])
    except RuntimeError:
        return {}
    mapping: dict[str, str] = {}
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        short = line.rsplit("/", 1)[-1]
        mapping.setdefault(short, line)
    return mapping


def get_installed_size(name: str) -> str:
    """Disk usage of one installed keg. Not part of `brew info --json`,
    so this is called lazily, on demand, for whichever formula is
    currently selected — never upfront for every formula."""
    if mock.is_mock():
        return mock.SIZES.get(name, "—")
    try:
        cellar = run(["brew", "--cellar"]).strip()
        kb = du_kb(f"{cellar}/{name}")
        return format_size(kb) if kb else "unknown"
    except Exception:
        return "unknown"


def get_total_installed_size() -> str:
    """Total size of everything in the Cellar (leaves + dependencies) —
    a single `du -sk` over the whole tree, not one call per formula."""
    if mock.is_mock():
        return mock.TOTAL_INSTALLED_SIZE
    try:
        cellar = run(["brew", "--cellar"]).strip()
    except RuntimeError:
        return "unknown"
    kb = du_kb(cellar)
    return format_size(kb) if kb else "unknown"


def get_homebrew_cache_size() -> str:
    """Total size of Homebrew's download cache."""
    if mock.is_mock():
        return mock.CACHE_SIZE
    try:
        cache = run(["brew", "--cache"]).strip()
    except RuntimeError:
        return "unknown"
    kb = du_kb(cache)
    return format_size(kb) if kb else "0 KB"
