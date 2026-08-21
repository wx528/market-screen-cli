# Market Screen // CLI Dashboard

A live, multi-region command-line dashboard built on
[Rich](https://github.com/Textualize/rich). Pure cosmetic demo — all
data is faked.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ▰▰▰ MARKET SCREEN // COMMAND-LINE DASHBOARD            2026-08-21  ● LIVE │
│ index 9,847 ▲ +1.23            session: morning · feed: nyse+arca+crypto   │
│ ◤ ▰▰  BREAKING   ▸▸ Fed signals rate cut in Q4 ━━━◆ EARNINGS ▸▸ NVDA beat…│
│   ▰▰  BREAKING   ▸▸ Fed signals rate cut in Q4 ━━━◆ EARNINGS ▸▸ NVDA beat…│
│ ▸ ◆AAPL $192.45 ▲0.87% ··· ◆TSLA $248.10 ▼1.24% ··· ◆NVDA $891.20 ▲0.42% ◂│
├─────────────────────────────────────────────────────────────────────────────┤
│ MARKETS        │ VOLATILITY      │ VOLUME          │ SENTIMENT               │
│ 9,847 ▲ +1.23  │ 18.4% ▁▂▅▇█▇▅▂  │ $2.31B ▆▅▆█▇▆   │ 72.4  ▃▅▇█▆▅▃▄         │
├─────────────────────────────────────────────────────────────────────────────┤
│           INTRADAY (sparkline)        │ SYSTEM  CPU/MEM/DISK/NET gauges    │
│                                      ├────────────────────────────────────┤
│                                      │ EVENT LOG (rolling)                │
├─────────────────────────────────────────────────────────────────────────────┤
│ TICKER STREAM (real-time quotes)     │ SECTOR HEATMAP                     │
├─────────────────────────────────────────────────────────────────────────────┤
│ STATUS ● NOMINAL         UPTIME 14d    LATENCY 12ms · v1.0.0 · q to quit  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Features

* **NYSE-style dual ticker** — slow scrolling headline marquee (double-
  height, ~2× visual size) + fast live ticker tape underneath. Top news
  reads at a glance, bottom prices flash by.
* **KPI strip** with sparklines (Markets / Volatility / Volume / Sentiment).
* **Intraday sparkline** with x-axis ticks and summary line.
* **System gauges** (CPU / Memory / Disk I/O / Network) as block-glyph
  progress bars — survives nested `Layout` where `ProgressBar` collapses.
* **Rolling event log** with timestamps.
* **Ticker stream** (price / change / vol / mini-bar).
* **Sector heatmap** (6 sectors × 6 cells).
* **Live clock**, uptime, status footer.
* **TOML-driven** — every tunable lives in `dashboard.toml`, no code edits.

## Run

```bash
uv run dashboard.py             # full-screen, real-time (Ctrl-C to exit)
uv run dashboard.py --demo      # one-shot render to stdout, then exit
uv run dashboard.py --anim 8    # animate 8 frames in-place
uv run dashboard.py --fps 20    # override refresh rate for this launch
uv run dashboard.py --init-config   # write a starter dashboard.toml
```

Requires Python ≥ 3.11 (uses stdlib `tomllib`). Rich is the only runtime
dep (pulled in via `uv`).

## Configuration

All tunables live in **`dashboard.toml`** (next to `dashboard.py`). Anything
missing falls back to the in-code defaults in `config.py` — nothing breaks.

```bash
uv run dashboard.py --init-config   # write a starter file with comments
```

### Keys

```toml
[terminal]
default_width  = 140
default_height = 42
min_width      = 100

[refresh]
fps              = 15   # CLI override: --fps N
marquee_step     = 1    # chars the BIG marquee advances per tick (slow)
ticker_step      = 2    # chars the ticker tape advances per tick (fast)
anim_frame_sleep = 0.08 # seconds between frames in --anim

[layout]
header_size = 7   # logo + clock + BIG marquee (2 rows) + ticker tape
kpi_size    = 7
mid_size    = 12
bottom_size = 11
footer_size = 3

tickers     = [["AAPL","APPLE INC"], ...]      # TICKER STREAM rows + tape prices
notices     = [["BREAKING","...","red"], ...]  # marquee items
notices_big = [["BREAKING","...","red"], ...]  # top BIG marquee (slow)
seed_log    = ["order routed: ...", ...]       # EVENT LOG rotation
```

> ⚠️ Top-level arrays (`tickers` / `notices` / `seed_log` / `notices_big`)
> **must** sit above **or** below all `[tables]` — never interleaved.
> TOML silently drops them otherwise. The starter file already places them
> at the top.

## Layout notes

* `Layout` is the spine; each region renders a `Panel` rebuilt every tick.
* **Double-height big marquee** — `marquee_big()` returns a
  `Group(line1, line2)`. Line 1 is bold-coloured; line 2 is the same
  chars at `dim` style, giving a "raised" feel that reads ~2× as tall.
  Note: terminals can't change font size per cell, so this is the
  closest approximation — characters physically occupy two rows.
* **Ticker tape** rebuilds its `(char, style)` buffer each tick because
  prices change (`tape_stream` is a random-walk of every symbol).
* Both marquees slice a window from a flat `(char, style)` buffer
  cached at module init (`_MARQUEE_CHARS`, `_MARQUEE_BIG_CHARS`);
  wrap-around is `% n`.
* Sparklines are 8-level Unicode block glyphs (`▁▂▃▄▅▆▇█`); Rich 15
  removed `rich.sparkline`, so a tiny inline renderer is used.
* Gauges use block-glyph bars (`█`/`░`) — survives in nested `Layout`s
  where `ProgressBar` collapses.
* Ticker / log / series are `deque(maxlen=…)` mutated each tick for O(1)
  rolling behaviour.

## Performance

Benchmarked on a 140×42 terminal at 15 fps, full dashboard:

* `render()` cost: **~4 ms / frame** → ~250 fps headroom
* CPU usage: **~1 %** at 15 fps
* ANSI output: ~200 KB/s
* Higher fps (`--fps 30`) is wasted; the human eye resolves marquee
  motion around 24 fps. Keep the default unless you're chasing
  non-existent smoothness.

## Files

| File | Purpose |
|---|---|
| `dashboard.py`  | Main app (~580 lines, single file). |
| `config.py`     | In-code defaults + TOML loader. |
| `dashboard.toml`| Optional user overrides. |
| `pyproject.toml` / `uv.lock` | Managed by `uv`. |
| `CHANGELOG.md`  | Release notes. |

## Tweaks

* Edit `MarketState.tick()` to plug a real feed (HTTP / WebSocket).
* Add / remove `notices` / `tickers` / `seed_log` in `dashboard.toml`.
* `--fps N` overrides the TOML fps for a single launch.
* `--ticker-step N` could be added in the same pattern if you want
  per-launch override for the tape speed too.

## License

MIT.