"""Right-hand detail panel: everything boozer knows about the selected
formula. Pure presentation — takes a Formula (+ a size string, fetched
separately/lazily by the app) and renders it. No subprocess calls, no
brew knowledge.

Implemented as a VerticalScroll with a single Static child, not a bare
Static: Textual scrolling clips and offsets *children* of a scrollable
container, it isn't something a plain Static does to its own rendered
text no matter what overflow-y is set to. A formula with a long
dependency/build-dependency list can easily exceed the panel's height,
and VerticalScroll ships with the usual pager keybindings (arrows /
PageUp / PageDown / Home / End) out of the box.
"""

from __future__ import annotations

from textual.containers import VerticalScroll
from textual.widgets import Static

from ..markup import escape
from ..models import Formula
from ..theme import AMBER, GREEN_BRIGHT


class DetailPanel(VerticalScroll):
    """Rendered via an explicit show() call rather than a reactive
    attribute — the async size lookup mutates content for the *same*
    formula object, which a reactive's equality check wouldn't treat as
    a change, so the app drives re-rendering explicitly instead.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.border_title = "INGREDIENTS"

    def compose(self):
        yield Static(id="detail-content")

    def show_error(self, message: str) -> None:
        self.query_one("#detail-content", Static).update(f"[bold red]Error:[/] {escape(message)}")
        self.scroll_home(animate=False)

    def show(self, formula: Formula | None, size_text: str, *, reset_scroll: bool = True) -> None:
        content = self.query_one("#detail-content", Static)

        if formula is None:
            content.update("Select a formula on the left ←")
            if reset_scroll:
                self.scroll_home(animate=False)
            return

        check = f"[{GREEN_BRIGHT}]✓[/]"
        cross = f"[{AMBER}]✕[/]"

        # Everything below except our own literal `[bold]`/`[dim]`/etc
        # tags is data straight from `brew info` — desc, caveats, and
        # dependency names are free text a formula's maintainer wrote,
        # not something boozer controls, and can contain literal
        # brackets that would otherwise crash Rich's markup parser
        # (see boozer/markup.py). Escape all of it.
        lines: list[str] = []
        lines.append(f"[bold]{escape(formula.display_name)}[/]")
        lines.append(escape(formula.desc))
        lines.append("")
        lines.append(f"[bold]Version:[/] {escape(formula.version)}")
        lines.append(f"[bold]Tap:[/] {escape(formula.tap)}")
        lines.append(f"[bold]Homepage:[/] [underline]{escape(formula.homepage)}[/]")
        lines.append(f"[bold]License:[/] {escape(formula.license)}")
        if formula.installs_90d is not None:
            lines.append(f"[bold]Installs (90d):[/] {formula.installs_90d}")

        lines.append("")
        lines.append(f"[bold]Status:[/] {check} Installed")
        lines.append(f"[bold]Size:[/] {escape(size_text)}")
        if formula.installed_date:
            lines.append(f"[bold]Installed on:[/] {formula.installed_date}")

        if formula.conflicts:
            lines.append("")
            lines.append("[bold]Conflicts:[/]")
            for c in formula.conflicts:
                lines.append(f"  {cross} {escape(c)}")

        lines.append("")
        lines.append("[bold]Dependencies:[/]")
        if formula.deps:
            for dep, ok in formula.deps:
                lines.append(f"  {check if ok else cross} {escape(dep)}")
        else:
            lines.append("  [dim](none)[/]")

        if formula.build_deps:
            lines.append("")
            lines.append("[bold]Build dependencies:[/]")
            for dep, ok in formula.build_deps:
                lines.append(f"  {check if ok else cross} {escape(dep)}")

        if formula.required_by:
            lines.append("")
            lines.append("[bold]Required by:[/]")
            for r in formula.required_by:
                lines.append(f"  {check} {escape(r)}")

        if formula.caveats:
            lines.append("")
            lines.append("[bold yellow]Caveats:[/]")
            lines.append(escape(formula.caveats))

        content.update("\n".join(lines))
        if reset_scroll:
            self.scroll_home(animate=False)
