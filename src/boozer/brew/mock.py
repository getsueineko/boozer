"""Fake brew responses for development/demo without a real Homebrew
install. Every function here mirrors the *shape* of the real `brew`
output its counterpart in queries.py/info.py would parse, so the rest
of the app can't tell the difference.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone


def is_mock() -> bool:
    return bool(os.environ.get("BREW_TUI_MOCK"))


def leaf_names() -> list[str]:
    return ["ripgrep", "fzf", "htop", "neovim", "jq", "wget", "flux", "ffmpeg", "deno", "yt-dlp"]


SIZES: dict[str, str] = {
    "deno": "268.7MB",
    "ffmpeg": "72.4MB",
    "ripgrep": "5.1MB",
    "fzf": "4.8MB",
    "htop": "1.2MB",
    "neovim": "38.9MB",
    "jq": "1.6MB",
    "wget": "3.9MB",
    "flux": "62.3MB",
    "yt-dlp": "18.2MB",
}

TOTAL_INSTALLED_SIZE = "1.2 GB"
CACHE_SIZE = "3.8 GB"

# --installed --help output for formulae that have no curated examples
# (see curated.py) and LLM examples are off by default — demonstrates
# the "--help" fallback in the examples panel.
HELP_TEXT: dict[str, str] = {
    "flux": (
        "Command line utility for assembling Flux GitOps content.\n\n"
        "Usage:\n  flux [command]\n\n"
        "Available Commands:\n"
        "  bootstrap   Bootstrap toolkit components\n"
        "  get         Get sources and resources\n"
        "  reconcile   Reconcile sources and resources\n"
        "  suspend     Suspend sources and resources\n\n"
        'Use "flux [command] --help" for more information about a command.'
    ),
    "deno": (
        "deno 2.9.5\n"
        "A modern JavaScript and TypeScript runtime\n\n"
        "Usage: deno [OPTIONS] [COMMAND]\n\n"
        "Commands:\n"
        "  run       Run a JavaScript or TypeScript program\n"
        "  test      Run tests\n"
        "  fmt       Format source files\n"
        "  compile   Compile a program to a standalone binary\n\n"
        "Options:\n"
        "  -h, --help     Print help\n"
        "  -V, --version  Print version"
    ),
}

# name -> (installed_version, latest_version). Only formulae that
# should demo something other than "up to date" need an entry here —
# everything else defaults to matching versions (see info_json below).
VERSION_OVERRIDES: dict[str, tuple[str, str]] = {
    "ffmpeg": ("8.0", "8.0"),
    "deno": ("2.9.5", "2.9.5"),
    # Demonstrates the "EXPIRED" banner: newer version available.
    "wget": ("1.24.5", "1.25.0"),
}


def info_json() -> dict:
    now = datetime(2026, 8, 8, tzinfo=timezone.utc).timestamp()
    # name -> (desc, homepage, full_name, license, tap, deps, build_deps, conflicts, installs_90d)
    data: dict[str, tuple] = {
        "ripgrep": ("Search tool like grep, but faster and respects .gitignore", "https://github.com/BurntSushi/ripgrep", "ripgrep", "MIT/Unlicense", "homebrew/core", ["pcre2"], [], [], 210044),
        "fzf": ("Command-line fuzzy finder written in Go", "https://github.com/junegunn/fzf", "fzf", "MIT", "homebrew/core", [], [], [], 180221),
        "htop": ("Improved top (interactive process viewer)", "https://htop.dev/", "htop", "GPL-2.0-only", "homebrew/core", [], [], [], 95120),
        "neovim": ("Ambitious Vim-fork focused on extensibility and usability", "https://neovim.io/", "neovim", "Apache-2.0", "homebrew/core", [], [], [], 140532),
        "jq": ("Lightweight and flexible command-line JSON processor", "https://jqlang.github.io/jq/", "jq", "MIT", "homebrew/core", [], [], [], 300817),
        "wget": ("Internet file retriever", "https://www.gnu.org/software/wget/", "wget", "GPL-3.0-or-later", "homebrew/core", [], [], [], 88012),
        "ffmpeg": ("Complete multimedia processing toolkit", "https://ffmpeg.org/", "ffmpeg", "GPL-3.0-or-later", "homebrew/core", [], [], [], 260900),
        # Illustrates the exact same-name-different-tap collision that
        # boozer.brew.info guards against: this is fluxcd/tap/flux
        # (GitOps CLI), not the unrelated homebrew-core "flux" query
        # language.
        "flux": ("GitOps toolkit for Kubernetes", "https://fluxcd.io/", "fluxcd/tap/flux", "Apache-2.0", "fluxcd/tap", [], [], [], None),
        # Mirrors deno's real dependency graph: runtime deps that are
        # installed, build deps that aren't kept after building, a
        # conflict, and a reverse-dependency from yt-dlp — itself one of
        # "your" leaves.
        "deno": ("Secure runtime for JavaScript and TypeScript", "https://deno.com/", "deno", "MIT", "homebrew/core",
                 ["little-cms2", "sqlite"], ["cmake", "lld", "llvm", "ninja", "pkgconf", "rust"], ["dxpy"], 47442),
        "yt-dlp": ("Feature-rich command-line audio/video downloader", "https://github.com/yt-dlp/yt-dlp", "yt-dlp", "Unlicense", "homebrew/core",
                   ["deno"], [], [], 320980),
        # Not leaves themselves — present only so deno's runtime deps
        # resolve to "installed" (✓) rather than "missing" (✕).
        "little-cms2": ("Small-footprint color management engine", "https://littlecms.com/", "little-cms2", "MIT", "homebrew/core", [], [], [], None),
        "sqlite": ("Command-line interface for SQLite", "https://sqlite.org/index.html", "sqlite", "blessing", "homebrew/core", [], [], [], None),
    }
    formulae = []
    for name, (desc, home, full_name, license_, tap, deps, build_deps, conflicts, installs_90d) in data.items():
        installed_version, stable_version = VERSION_OVERRIDES.get(name, ("1.0.0", "1.0.0"))
        entry = {
            "name": name,
            "full_name": full_name,
            "desc": desc,
            "homepage": home,
            "license": license_,
            "tap": tap,
            "versions": {"stable": stable_version},
            "installed": [{"version": installed_version, "time": int(now) if name == "deno" else None}],
            "caveats": None,
            "dependencies": deps,
            "build_dependencies": build_deps,
            "conflicts_with": conflicts,
        }
        if installs_90d is not None:
            entry["analytics"] = {"install": {"90d": {name: installs_90d}}}
        formulae.append(entry)
    return {"formulae": formulae}
