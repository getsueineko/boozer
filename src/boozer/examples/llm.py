"""Generates examples on demand via a local LM Studio server using its
OpenAI-compatible `/v1/chat/completions` endpoint.

Only stdlib (`urllib`) is used — no extra HTTP client dependency for one
local call.

Disabled by default: set BOOZER_ENABLE_LLM_EXAMPLES=1 to opt in.

Configuration (all optional):
    BOOZER_ENABLE_LLM_EXAMPLES=1
        Enable LLM-generated examples (default: off).

    BOOZER_LM_STUDIO_URL
        LM Studio base URL.
        Default: http://localhost:1234/v1

    BOOZER_LM_STUDIO_MODEL
        Model identifier exposed by LM Studio.
        Default: local-model

    BOOZER_LM_STUDIO_MAX_TOKENS
        Maximum number of generated tokens.
        Default: 1024.

    BOOZER_LM_STUDIO_THINKING
        Enable model thinking/reasoning.
        Default: off.

        Set to 1/true/yes to enable thinking.

        For Qwen3.5 this is passed to the chat template as:
            {"chat_template_kwargs": {"enable_thinking": false}}

    BOOZER_LM_STUDIO_TIMEOUT
        Generation timeout in seconds.
        Default: 90.

The provider intentionally uses non-thinking mode by default. Boozer needs
a short, structured JSON response, not a reasoning trace. This is especially
important for Qwen3.5 models, which enable thinking by default.
"""

from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from urllib.parse import urlparse

from ..models import Formula
from .types import Example


DEFAULT_BASE_URL = "http://localhost:1234/v1"
DEFAULT_MODEL = "local-model"

# Six short examples do not need a large generation budget.
DEFAULT_MAX_TOKENS = 1024

DEFAULT_GENERATION_TIMEOUT = 90.0

# Failing to even reach LM Studio should be near-instant. This is kept
# separate from the generation timeout.
REACHABILITY_TIMEOUT = 1.5

TARGET_COUNT = 6


_PROMPT_TEMPLATE = """You are generating a short command-line cheat sheet.

Formula: {name}
Description: {desc}
Homepage: {homepage}
{caveats_line}
List the {count} most commonly used commands for "{name}".

Respond with ONLY a JSON array, no prose and no markdown code fences,
in exactly this shape:

[{{"label": "Short description", "command": "actual runnable command"}}]

Rules:
- Exactly {count} items, most useful first.
- "command" must be a real, correct invocation of "{name}" itself —
  its actual flags, not a different tool's.
- "label" is 2-5 words, with no trailing punctuation.
- Nothing outside the JSON array.
- Do not explain your choices.
"""


def _is_enabled() -> bool:
    """Whether LLM example generation is enabled."""
    return os.environ.get(
        "BOOZER_ENABLE_LLM_EXAMPLES", ""
    ).strip().lower() in ("1", "true", "yes")


def _base_url() -> str:
    """Return the configured LM Studio API base URL."""
    return os.environ.get(
        "BOOZER_LM_STUDIO_URL",
        DEFAULT_BASE_URL,
    ).rstrip("/")


def _model() -> str:
    """Return the configured LM Studio model identifier."""
    return os.environ.get(
        "BOOZER_LM_STUDIO_MODEL",
        DEFAULT_MODEL,
    )


def _max_tokens() -> int:
    """Return the maximum number of generated tokens."""
    try:
        value = int(
            os.environ.get(
                "BOOZER_LM_STUDIO_MAX_TOKENS",
                DEFAULT_MAX_TOKENS,
            )
        )
        return max(1, value)
    except ValueError:
        return DEFAULT_MAX_TOKENS


def _thinking_enabled() -> bool:
    """Whether LM Studio model thinking/reasoning should be enabled.

    Thinking is intentionally disabled by default because Boozer needs
    a short structured JSON response. Qwen3.5 supports this through the
    `enable_thinking` Jinja variable.
    """
    return os.environ.get(
        "BOOZER_LM_STUDIO_THINKING", ""
    ).strip().lower() in ("1", "true", "yes")


def _generation_timeout() -> float:
    """Return the generation timeout in seconds."""
    try:
        value = float(
            os.environ.get(
                "BOOZER_LM_STUDIO_TIMEOUT",
                DEFAULT_GENERATION_TIMEOUT,
            )
        )
        return max(1.0, value)
    except ValueError:
        return DEFAULT_GENERATION_TIMEOUT


