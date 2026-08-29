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

Content is built as `rich.text.Text` via boozer.markup's plain()/
styled(), not f-string markup: `desc`/`caveats`/dependency names come
straight from `brew info` — free text a formula's maintainer wrote,
not something boozer controls — and can contain literal brackets that
reliably crash Rich's markup parser if run through it. See
boozer/markup.py for why `rich.markup.escape()` alone doesn't fully
solve this.
"""

from __future__ import annotations

from rich.text import Text
from textual.containers import VerticalScroll
from textual.widgets import Static

from ..markup import plain, styled
from ..models import Formula
from ..theme import AMBER, GREEN_BRIGHT


def _field(label: str, value: str) -> Text:
    """`label` is always a short constant boozer writes itself (safe
    for styled()); `value` is external brew data (must go through
    plain())."""
    result = styled(f"[bold]{label}:[/] ")
    result.append_text(plain(value))
    result.append("\n")
    return result


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
        result = styled("[bold red]Error:[/] ")
        result.append_text(plain(message))
        self.query_one("#detail-content", Static).update(result)
        self.scroll_home(animate=False)

    def show(self, formula: Formula | None, size_text: str, *, reset_scroll: bool = True) -> None:
        content = self.query_one("#detail-content", Static)

        if formula is None:
            content.update("Select a formula on the left ←")
            if reset_scroll:
                self.scroll_home(animate=False)
            return

        check = styled(f"[{GREEN_BRIGHT}]✓[/] ")
        cross = styled(f"[{AMBER}]✕[/] ")

        result = Text()
        result.append(formula.display_name, style="bold")
        result.append("\n")
        result.append_text(plain(formula.desc))
        result.append("\n\n")

        result.append_text(_field("Version", formula.version))
        result.append_text(_field("Tap", formula.tap))
        result.append_text(styled("[bold]Homepage:[/] "))
        result.append(formula.homepage, style="underline")
        result.append("\n")
        result.append_text(_field("License", formula.license))
        if formula.installs_90d is not None:
            result.append_text(styled(f"[bold]Installs (90d):[/] {formula.installs_90d}\n"))

        result.append("\n")
        result.append_text(styled("[bold]Status:[/] "))
        result.append_text(check)
        result.append("Installed\n")
        result.append_text(_field("Size", size_text))
        if formula.installed_date:
            result.append_text(styled(f"[bold]Installed on:[/] {formula.installed_date}\n"))

        if formula.conflicts:
            result.append("\n")
            result.append_text(styled("[bold]Conflicts:[/]\n"))
            for c in formula.conflicts:
                result.append("  ")
                result.append_text(cross)
                result.append_text(plain(c))
                result.append("\n")

        result.append("\n")
        result.append_text(styled("[bold]Dependencies:[/]\n"))
        if formula.deps:
            for dep, ok in formula.deps:
                result.append("  ")
                result.append_text(check if ok else cross)
                result.append_text(plain(dep))
                result.append("\n")
        else:
            result.append_text(styled("  [dim](none)[/]\n"))

        if formula.build_deps:
            result.append("\n")
            result.append_text(styled("[bold]Build dependencies:[/]\n"))
            for dep, ok in formula.build_deps:
                result.append("  ")
                result.append_text(check if ok else cross)
                result.append_text(plain(dep))
                result.append("\n")

        if formula.required_by:
            result.append("\n")
            result.append_text(styled("[bold]Required by:[/]\n"))
            for r in formula.required_by:
                result.append("  ")
                result.append_text(check)
                result.append_text(plain(r))
                result.append("\n")

        if formula.caveats:
            result.append("\n")
            result.append_text(styled("[bold yellow]Caveats:[/]\n"))
            result.append_text(plain(formula.caveats))

        content.update(result)
        if reset_scroll:
            self.scroll_home(animate=False)
