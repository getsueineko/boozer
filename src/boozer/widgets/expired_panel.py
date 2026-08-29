"""'EXPIRED' banner: shown above the Ingredients panel only when a
newer version of the selected formula is available than what's
installed. Pure renderer, like the other panels — the version
comparison itself lives on Formula.is_outdated.
"""

from __future__ import annotations

from textual.widgets import Static

from ..markup import styled
from ..models import Formula


class ExpiredPanel(Static):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.border_title = "EXPIRED"

    def show(self, formula: Formula | None) -> None:
        if formula is None or not formula.is_outdated:
            self.remove_class("visible")
            return
        result = styled("⚠ Newer version available: ")
        result.append(formula.latest_version, style="bold")
        result.append(" (installed: ")
        result.append(formula.version)
        result.append(")")
        self.update(result)
        self.add_class("visible")
