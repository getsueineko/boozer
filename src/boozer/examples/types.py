"""Data contract for the examples module. Deliberately tiny — every
provider (curated, tldr, LLM, cache, ...) speaks this and only this, so
the UI layer never needs to know which provider answered."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Example:
    """One usage example: a short human label and the command it runs.

    label   e.g. "Convert video"      — what the command does, a few words
    command e.g. "ffmpeg -i in.mp4 out.mkv" — copy-pasteable, no prose
    """
    label: str
    command: str
