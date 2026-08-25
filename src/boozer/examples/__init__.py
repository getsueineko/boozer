"""'How is this best served?' — a short cheat-sheet of the most-used
commands for a formula.

Public surface:

    get_examples(formula) -> list[Example] | None

Internally this walks a prioritized list of providers (see provider.py
for the full design) and returns the first non-empty result, truncated
to MAX_EXAMPLES:

    1. CuratedProvider          — hand-picked, always available
    2. CachingProvider(LlmProvider()) — disk cache, then a local LM
       Studio model on a cache miss (opt-in, see llm.py)

TldrProvider (provider.py) is designed but not implemented yet.
"""

from __future__ import annotations

from . import cache
from ..models import Formula
from .curated import CuratedProvider
from .llm import LlmProvider
from .provider import ExampleProvider
from .types import Example

MAX_EXAMPLES = 6


class CachingProvider:
    """Wraps another provider with a read-through/write-through disk
    cache (cache.py), so a given (formula, version) only ever hits the
    wrapped provider once. Composition rather than every slow provider
    re-implementing its own caching.
    """

    def __init__(self, inner: ExampleProvider) -> None:
        self._inner = inner

    def get(self, formula: Formula) -> list[Example] | None:
        cached = cache.read(formula)
        if cached:
            return cached
        result = self._inner.get(formula)
        if result:
            cache.write(formula, result)
        return result


_PROVIDERS: list[ExampleProvider] = [
    CuratedProvider(),
    CachingProvider(LlmProvider()),
    # Future: CachingProvider(TldrProvider()) — see provider.py
]


def get_examples(formula: Formula) -> list[Example] | None:
    for provider in _PROVIDERS:
        result = provider.get(formula)
        if result:
            return result[:MAX_EXAMPLES]
    return None


__all__ = ["Example", "get_examples", "MAX_EXAMPLES"]

