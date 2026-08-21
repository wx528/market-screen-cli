"""Configuration loader.

Reads `dashboard.toml` (next to this file) and merges it on top of the
DEFAULTS below. Missing file or missing keys → defaults. Touching the
TOML only takes effect on next launch — that is the expected behaviour.

Run `dashboard.py --init-config` to dump a commented starter file.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path
from typing import Any


# ── defaults (used when TOML is absent or a key is missing) ───────────────────

DEFAULTS: dict[str, Any] = {
    "terminal": {
        "default_width":  140,   # used by --demo / --anim fallbacks
        "default_height": 42,
        "min_width":      100,   # hard floor; below this layout collapses
    },
    "refresh": {
        "fps":             15,    # Live refresh rate, 4–30 reasonable
        "marquee_step":    1,     # chars the BIG marquee advances per tick (slow)
        "ticker_step":     2,     # chars the ticker tape advances per tick (fast)
        "anim_frame_sleep": 0.08, # seconds between frames in --anim mode
    },
    "layout": {
        "header_size":  7,   # logo + clock + BIG marquee (2 rows) + ticker tape
        "kpi_size":     7,
        "mid_size":     12,
        "bottom_size":  11,
        "footer_size":  3,
    },
    # Tickers shown in the TICKER STREAM panel. Each row: [symbol, full_name].
    "tickers": [
        ["AAPL",  "APPLE INC"],
        ["MSFT",  "MICROSOFT"],
        ["NVDA",  "NVIDIA"],
        ["TSLA",  "TESLA"],
        ["AMZN",  "AMAZON"],
        ["GOOGL", "ALPHABET"],
        ["META",  "META PLATFORMS"],
        ["BTC",   "BITCOIN"],
        ["ETH",   "ETHEREUM"],
        ["GOLD",  "GOLD SPOT"],
        ["OIL",   "WTI CRUDE"],
        ["DXY",   "DOLLAR INDEX"],
    ],
    # Marquee news ticker. Each row: [category, message, color].
    # Color: red / yellow / cyan / magenta / green / white / blue.
    "notices": [
        ["BREAKING", "Fed signals rate cut in Q4 — futures rally across the curve", "red"],
        ["ALERT",    "TSLA implied vol spikes to 92 (3-sigma breach on options chain)", "yellow"],
        ["MARKET",   "Brent crude +2.4% on supply concerns; OPEC+ holds output",       "cyan"],
        ["FX",       "USD/JPY breaks 148.32 resistance — yen weakens on yield gap",    "magenta"],
        ["EARNINGS", "NVDA beat consensus EPS by 8% post-market; guide raised",        "cyan"],
        ["NEWS",     "ECB holds rates steady; hawkish tone softened at the margin",     "white"],
        ["ALERT",    "BTC funding rate flips negative — shorts crowded, watch squeeze", "yellow"],
        ["BREAKING", "M&A rumor: AAPL in advanced talks to acquire XYZ for $42B",      "red"],
        ["MARKET",   "10Y Treasury yield retreats to 4.18% after CPI surprise",        "cyan"],
        ["SYSTEM",   "Order routing nominal — venue latency p99 = 12ms",               "green"],
        ["FX",       "EUR/USD coiled at 1.0820 ahead of ECB presser; vol subdued",    "magenta"],
        ["NEWS",     "China PMI prints 50.4 — first expansion in 6 months",            "white"],
        ["MARKET",   "Gold spot tags all-time high $2,478 on safe-haven bid",          "cyan"],
        ["EARNINGS", "MSFT cloud growth +22% YoY, beats top-line by 1.4%",             "cyan"],
    ],
    # Big-marquee headlines (slow, top row). Keep this short — 3–8 items.
    # Each row: [category, message, color].
    "notices_big": [
        ["BREAKING", "Fed signals rate cut in Q4 — futures rally across the curve", "red"],
        ["EARNINGS", "NVDA beat consensus EPS by 8% post-market; guide raised",      "yellow"],
        ["BREAKING", "M&A rumor: AAPL in advanced talks to acquire XYZ for $42B",    "red"],
        ["ALERT",    "TSLA implied vol spikes to 92 (3-sigma breach on options chain)", "yellow"],
        ["EARNINGS", "MSFT cloud growth +22% YoY, beats top-line by 1.4%",            "yellow"],
    ],
    # Rolling event-log messages.
    "seed_log": [
        "order routed: AAPL BUY 100 @ 192.45",
        "ws heartbeat OK (latency 12ms)",
        "feed reconnected: NYSE",
        "alert: TSLA vol > 3-sigma",
        "order routed: NVDA SELL 50 @ 891.20",
        "spread narrowing on BTC",
        "settlement cleared batch #4821",
        "user login: analyst_07 from 10.0.4.18",
        "rate limit refreshed: 240/240",
        "risk check passed: portfolio #7",
        "fx snapshot cached: USD/JPY 148.32",
        "tick batch flushed: 4,182 rows",
    ],
}


# ── merge + load ─────────────────────────────────────────────────────────────

def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursive dict merge; lists/values in `override` replace `base`."""
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _deep_copy(d: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in d.items():
        out[k] = dict(v) if isinstance(v, dict) else (list(v) if isinstance(v, list) else v)
    return out


def load(path: Path | None = None) -> dict[str, Any]:
    """Load config; merge TOML on top of DEFAULTS."""
    base = _deep_copy(DEFAULTS)
    p = path or (Path(__file__).parent / "dashboard.toml")
    if p.exists():
        with open(p, "rb") as f:
            user = tomllib.load(f)
        base = _deep_merge(base, user)
    return base


def dump_starter(path: Path) -> None:
    """Write a fully-commented starter file the user can edit.

    NOTE on TOML ordering: top-level arrays (`tickers`, `notices`, `seed_log`)
    MUST come either before all `[tables]` or after — never interleaved. This
    is a hard TOML spec rule; the parser silently drops the offenders
    otherwise.
    """
    content = '''# dashboard.toml — user-tunable settings.
# Rename or copy to `dashboard.toml` (same folder as dashboard.py) and edit.
# Anything missing here falls back to the in-code defaults; nothing breaks.
#
# ⚠️  Top-level arrays (tickers / notices / seed_log) MUST be at the very top
#     OR the very bottom of this file — never interleaved with [tables]. TOML
#     will silently drop them otherwise.

# ── top-level arrays (kept above all [tables] per TOML spec) ────────────────

# Tickers shown in the TICKER STREAM panel. Each row: [symbol, full_name].
tickers = [
  ["AAPL",  "APPLE INC"],
  ["MSFT",  "MICROSOFT"],
  ["NVDA",  "NVIDIA"],
  ["TSLA",  "TESLA"],
  ["AMZN",  "AMAZON"],
  ["GOOGL", "ALPHABET"],
  ["META",  "META PLATFORMS"],
  ["BTC",   "BITCOIN"],
  ["ETH",   "ETHEREUM"],
  ["GOLD",  "GOLD SPOT"],
  ["OIL",   "WTI CRUDE"],
  ["DXY",   "DOLLAR INDEX"],
]

# Marquee news ticker. Each row: [category, message, color].
# Color: red / yellow / cyan / magenta / green / white / blue.
notices = [
  ["BREAKING", "Fed signals rate cut in Q4 — futures rally across the curve", "red"],
  ["ALERT",    "TSLA implied vol spikes to 92 (3-sigma breach on options chain)", "yellow"],
  ["MARKET",   "Brent crude +2.4% on supply concerns; OPEC+ holds output",       "cyan"],
  # ...add your own...
]

# Big-marquee headlines (slow, top row). Keep this short — 3–8 items.
# Each row: [category, message, color].
notices_big = [
  ["BREAKING", "Fed signals rate cut in Q4 — futures rally across the curve", "red"],
  ["EARNINGS", "NVDA beat consensus EPS by 8% post-market; guide raised",      "yellow"],
  ["BREAKING", "M&A rumor: AAPL in advanced talks to acquire XYZ for $42B",    "red"],
  # ...add your own...
]

# Rolling event-log messages.
seed_log = [
  "order routed: AAPL BUY 100 @ 192.45",
  "ws heartbeat OK (latency 12ms)",
  "feed reconnected: NYSE",
  # ...
]

# ── tunables (all optional, fall back to in-code defaults) ──────────────────

[terminal]
default_width  = 140   # width used by --demo / --anim when the console can't be probed
default_height = 42    # ditto for height
min_width      = 100   # hard floor: below this the layout starts to look squashed

[refresh]
fps              = 15  # Live refresh rate, 4–30 reasonable. CLI override: --fps N
marquee_step     = 1   # chars the BIG marquee advances per tick (slow)
ticker_step      = 2   # chars the ticker tape advances per tick; bump 3-4 for faster
anim_frame_sleep = 0.08  # seconds between frames in --anim mode

[layout]
header_size  = 8   # height of the header row (logo + clock + big marquee 2-row + ticker tape)
kpi_size     = 7   # height of the 4 KPI cards row
mid_size     = 12  # height of the chart + system/log row
bottom_size  = 11  # height of the ticker + heatmap row
footer_size  = 3   # height of the status footer
'''
    path.write_text(content, encoding="utf-8")


# ── module-level singleton ───────────────────────────────────────────────────

CONFIG: dict[str, Any] = load()


if __name__ == "__main__":
    if "--init-config" in sys.argv:
        target = Path(__file__).parent / "dashboard.toml"
        dump_starter(target)
        print(f"wrote {target}")
    else:
        import json
        print(json.dumps(CONFIG, indent=2, ensure_ascii=False))