"""Right-hand detail panel: everything boozer knows about the selected
formula. Pure presentation — takes a Formula (+ a size string, fetched
separately/lazily by the app) and renders it. No subprocess calls, no
brew knowledge.
"""

from __future__ import annotations

from textual.widgets import Static

from ..models import Formula
from ..theme import AMBER, GREEN_BRIGHT


class DetailPanel(Static):
    """Rendered via an explicit show() call rather than a reactive
    attribute — the async size lookup mutates content for the *same*
    formula object, which a reactive's equality check wouldn't treat as
    a change, so the app drives re-rendering explicitly instead.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.border_title = "INGREDIENTS"

    def show(self, formula: Formula | None, size_text: str) -> None:
        if formula is None:
            self.update("Select a formula on the left ←")
            return

        check = f"[{GREEN_BRIGHT}]✓[/]"
        cross = f"[{AMBER}]✕[/]"

        lines: list[str] = []
        lines.append(f"[bold]{formula.display_name}[/]")
        lines.append(formula.desc)
        lines.append("")
        lines.append(f"[bold]Version:[/] {formula.version}")
        lines.append(f"[bold]Tap:[/] {formula.tap}")
        lines.append(f"[bold]Homepage:[/] [underline]{formula.homepage}[/]")
        lines.append(f"[bold]License:[/] {formula.license}")
        if formula.installs_90d is not None:
            lines.append(f"[bold]Installs (90d):[/] {formula.installs_90d}")

        lines.append("")
        lines.append(f"[bold]Status:[/] {check} Installed")
        lines.append(f"[bold]Size:[/] {size_text}")
        if formula.installed_date:
            lines.append(f"[bold]Installed on:[/] {formula.installed_date}")

        if formula.conflicts:
            lines.append("")
            lines.append("[bold]Conflicts:[/]")
            for c in formula.conflicts:
                lines.append(f"  {cross} {c}")

        lines.append("")
        lines.append("[bold]Dependencies:[/]")
        if formula.deps:
            for dep, ok in formula.deps:
                lines.append(f"  {check if ok else cross} {dep}")
        else:
            lines.append("  [dim](none)[/]")

        if formula.build_deps:
            lines.append("")
            lines.append("[bold]Build dependencies:[/]")
            for dep, ok in formula.build_deps:
                lines.append(f"  {check if ok else cross} {dep}")

        if formula.required_by:
            lines.append("")
            lines.append("[bold]Required by:[/]")
            for r in formula.required_by:
                lines.append(f"  {check} {r}")

        if formula.caveats:
            lines.append("")
            lines.append("[bold yellow]Caveats:[/]")
            lines.append(formula.caveats)

        self.update("\n".join(lines))
