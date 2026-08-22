# Changelog

All notable changes to this project will be documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.0.2] — 2026-08-22

### Added
- **Interactive detail overlay** — keyboard-driven drill-down.
  - `1` / `2` / `3` / `4` — expand KPI 1..4 detail (full-screen
    sparkline + last value / change)
  - `t` — expand ticker tape detail (full-width live prices)
  - `h` — keyboard shortcuts overlay
  - `ESC` — back to dashboard
  - `q` / Ctrl-C — quit
  - `--demo-detail=kpi1|kpi2|kpi3|kpi4|ticker|help` for screenshotting
- Footer now shows the hotkey hint row (`keys 1-4 kpi  t ticker  h
  help  esc back  q quit`).
- Cross-platform non-blocking keyboard polling (`msvcrt` on Windows,
  `termios + select` on POSIX). Special-key handling for arrows /
  ESC.

## [0.0.1] — 2026-08-21

Initial release.

### Added
- Live multi-region terminal dashboard built on Rich.
- NYSE-style **dual marquee header**:
  - Top **double-height big marquee** (slow, bold-coloured) for
    `BREAKING / EARNINGS / ALERT` headlines — characters physically
    occupy two rows to simulate a larger font (terminals cannot change
    font size per cell).
  - Bottom **ticker tape** (fast, dim) for live prices of every
    configured symbol, with green/red `▲/▼` change indicators.
- KPI strip: MARKETS / VOLATILITY / VOLUME / SENTIMENT, each with a
  self-rolled 8-level block-glyph sparkline (`▁▂▃▄▅▆▇█`).
- INTRADAY sparkline panel with faux x-axis ticks and summary line.
- SYSTEM gauges: CPU / MEMORY / DISK I/O / NETWORK as block-glyph
  progress bars (`█/░`) — survives nested `Layout` where
  `ProgressBar` collapses.
- EVENT LOG rolling deque.
- TICKER STREAM table (price / change % / vol / mini-bar).
- SECTOR HEATMAP (6 sectors × 6 cells).
- Live header with clock + `● LIVE` indicator.
- Status footer with uptime + nominal status + latency.

### Configuration
- All tunables in `dashboard.toml` (TOML, stdlib `tomllib`).
- `--init-config` writes a fully-commented starter file.
- CLI flags: `--demo`, `--anim N`, `--fps N`.
- Missing keys fall back to in-code defaults — nothing breaks.

### Performance
- `render()` cost: ~4 ms / frame (headroom ~250 fps at 140×42).
- ~1 % CPU at 15 fps, ~200 KB/s ANSI output.
- Marquee char buffers cached at module init (`_MARQUEE_CHARS`,
  `_MARQUEE_BIG_CHARS`); ticker tape rebuilds per tick since prices
  change.

### Known limitations
- Terminals cannot change font size per cell — "larger" text is
  approximated via double-row rendering.
- Top-level arrays in `dashboard.toml` must sit above **or** below
  all `[tables]` per TOML spec; interleaved arrays are silently
  dropped.
- All data is faked; no real feeds. Plug your source into
  `MarketState.tick()` to wire real data.