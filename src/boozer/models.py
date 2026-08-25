"""Domain model.

Deliberately dependency-free: no subprocess, no Textual, no I/O of any
kind. Anything that touches brew lives in `boozer.brew`; anything that
touches the terminal lives in `boozer.widgets` / `boozer.app`. This
module is what both of those talk *through*.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Formula:
    """One installed-on-request Homebrew formula, enriched with
    everything the detail panel needs to render in a single pass."""

    name: str
    full_name: str = ""
    desc: str = ""
    homepage: str = ""
    version: str = ""
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
