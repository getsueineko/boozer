"""Runs `<name> --help` (falling back to `-h`) for whatever formula is
selected. This is the universal fallback for the "How is this best
served?" panel: unlike curated examples or an LLM call, every
well-behaved CLI tool supports one of these flags, and the output is
guaranteed to describe whatever's *actually installed* — not a guess.
"""

from __future__ import annotations

import subprocess

from . import mock

HELP_FLAGS = ("--help", "-h")
TIMEOUT_SECONDS = 5


def get_help_text(name: str) -> str | None:
    if mock.is_mock():
        return mock.HELP_TEXT.get(name)

    for flag in HELP_FLAGS:
        try:
            result = subprocess.run(
                [name, flag],
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        # Plenty of CLI tools print --help to stderr, not stdout, and a
        # nonzero exit code for --help is common enough (some tools
        # treat "no subcommand given" as an error) that it's not a
        # reliable signal either way — the only thing that matters here
        # is whether we got *some* text back.
        output = f"{result.stdout or ''}{result.stderr or ''}".strip()
        if output:
            return output
    return None
