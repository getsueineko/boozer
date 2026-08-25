"""Thin subprocess primitives. Nothing here knows what "a formula" or
"a leaf" is — that belongs in queries.py / info.py. This module exists
so every other module in the package shells out through one place, with
one error-handling convention.
"""

from __future__ import annotations

import subprocess


def run(cmd: list[str]) -> str:
    """Run a command and return its stdout, or raise RuntimeError with a
    human-readable message — never a bare CalledProcessError/OSError
    that would need re-explaining higher up the call stack."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except FileNotFoundError as e:
        raise RuntimeError(
            f"{cmd[0]} was not found in PATH — make sure Homebrew is installed."
        ) from e
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        raise RuntimeError(f"{' '.join(cmd)} failed: {stderr}") from e
    return result.stdout


def du_kb(path: str) -> int:
    """Disk usage of `path` in KiB, or 0 if it can't be measured (missing
    path, `du` unavailable, timeout, ...). Zero is treated as "unknown"
    by callers, not "empty directory", so this never needs to raise."""
    try:
        result = subprocess.run(
            ["du", "-sk", path],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return int(result.stdout.split()[0])
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    return 0


def format_size(kb: int) -> str:
    """KiB as a compact human-readable size: '268.7 MB', '1.2 GB', ..."""
    value = float(kb)
    for unit in ("KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"
