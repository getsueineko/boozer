"""Compact disk-usage summary ('CALORIES'): total installed size and
Homebrew cache size. Pure renderer — the app fetches both numbers in a
background worker and calls show() when they're ready.
"""

from __future__ import annotations

from textual.widgets import Static


class WeightPanel(Static):
    def show(self, installed_size: str, cache_size: str) -> None:
        self.update(
            f"[bold]Installed:[/] {installed_size}\n"
            f"[bold]Homebrew cache:[/] {cache_size}"
        )
