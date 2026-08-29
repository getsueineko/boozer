"""Safe construction of styled content for Static widgets.

Textual's `Static.update()` parses whatever string it's given as Rich
markup, including text boozer didn't author itself — `brew info`'s
`desc`/`caveats`, a formula's `--help` output, LLM-generated commands.
That text routinely contains literal square brackets, and it turns out
`rich.markup.escape()` does NOT reliably neutralize all of them: its
regex only escapes `[` when followed by a lowercase letter, `#`, `/`,
or `@` (i.e. things that already look like a real tag start). Ordinary
CLI flag syntax like `[--git-dir=<path>]` — extremely common in
`--help` output — starts with `[-`, which escape() doesn't touch, and
Rich's parser still tries to interpret it as a tag-with-parameter and
crashes with `MarkupError: Expected markup value`.

The only fix that's actually reliable is to not run untrusted text
through the markup parser at all. `rich.text.Text(some_string)` is
never parsed as markup regardless of its content — it's a plain run
of characters, full stop. `plain()` wraps a string that way;
`styled()` is for the small number of literal tags boozer writes
itself (`[bold]`, `[dim]`, ...) and should only ever be called on
strings boozer authored, never on brew/--help/LLM content.

Usage: build up a `rich.text.Text` by concatenating `plain(...)` and
`styled(...)` pieces (Text supports `+`), and pass the result straight
to `Static.update()` — a Text object bypasses markup parsing entirely,
str objects go through it.
"""

from rich.text import Text

__all__ = ["plain", "styled"]


def plain(text: str) -> Text:
    """Untrusted/external text — brew output, --help output, LLM
    commands. Rendered exactly as given; brackets and all."""
    return Text(text)


def styled(markup: str) -> Text:
    """boozer-authored markup only (`[bold]...[/]`, `[dim]...[/]`).
    Never call this on brew/--help/LLM content."""
    return Text.from_markup(markup)
