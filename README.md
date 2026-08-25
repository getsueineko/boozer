# boozer

> 🐍🍺 boozer — the cheapest dive in the county, where the only thing on tap is snakes (pythons, you know the drill). It runs fast, pours generously, but if you’re looking for a real shitstorm — head over to Go’s [taproom](https://github.com/hzqtc/taproom): the selection is wider and the atmosphere is a whole lot fancier.

TUI for browsing Homebrew formulae you installed yourself (`brew leaves
--installed-on-request`), with an extended detail panel, disk-usage
summary, and a "how is this best served?" command cheat-sheet.

## Run

```bash
pip install -r requirements.txt
python -m boozer
```

Demo without a real brew install:

```bash
BREW_TUI_MOCK=1 python -m boozer
```

### Install as a system command

```bash
uv tool install --python 3.14 -e .
```

This installs `boozer` as a standalone CLI command (editable, so local
changes to the source take effect immediately without reinstalling) —
run it from anywhere with just `boozer`.

## Layout

```
boozer/
├── app.py              — Textual App: composition + event wiring only
├── boozer.tcss           — all styling (external stylesheet, not embedded in .py)
├── models.py               — Formula: pure data, zero I/O
├── theme.py                  — palette hex constants (used by inline Rich markup)
├── brew/                       — everything that talks to `brew`/`du`/the filesystem
│   ├── cli.py                    — raw subprocess primitives (run, du_kb, format_size)
│   ├── queries.py                  — one function per brew/du command
│   ├── info.py                       — orchestration: builds Formula objects,
│   │                                    including the tap name-collision fix
│   ├── mock.py                         — BREW_TUI_MOCK fake data
│   └── __init__.py                      — public API (5 functions, that's it)
├── examples/                    — "How is this best served?" knowledge base
│   ├── types.py                    — Example(label, command)
│   ├── curated.py                    — hand-picked examples, always available
│   ├── llm.py                          — real LM Studio-backed provider (see below)
│   ├── cache.py                          — disk cache backing CachingProvider
│   ├── provider.py                         — ExampleProvider interface +
│   │                                          TldrProvider design sketch (not implemented)
│   └── __init__.py                          — get_examples(formula), provider chain
└── widgets/                      — Textual widgets, presentation only
    ├── detail_panel.py
    ├── examples_panel.py
    └── weight_panel.py
```

Rule of thumb: nothing outside `boozer/brew/` imports `subprocess`;
nothing outside `boozer/widgets/` and `app.py` imports from `textual`.
`models.py` is the shared vocabulary between the two sides.

## "How is this best served?"

Examples come from a provider chain, tried in order until one answers
(see `boozer/examples/provider.py` for the full design rationale):

1. **CuratedProvider** — a small hand-picked dict, instant, no network.
2. **CachingProvider(LlmProvider())** — disk cache first
   (`~/.cache/boozer/examples/`); on a miss, asks a local
   [LM Studio](https://lmstudio.ai) model for 5-6 example commands and
   writes the result through to the cache.

`TldrProvider` (fetching community [tldr-pages](https://github.com/tldr-pages/tldr)
cheat sheets) is designed in `provider.py` but not implemented.

### Enabling the LLM provider

Off by default. To turn it on:

1. Run [LM Studio](https://lmstudio.ai), load a model, and start its
   local server (Developer tab → Start Server). It exposes an
   OpenAI-compatible API at `http://localhost:1234/v1` by default.
2. Set:
   ```bash
   export BOOZER_ENABLE_LLM_EXAMPLES=1
   python -m boozer
   ```

Optional configuration:

| Variable                     | Default                      | Meaning                                    |
|-------------------------------|-------------------------------|---------------------------------------------|
| `BOOZER_ENABLE_LLM_EXAMPLES`   | unset (off)                    | must be `1`/`true`/`yes` to enable at all    |
| `BOOZER_LM_STUDIO_URL`          | `http://localhost:1234/v1`      | LM Studio's OpenAI-compatible base URL       |
| `BOOZER_LM_STUDIO_MODEL`         | `local-model`                    | model id sent in the request — **required** if your LM Studio serves more than one model (check `curl <url>/v1/models`), since an unmatched id gets silently rejected |
| `BOOZER_LM_STUDIO_MAX_TOKENS`     | `1024`                            | generation budget for the answer itself     |
| `BOOZER_LM_STUDIO_THINKING`        | unset (off)                        | set `1`/`true`/`yes` to let the model reason before answering (see below) |
| `BOOZER_LM_STUDIO_TIMEOUT`          | `90` (seconds)                      | generation timeout — raise for slower/larger models |
| `BOOZER_CACHE_DIR`                  | `~/.cache/boozer/examples`            | where resolved examples are cached on disk   |

### Reasoning ("thinking") models

Some local models (Qwen3.5 and others with a chat template that supports
an `enable_thinking` toggle) reason internally before writing a final
answer — useful for hard problems, actively counterproductive for "give
me 6 JSON objects": the model can burn its whole token budget on
chain-of-thought and never get to writing the answer, leaving `content`
empty (`finish_reason: "length"`).

boozer disables thinking by default, by sending
`chat_template_kwargs: {"enable_thinking": false}` on every request —
not just hoping there's enough budget for the model to reason *and*
answer, but skipping the reasoning phase entirely. This only takes
effect on chat templates that support the variable (Qwen3.5 does;
others may simply ignore it). If you want reasoning anyway, set
`BOOZER_LM_STUDIO_THINKING=1` — note that if the model then exhausts
`BOOZER_LM_STUDIO_MAX_TOKENS` while still reasoning, boozer treats that
as "no examples" rather than guessing from a partial chain-of-thought
(`reasoning_content` is deliberately never used as a source of the
actual answer).

### How it behaves

- **Curated formulae never touch the network.** The LLM provider is
  only reached if nothing curated matches.
- **Fails fast when LM Studio isn't running** — a quick TCP reachability
  check (~1.5s) before attempting generation, rather than waiting out a
  long timeout every time.
- **Never blocks the UI.** Examples are only fetched when you actually
  open the panel (press `a`), and always in a background worker — the
  panel shows "Looking that up…" while a request is in flight, and you
  can keep navigating the list in the meantime.
- **Cached per (formula, version)** — a formula is only ever sent to
  the model once; subsequent lookups (including after a `brew upgrade`,
  since the version is part of the cache key) come straight from disk.
- **Tolerant of messy model output** — local models often wrap JSON in
  ` ```json ` fences or add a stray sentence despite instructions not
  to; the response is parsed by extracting the first `[...]` block
  rather than requiring an exact match. Malformed output degrades to
  "no examples", never a crash.
