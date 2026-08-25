"""The baseline provider: a small, hand-picked list of examples for
popular formulae. Always available, zero latency, zero network — every
other provider described in provider.py sits in *front* of this one,
not instead of it.
"""

from __future__ import annotations

from ..models import Formula
from .types import Example

_CURATED: dict[str, list[Example]] = {
    "ffmpeg": [
        Example("Convert video", "ffmpeg -i input.mp4 output.mkv"),
        Example("Extract audio", "ffmpeg -i video.mp4 audio.mp3"),
        Example("Resize", "ffmpeg -i in.mp4 -vf scale=1280:-1 out.mp4"),
    ],
    "ripgrep": [
        Example("Search recursively", 'rg "pattern" .'),
        Example("Case insensitive", 'rg -i "pattern"'),
        Example("Only filenames", 'rg -l "pattern"'),
    ],
    "fzf": [
        Example("Fuzzy find files", "fzf"),
        Example("Pipe results in", "find . -type f | fzf"),
        Example("Preview with bat", "fzf --preview 'bat --color=always {}'"),
    ],
    "jq": [
        Example("Pretty-print JSON", "cat file.json | jq ."),
        Example("Extract a field", "jq '.name' file.json"),
        Example("Filter an array", "jq '.[] | select(.active)' file.json"),
    ],
    "wget": [
        Example("Download a file", "wget https://example.com/file.zip"),
        Example("Resume a download", "wget -c https://example.com/file.zip"),
        Example("Mirror a site", "wget -m https://example.com"),
    ],
    "htop": [
        Example("Run it", "htop"),
        Example("Sort by memory", "htop -s PERCENT_MEM"),
    ],
    "neovim": [
        Example("Open a file", "nvim file.txt"),
        Example("Open at a line", "nvim +42 file.txt"),
    ],
    "yt-dlp": [
        Example("Download a video", "yt-dlp <url>"),
        Example("Audio only, best quality", "yt-dlp -x --audio-format mp3 <url>"),
    ],
}


class CuratedProvider:
    def get(self, formula: Formula) -> list[Example] | None:
        return _CURATED.get(formula.name)
