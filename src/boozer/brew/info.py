"""Turns raw `brew` JSON into `Formula` objects.

This is where the tap name-collision fix lives (see module docstring
below) and where per-formula dependency/required-by status gets
cross-referenced against the full installed set.
"""

from __future__ import annotations

from datetime import datetime, timezone

from ..models import Formula
from .queries import (
    get_formula_info_by_full_name,
    get_full_name_map,
    get_installed_json,
)


def _installs_90d(item: dict) -> int | None:
    try:
        period = ((item.get("analytics") or {}).get("install") or {}).get("90d") or {}
        if not period:
            return None
        return sum(int(v) for v in period.values())
    except Exception:
        return None


def _installed_date(item: dict) -> str:
    try:
        installed = item.get("installed") or []
        if not installed:
            return ""
        # See the comment in get_info() — the currently active version
        # is the last entry, not the first, when an old version hasn't
        # been cleaned up.
        ts = installed[-1].get("time")
        if not ts:
            return ""
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        return ""


def get_info(leaf_names: list[str]) -> list[Formula]:
    """Build one Formula per leaf name.

    Name resolution: we fetch info via `--installed` (all installed
    formulae in one call) rather than querying `brew info --json=v2
    <name> ...` per formula name. Some short names collide between taps
    (e.g. the core formula `flux`, an unrelated query language, vs
    `fluxcd/tap/flux`, the GitOps CLI many people actually install) — a
    name-based lookup can silently resolve to the wrong formula.
    `--installed` resolves formulae from their actual install receipts
    instead, so it normally can't get confused by a same-named formula
    in a different tap.

    As a second, independent check, we cross-reference every formula's
    full (tap-qualified) name against `brew list --formula --full-name`
    — which reads directly off the Cellar/receipts and can't be
    ambiguous. If it disagrees with what the bulk lookup resolved a name
    to, that bulk entry is for the WRONG formula — not just its display
    label, but its desc/homepage/version/license/etc too — so we
    re-fetch *that one formula* by its exact qualified name (which brew
    can't get wrong) and use that instead. This only costs an extra
    `brew info` call for the rare ambiguous case; everything else stays
    on the fast bulk path.
    """
    if not leaf_names:
        return []

    raw = get_installed_json()
    all_items = raw.get("formulae", [])
    by_name = {item.get("name"): item for item in all_items}
    installed_names = set(by_name.keys())
    full_name_map = get_full_name_map()

    # Reverse-dependency index: for every installed formula, note which
    # other installed formulae list it as a (build) dependency. This is
    # what "Required By" surfaces — e.g. you `brew install`ed X
    # yourself, but Y (which you also installed yourself) happens to
    # need it too.
    required_by: dict[str, list[str]] = {}
    for item in all_items:
        consumer = item.get("name")
        for dep in (item.get("dependencies") or []) + (item.get("build_dependencies") or []):
            required_by.setdefault(dep, []).append(consumer)

    formulae: list[Formula] = []
    for name in leaf_names:
        item = by_name.get(name)
        if item is None:
            continue

        true_full_name = full_name_map.get(name)
        bulk_full_name = item.get("full_name") or name
        if true_full_name and true_full_name != bulk_full_name:
            corrected = get_formula_info_by_full_name(true_full_name)
            if corrected is not None:
                item = corrected

        # `installed` can have more than one entry if an old version
        # hasn't been cleaned up after `brew upgrade` (Homebrew doesn't
        # always auto-cleanup). Entries are listed oldest-first, so the
        # currently active version — the one actually in use — is the
        # LAST one, not the first. Reading installed[0] here would keep
        # showing a stale version (and a stuck EXPIRED banner) even
        # right after upgrading.
        installed = item.get("installed") or [{}]
        current_install = installed[-1]
        stable_version = item.get("versions", {}).get("stable", "") or ""
        version = current_install.get("version") or stable_version

        raw_deps = item.get("dependencies") or []
        raw_build_deps = item.get("build_dependencies") or []

        formulae.append(
            Formula(
                name=name,
                full_name=true_full_name or item.get("full_name") or name,
                desc=item.get("desc") or "(no description)",
                homepage=item.get("homepage") or "",
                version=version,
                latest_version=stable_version,
                license=item.get("license") or "Unknown",
                tap=item.get("tap") or "unknown",
                caveats=(item.get("caveats") or "").strip(),
                conflicts=item.get("conflicts_with") or [],
                deps=[(d, d in installed_names) for d in raw_deps],
                build_deps=[(d, d in installed_names) for d in raw_build_deps],
                required_by=sorted(set(required_by.get(name, [])) - {name}),
                installs_90d=_installs_90d(item),
                installed_date=_installed_date(item),
            )
        )

    formulae.sort(key=lambda f: f.name)
    return formulae
