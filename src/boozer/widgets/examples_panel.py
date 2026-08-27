"""'How is this best served?' panel. Pure renderer, like DetailPanel and
WeightPanel — knows nothing about where content came from (curated
list, disk cache, a local LLM call, or a live `--help` invocation; see
boozer/examples/provider.py and boozer/brew/help.py) and, critically,
never calls get_examples() or get_help_text() itself.

That matters because either source can be slow: an LLM lookup can be a
network round-trip with a timeout up to ~90s, and even `--help` is a
subprocess call that could hang on a misbehaving binary. If this widget
fetched content synchronously, selecting a formula while the panel is
open could freeze the whole UI. The app fetches in a background worker
(see Boozer._fetch_examples) and only ever hands this widget an
already-resolved result.
"""

from __future__ import annotations

from textual.widgets import Static

from ..examples import Example

_HINT = "\n\n[dim]Press a again to hide command examples.[/dim]"


class ExamplesPanel(Static):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.border_title = "HOW IS THIS BEST SERVED?"

    def show_loading(self) -> None:
        self.update("Looking that up…")

    def show_examples(self, examples: list[Example]) -> None:
        width = max(len(e.label) for e in examples) + 2
        lines = [f"  {e.label.ljust(width)}[bold]{e.command}[/bold]" for e in examples]
        self.update("\n".join(lines) + _HINT)

    def show_help_text(self, name: str, text: str) -> None:
        # No curated/cached/LLM examples — fall back to real, live
        # `--help` output for whatever's actually installed. Capped so
        # a chatty --help doesn't blow out the panel height; #detail
        # scrolls but this panel doesn't, by design (it should stay a
        # quick glance, not a pager).
        lines = text.splitlines()
        MAX_LINES = 24
        shown = lines[:MAX_LINES]
        truncated = len(lines) > MAX_LINES
        body = "\n".join(shown)
        if truncated:
            body += f"\n[dim]… ({len(lines) - MAX_LINES} more lines, run `{name} --help` to see all)[/dim]"
        self.update(f"[dim]No curated examples yet — showing `{name} --help`:[/dim]\n\n{body}" + _HINT)

    def show_unavailable(self, name: str) -> None:
        self.update(
            f"No examples in the local knowledge base, and `{name} --help` "
            "produced no output.\n\n"
            f"[dim]Press a again to hide this panel.[/dim]"
        )
