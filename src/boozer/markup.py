"""Anything passed to a Textual `Static.update()` call is parsed as
Rich markup by default — including text boozer didn't author itself:
brew's `desc`/`caveats`/dependency names, live `--help` output, and
LLM-generated commands. That text routinely contains literal square
brackets (CLI usage syntax like `[OPTIONS]`, or Rust/clap-style help
text like `[env: FOO="..."]`) that Rich's markup parser tries to
interpret as style tags — and can crash on outright, if the bracketed
content looks like an unterminated tag parameter (`MarkupError:
Expected markup value`, seen in practice with real `--help` output).

`escape()` neutralizes any markup syntax in a string so it renders
literally. Use it on every externally-sourced string before
interpolating it into an f-string alongside literal markup we write
ourselves (`[bold]...[/]`, `[dim]...[/]`) — those stay unescaped since
they're intentional.
"""

from rich.markup import escape

__all__ = ["escape"]
