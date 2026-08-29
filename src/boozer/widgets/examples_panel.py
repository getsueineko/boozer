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

Implemented as a VerticalScroll with a single Static child, not a bare
Static: Textual scrolling clips and offsets *children* of a scrollable
container, it isn't something a plain Static does to its own rendered
text no matter what overflow-y is set to. VerticalScroll also ships
with the usual pager keybindings (arrows / PageUp / PageDown / Home /
End) out of the box, so long content (a chatty --help, or long LLM
commands) scrolls within the box — capped at `max-height: 40%` in
boozer.tcss — instead of overflowing the layout or being hard-truncated.

Content is built as `rich.text.Text` via boozer.markup's plain()/
styled() rather than f-string markup, since real --help output reliably
crashes Rich's markup parser otherwise — see boozer/markup.py.
"""

from __future__ import annotations

from rich.text import Text
from textual.containers import VerticalScroll
from textual.widgets import Static

from ..examples import Example
from ..markup import plain, styled

_HINT = "\n\n[dim]Press a again to hide command examples.[/dim]"

# Not a UX-driven truncation (scrolling handles normal --help output
# fine) — just a sane ceiling against a genuinely pathological command
# that dumps megabytes to stdout.
_SAFETY_LINE_CAP = 500


class ExamplesPanel(VerticalScroll):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.border_title = "HOW IS THIS BEST SERVED?"

    def compose(self):
        yield Static(id="examples-content")

    def _content(self) -> Static:
        return self.query_one("#examples-content", Static)

    def show_loading(self) -> None:
        self._content().update("Looking that up…")
        self.scroll_home(animate=False)

    def show_examples(self, examples: list[Example]) -> None:
        # label/command come from curated.py (hand-written, effectively
        # trusted) or an LLM response (not trusted at all) — build via
        # plain() either way so neither can crash the markup parser or
        # inject bogus styling. Command gets bold via Text's structural
        # style=, not a markup tag wrapped around untrusted content.
        width = max(len(e.label) for e in examples) + 2
        result = Text()
        for i, e in enumerate(examples):
            if i:
                result.append("\n")
            result.append(f"  {e.label.ljust(width)}")
            result.append(e.command, style="bold")
        result.append_text(styled(_HINT))
        self._content().update(result)
        self.scroll_home(animate=False)

    def show_help_text(self, name: str, text: str) -> None:
        # No curated/cached/LLM examples — fall back to real, live
        # `--help` output for whatever's actually installed. --help
        # text routinely contains literal brackets (`[OPTIONS]`,
        # `[--flag=<value>]`, clap/Rust-style `[env: FOO="..."]`) that
        # reliably crash Rich's markup parser if run through it at all
        # — see boozer/markup.py. Built as Text, not an f-string; `name`
        # goes through plain() too even though formula names are
        # generally safe, to keep this consistent and not rely on that.
        lines = text.splitlines()
        shown = lines[:_SAFETY_LINE_CAP]
        truncated = len(lines) > _SAFETY_LINE_CAP

        result = styled("[dim]No curated examples yet — showing `[/dim]")
        result.append_text(plain(name))
        result.append_text(styled("[dim] --help`:[/dim]\n\n"))
        result.append_text(plain("\n".join(shown)))
        if truncated:
            result.append_text(styled(f"\n[dim]… ({len(lines) - _SAFETY_LINE_CAP} more lines, run `[/dim]"))
            result.append_text(plain(name))
            result.append_text(styled("[dim] --help` to see all)[/dim]"))
        result.append_text(styled(_HINT))
        self._content().update(result)
        self.scroll_home(animate=False)

    def show_unavailable(self, name: str) -> None:
        result = styled("No examples in the local knowledge base, and `")
        result.append_text(plain(name))
        result.append_text(styled(" --help` produced no output.\n\n[dim]Press a again to hide this panel.[/dim]"))
        self._content().update(result)
        self.scroll_home(animate=False)
