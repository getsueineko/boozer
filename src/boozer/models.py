"""Domain model.

Deliberately dependency-free: no subprocess, no Textual, no I/O of any
kind. Anything that touches brew lives in `boozer.brew`; anything that
touches the terminal lives in `boozer.widgets` / `boozer.app`. This
module is what both of those talk *through*.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Homebrew appends "_N" to a formula's version string when there's a
# "revision" bump — a rebuild triggered by e.g. a dependency's ABI
# changing, with no change to the upstream version itself (see `brew
# info`'s `revision` field). `installed[].version` includes this
# suffix; `versions.stable` never does. Comparing the two directly
# would treat "0.2.2" and "0.2.2_1" as different versions when they're
# the same upstream release — strip the suffix before comparing.
_REVISION_SUFFIX = re.compile(r"_\d+$")


def _without_revision(version: str) -> str:
    return _REVISION_SUFFIX.sub("", version)


@dataclass
class Formula:
    """One installed-on-request Homebrew formula, enriched with
    everything the detail panel needs to render in a single pass."""

    name: str
    full_name: str = ""
    desc: str = ""
    homepage: str = ""
    version: str = ""
    latest_version: str = ""
    license: str = ""
    tap: str = ""
    caveats: str = ""
    conflicts: list[str] = field(default_factory=list)
    deps: list[tuple[str, bool]] = field(default_factory=list)          # (name, currently installed)
    build_deps: list[tuple[str, bool]] = field(default_factory=list)    # (name, currently installed)
    required_by: list[str] = field(default_factory=list)
    installs_90d: int | None = None
    installed_date: str = ""

    @property
    def searchable(self) -> str:
        return f"{self.name} {self.desc}".lower()

    @property
    def display_name(self) -> str:
        """Show the tap for non-core formulae, e.g. fluxcd/tap/flux."""
        return self.full_name if self.full_name and "/" in self.full_name else self.name

    @property
    def is_outdated(self) -> bool:
        """True if a newer version than what's installed is known to
        exist. `latest_version` comes from `versions.stable` in `brew
        info` — the formula definition's current version, independent
        of what's actually installed. Compares with revision suffixes
        stripped (see _without_revision) so e.g. installed "0.2.2_1"
        against stable "0.2.2" is correctly NOT outdated — same
        release, just rebuilt."""
        if not self.latest_version:
            return False
        return _without_revision(self.latest_version) != _without_revision(self.version)
