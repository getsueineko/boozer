"""Everything that talks to `brew`, `du`, and the filesystem lives here.
Nothing outside this package should import `subprocess` directly, and
nothing outside this package needs to know that any of this shells out
at all — the public surface is just:

    get_leaves() -> list[str]
    get_info(leaf_names) -> list[Formula]
    get_installed_size(name) -> str
    get_total_installed_size() -> str
    get_homebrew_cache_size() -> str
"""

from .info import get_info
from .queries import (
    get_homebrew_cache_size,
    get_installed_size,
    get_leaves,
    get_total_installed_size,
)

__all__ = [
    "get_leaves",
    "get_info",
    "get_installed_size",
    "get_total_installed_size",
    "get_homebrew_cache_size",
]
