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
"""

from __future__ import annotations

from textual.containers import VerticalScroll
from textual.widgets import Static

from ..examples import Example
from ..markup import escape

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
        # trusted) or an LLM response (not trusted at all) — escape
        # both so neither can crash the markup parser or inject bogus
        # styling; pad width BEFORE escaping so alignment reflects the
        # real visible text, not the (usually longer) escaped form.
        width = max(len(e.label) for e in examples) + 2
        lines = [
            f"  {escape(e.label.ljust(width))}[bold]{escape(e.command)}[/bold]"
            for e in examples
        ]
        self._content().update("\n".join(lines) + _HINT)
        self.scroll_home(animate=False)

    def show_help_text(self, name: str, text: str) -> None:
        # No curated/cached/LLM examples — fall back to real, live
        # `--help` output for whatever's actually installed. --help
        # text routinely contains literal brackets (usage syntax like
        # `[OPTIONS]`, clap/Rust-style `[env: FOO="..."]`) that can
        # outright crash Rich's markup parser if left unescaped — see
        # boozer/markup.py.
        text = escape(text)
        lines = text.splitlines()
        shown = lines[:_SAFETY_LINE_CAP]
        truncated = len(lines) > _SAFETY_LINE_CAP
        body = "\n".join(shown)
        if truncated:
            body += f"\n[dim]… ({len(lines) - _SAFETY_LINE_CAP} more lines, run `{escape(name)} --help` to see all)[/dim]"
        self._content().update(f"[dim]No curated examples yet — showing `{escape(name)} --help`:[/dim]\n\n{body}" + _HINT)
        self.scroll_home(animate=False)

    def show_unavailable(self, name: str) -> None:
        self._content().update(
            f"No examples in the local knowledge base, and `{escape(name)} --help` "
            "produced no output.\n\n"
            f"[dim]Press a again to hide this panel.[/dim]"
        )
        self.scroll_home(animate=False)
