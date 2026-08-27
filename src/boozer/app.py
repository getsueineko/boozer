"""The Textual App itself. This module's only job is wiring: pull data
from `boozer.brew`, hand it to widgets in `boozer.widgets`, respond to
user input. It intentionally contains no brew/subprocess knowledge and
no example-lookup logic — both live in their own packages.
"""

from __future__ import annotations

import os
from typing import NamedTuple

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Input, Label, ListItem, ListView, Static
from textual.binding import Binding

from . import brew
from .examples import Example, get_examples
from .models import Formula
from .theme import CHEVRON
from .widgets import DetailPanel, ExamplesPanel, ExpiredPanel, WeightPanel


class ExamplesResult(NamedTuple):
    """Either curated/LLM examples, live `--help` output, or neither —
    the panel renders whichever one is populated."""

    examples: list[Example] | None
    help_text: str | None


class Boozer(App):
    CSS_PATH = "boozer.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("ctrl+f", "focus_search", "Search"),
        Binding("escape", "focus_list", "List"),
        Binding("a", "toggle_examples", "How is this best served?"),
    ]
    TITLE = ""
    # This app has one deliberate visual identity and a small, fixed set
    # of actions already reachable via BINDINGS — the command palette
    # (ctrl+p) doesn't add anything here, so it's disabled outright
    # rather than just hidden or re-themed.
    ENABLE_COMMAND_PALETTE = False

    def __init__(self) -> None:
        super().__init__()
        self.all_formulae: list[Formula] = []
        self.size_cache: dict[str, str] = {}
        # A name present in this dict means "already looked up" —
        # distinct from "not fetched yet".
        self.examples_cache: dict[str, ExamplesResult] = {}
        self._current_formula: Formula | None = None

    def compose(self) -> ComposeResult:
        yield Static(id="app-header")
        with Horizontal(id="main-row"):
            with Vertical(id="left-col"):
                with Vertical(id="search-box"):
                    yield Input(placeholder="Search by name or description…", id="search")
                with Vertical(id="list-box"):
                    yield ListView(id="list")
                yield WeightPanel(id="weight")
            with Vertical(id="right-col"):
                yield ExpiredPanel(id="expired")
                yield DetailPanel(id="detail")
                yield ExamplesPanel(id="examples")
        yield Footer()

    def on_mount(self) -> None:
        search_box = self.query_one("#search-box")
        search_box.border_title = "WHAT'LL I DRINK?"

        list_box = self.query_one("#list-box")
        list_box.border_title = "ON THE SHELF IN THE FRIDGE"

        self._set_header(loading=True)

        weight = self.query_one("#weight", WeightPanel)
        weight.border_title = "CALORIES"
        weight.show("calculating…", "calculating…")

        self.run_worker(self._load, exclusive=True, thread=True)
        self.run_worker(self._load_weight, exclusive=False, thread=True)

    def _set_header(self, *, loading: bool = False, error: bool = False, count: int = 0) -> None:
        host = os.uname().nodename.upper()
        if loading:
            status = "loading…"
        elif error:
            status = "ERROR"
        else:
            status = f"{count} FORMULAE"
        self.query_one("#app-header", Static).update(
            f"-= BOOZER {host} =-\nWhat do I drink there? // {status}"
        )

    # -- background loading ------------------------------------------------

    def _load(self) -> None:
        try:
            names = brew.get_leaves()
            formulae = brew.get_info(names)
        except Exception as e:  # noqa: BLE001 — surface any error in the UI, never crash
            self.call_from_thread(self._on_error, str(e))
            return
        self.call_from_thread(self._on_loaded, formulae)

    def _on_error(self, message: str) -> None:
        self._set_header(error=True)
        detail = self.query_one("#detail", DetailPanel)
        detail.update(f"[bold red]Error:[/] {message}")

    def _on_loaded(self, formulae: list[Formula]) -> None:
        self.all_formulae = formulae
        self._set_header(count=len(formulae))
        self._populate(formulae)
        self.query_one("#list", ListView).focus()

    def _load_weight(self) -> None:
        installed_size = brew.get_total_installed_size()
        cache_size = brew.get_homebrew_cache_size()
        self.call_from_thread(self._on_weight_loaded, installed_size, cache_size)

    def _on_weight_loaded(self, installed_size: str, cache_size: str) -> None:
        self.query_one("#weight", WeightPanel).show(installed_size, cache_size)

    # -- list / selection ----------------------------------------------------

    def _populate(self, formulae: list[Formula]) -> None:
        list_view = self.query_one("#list", ListView)
        list_view.clear()
        for i, f in enumerate(formulae):
            name_col = f.name.ljust(16)
            item = ListItem(
                Label(f"[{CHEVRON}]›[/] [bold]{name_col}[/bold][dim]{f.desc[:48]}[/dim]")
            )
            if i % 2 == 1:
                item.add_class("row-odd")
            item.formula = f  # type: ignore[attr-defined]
            list_view.append(item)
        if formulae:
            list_view.index = 0
            self._select(formulae[0])
        else:
            self._select(None)

    def _select(self, formula: Formula | None) -> None:
        self._current_formula = formula

        expired = self.query_one("#expired", ExpiredPanel)
        expired.show(formula)

        detail = self.query_one("#detail", DetailPanel)
        if formula is None:
            detail.show(None, "")
            return

        cached_size = self.size_cache.get(formula.name)
        detail.show(formula, cached_size or "calculating…")
        if cached_size is None:
            self.run_worker(
                lambda f=formula: self._fetch_size(f),
                thread=True,
                name=f"size-{formula.name}",
            )

        # Examples are looked up lazily: only fetch (and only ever hit
        # the network or spawn --help) if the panel is actually visible
        # right now. Navigating the list with the panel closed should
        # never trigger an LLM call or a subprocess.
        examples_panel = self.query_one("#examples", ExamplesPanel)
        if examples_panel.has_class("visible"):
            self._show_examples_for(formula)

    def _fetch_size(self, formula: Formula) -> None:
        size = brew.get_installed_size(formula.name)
        self.call_from_thread(self._on_size_ready, formula.name, size)

    def _on_size_ready(self, name: str, size: str) -> None:
        self.size_cache[name] = size
        if self._current_formula is not None and self._current_formula.name == name:
            self.query_one("#detail", DetailPanel).show(self._current_formula, size)

    def _show_examples_for(self, formula: Formula) -> None:
        """Show a cached result immediately, or a loading placeholder
        plus a background fetch. Never calls get_examples() or
        get_help_text() on the UI thread — a lookup can be a network
        round-trip to a local LLM (see boozer/examples/llm.py) or a
        subprocess call that could hang on a misbehaving binary."""
        panel = self.query_one("#examples", ExamplesPanel)
        cached = self.examples_cache.get(formula.name)
        if cached is not None:
            self._render_examples_result(panel, formula.name, cached)
            return
        panel.show_loading()
        self.run_worker(
            lambda f=formula: self._fetch_examples(f),
            thread=True,
            name=f"examples-{formula.name}",
        )

    def _fetch_examples(self, formula: Formula) -> None:
        examples = get_examples(formula)
        help_text = None
        if not examples:
            # Default fallback: every well-behaved CLI tool answers
            # --help, and unlike curated/LLM examples this describes
            # whatever is *actually* installed, not a guess.
            help_text = brew.get_help_text(formula.name)
        result = ExamplesResult(examples=examples, help_text=help_text)
        self.call_from_thread(self._on_examples_result, formula.name, result)

    def _on_examples_result(self, name: str, result: ExamplesResult) -> None:
        self.examples_cache[name] = result
        if self._current_formula is not None and self._current_formula.name == name:
            panel = self.query_one("#examples", ExamplesPanel)
            if panel.has_class("visible"):
                self._render_examples_result(panel, name, result)

    def _render_examples_result(self, panel: ExamplesPanel, name: str, result: ExamplesResult) -> None:
        if result.examples:
            panel.show_examples(result.examples)
        elif result.help_text:
            panel.show_help_text(name, result.help_text)
        else:
            panel.show_unavailable(name)

    # -- events ---------------------------------------------------------------

    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.lower().strip()
        filtered = [f for f in self.all_formulae if query in f.searchable] if query else self.all_formulae
        self._populate(filtered)

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.item is not None and hasattr(event.item, "formula"):
            self._select(event.item.formula)  # type: ignore[attr-defined]

    def action_focus_search(self) -> None:
        self.query_one("#search", Input).focus()

    def action_focus_list(self) -> None:
        self.query_one("#list", ListView).focus()

    def action_toggle_examples(self) -> None:
        panel = self.query_one("#examples", ExamplesPanel)
        panel.toggle_class("visible")
        if panel.has_class("visible") and self._current_formula is not None:
            self._show_examples_for(self._current_formula)


def main() -> None:
    Boozer().run()


if __name__ == "__main__":
    main()
