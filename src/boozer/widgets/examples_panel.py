"""'How is this best served?' panel. Pure renderer, like DetailPanel and
WeightPanel — knows nothing about where examples came from (curated
list, disk cache, or a local LLM call; see boozer/examples/provider.py)
and, critically, never calls get_examples() itself.

That last point matters now that LlmProvider is real: a lookup can
involve a network round-trip to a local model with a timeout up to
~45s. If this widget fetched examples synchronously (as an earlier
version did), selecting a formula while the panel is open could freeze
the whole UI for that long. The app fetches in a background worker
(see Boozer._fetch_examples) and only ever hands this widget an
already-resolved result.
"""

from __future__ import annotations

from textual.widgets import Static

from ..examples import Example


class ExamplesPanel(Static):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.border_title = "HOW IS THIS BEST SERVED?"

    def show_loading(self) -> None:
        self.update("Looking that up…")

    def show_examples(self, examples: list[Example] | None) -> None:
        if not examples:
            self.update(
                "No examples in the local knowledge base yet.\n\n"
                "[dim]Press a again to hide command examples.[/dim]"
            )
            return
        width = max(len(e.label) for e in examples) + 2
        lines = [f"  {e.label.ljust(width)}[bold]{e.command}[/bold]" for e in examples]
        self.update("\n".join(lines) + "\n\n[dim]Press a again to hide command examples.[/dim]")