def _is_reachable(base_url: str) -> bool:
    """Fast TCP-level check.

    A non-running LM Studio should fail in ~1.5 seconds rather than waiting
    for the full generation timeout.
    """
    parsed = urlparse(base_url)

    host = parsed.hostname or "localhost"
    port = parsed.port or (
        443 if parsed.scheme == "https" else 80
    )

    try:
        with socket.create_connection(
            (host, port),
            timeout=REACHABILITY_TIMEOUT,
        ):
            return True
    except OSError:
        return False


def _extract_json_array(text: str) -> str | None:
    """Extract the first JSON array from model output.

    Local models may occasionally add markdown fences or a short sentence
    despite the prompt. We tolerate that here because the final consumer
    only needs the JSON array.
    """
    text = text.strip()

    if not text:
        return None

    # Remove markdown fences such as:
    #
    # ```json
    # [...]
    # ```
    if text.startswith("```"):
        text = text.strip("`")

        if text.lower().startswith("json"):
            text = text[4:]

        text = text.strip()

    start = text.find("[")
    end = text.rfind("]")

    if start == -1 or end == -1 or end < start:
        return None

    return text[start : end + 1]


def _chat_completion(prompt: str) -> dict | None:
    """Call LM Studio and return the raw assistant message.

    Thinking is disabled by default through the Qwen-compatible
    `chat_template_kwargs` parameter.

    The complete assistant message is returned so the caller can inspect
    `content`. `reasoning_content` is intentionally not used as a fallback:
    reasoning is not an authoritative source for the requested commands.
    """
    url = f"{_base_url()}/chat/completions"

    body = json.dumps(
        {
            "model": _model(),
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "temperature": 0.1,
            "max_tokens": _max_tokens(),

            # Qwen3.5 uses the `enable_thinking` Jinja variable.
            #
            # False by default:
            #   thinking -> OFF
            #   content  -> direct answer
            #
            # Set BOOZER_LM_STUDIO_THINKING=1 if reasoning is explicitly
            # desired.
            "chat_template_kwargs": {
                "enable_thinking": _thinking_enabled(),
            },
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            req,
            timeout=_generation_timeout(),
        ) as resp:
            payload = json.loads(resp.read())

    except (
        urllib.error.HTTPError,
        urllib.error.URLError,
        TimeoutError,
        OSError,
        ValueError,
    ):
        return None

    try:
        return payload["choices"][0]["message"]
    except (
        KeyError,
        IndexError,
        TypeError,
    ):
        return None


def _parse_examples(text: str) -> list[Example]:
    """Parse model output into Boozer Example objects."""
    json_text = _extract_json_array(text)

    if not json_text:
        return []

    try:
        raw_items = json.loads(json_text)
    except (TypeError, ValueError):
        return []

    if not isinstance(raw_items, list):
        return []

    examples: list[Example] = []

    for item in raw_items:
        if not isinstance(item, dict):
            continue

        label = str(
            item.get("label", "")
        ).strip()

        command = str(
            item.get("command", "")
        ).strip()

        if not label or not command:
            continue

        examples.append(
            Example(
                label=label,
                command=command,
            )
        )

    return examples


class LlmProvider:
    """Last-resort provider for generating command examples.

    The provider asks a local LM Studio model for examples when no curated
    or cached examples are available.

    See the module docstring for configuration.
    """

    def get(self, formula: Formula) -> list[Example] | None:
        if not _is_enabled():
            return None

        base_url = _base_url()

        if not _is_reachable(base_url):
            return None

        caveats_line = (
            f"Caveats: {formula.caveats}\n"
            if formula.caveats
            else ""
        )

        prompt = _PROMPT_TEMPLATE.format(
            name=formula.name,
            desc=formula.desc or "(no description)",
            homepage=formula.homepage or "(none)",
            caveats_line=caveats_line,
            count=TARGET_COUNT,
        )

        message = _chat_completion(prompt)

        if not message:
            return None

        # Only use the normal assistant answer.
        #
        # Do NOT fall back to reasoning_content. If thinking is enabled
        # and the model exhausts max_tokens before producing content,
        # returning reasoning as commands can produce incorrect results.
        content = (
            message.get("content") or ""
        ).strip()

        if not content:
            return None

        examples = _parse_examples(content)

        return examples or None
