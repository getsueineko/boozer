"""The pluggable-provider design for "How is this best served?".

STATUS: `CuratedProvider` (curated.py) and `LlmProvider` (llm.py, backed
by cache.py) are real, wired-up implementations — see
examples/__init__.py for how they're chained. `TldrProvider` below is
still a design sketch, not implemented.

--------------------------------------------------------------------
Why a provider chain instead of one bigger dict?
--------------------------------------------------------------------
The curated list in curated.py covers ~10 formulae by hand — great
quality where it exists, but it doesn't scale to "every formula
someone might have installed". The chain tries cheapest/most-trustworthy
sources first and falls through:

  1. CuratedProvider        — hand-picked, in this repo, zero latency,
                               zero network/process dependency.
  2. CachingProvider(Llm..) — disk cache first (~/.cache/boozer/examples,
                               instant, offline); on a miss, asks a
                               local LM Studio model and writes the
                               result through to the cache. Opt-in via
                               BOOZER_ENABLE_LLM_EXAMPLES=1 — see
                               llm.py's module docstring.
  3. TldrProvider (sketch)  — not implemented. Would fetch the
                               community-maintained tldr-pages cheat
                               sheet, giving good coverage without
                               needing a local model at all. Left as a
                               sketch below; slotting it in later is
                               just `CachingProvider(TldrProvider())`
                               ahead of the LLM provider in
                               examples/__init__.py's `_PROVIDERS` list.

`get_examples()` in __init__.py walks the list and returns the first
non-empty result, truncated to MAX_EXAMPLES. Each provider only ever
answers "what do I know" — the fallback ordering lives in one place.

--------------------------------------------------------------------
Interface
--------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Protocol

from ..models import Formula
from .types import Example


class ExampleProvider(Protocol):
    """A source of usage examples for a formula.

    `get()` returns `None` to mean "I don't have an opinion about this
    formula" (try the next provider) — as distinct from returning `[]`,
    which would mean "I checked, and there genuinely are no examples"
    and would stop the chain. In practice today's providers only ever
    return `None` or a non-empty list; `[]` is reserved in case a future
    provider wants to positively assert absence.

    Providers must not block the UI thread — `get_examples()` is called
    from a background worker (the same pattern used for
    `get_installed_size()`), but a provider that hits the network
    should still apply its own short timeout rather than relying on the
    caller to enforce one (see llm.py for the reachability-check /
    generation-timeout split this matters for in practice).
    """

    def get(self, formula: Formula) -> list[Example] | None:
        ...


class TldrProvider:
    """Not implemented. Would fetch
    https://github.com/tldr-pages/tldr community cheat sheets and adapt
    their example blocks into `Example`s — good coverage of common CLI
    tools without needing a local model running at all.

    Open design questions to resolve before implementing:
    - tldr pages are Markdown with a loose but consistent format
      (`- Do a thing:` followed by `` `command {{placeholder}}` ``) —
      needs a small parser, not a full Markdown engine.
    - Formula name -> tldr page name isn't always 1:1 (tldr pages are
      organised by `common/`, `osx/`, `linux/`, etc, and the slug isn't
      always the brew formula name) — needs a lookup/fallback strategy.
    - Network use needs the same explicit opt-in as LlmProvider, plus a
      short timeout and graceful fallback to the next provider.
    - Should reuse cache.py the same way LlmProvider does, via
      `CachingProvider(TldrProvider())`.
    """

    def get(self, formula: Formula) -> list[Example] | None:
        raise NotImplementedError("design stage — see module docstring")
