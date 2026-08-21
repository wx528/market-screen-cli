"""Market Screen // Command-Line Dashboard.

A live, multi-region terminal dashboard built with Rich.
Pure cosmetic / demo data — no real feeds.

Run:
    uv run dashboard.py
"""

from __future__ import annotations

import math
import random
import time
from collections import deque
from datetime import datetime
from pathlib import Path

from rich.align import Align
from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.padding import Padding
from rich.panel import Panel
from rich.progress_bar import ProgressBar
from rich.style import Style
from rich.table import Table
from rich.text import Text
from rich.box import ROUNDED
from rich.rule import Rule

from config import CONFIG as CFG

# ── self-rolled sparkline (rich.sparkline was removed in 15.x)
SPARK_BLOCKS = "▁▂▃▄▅▆▇█"


def sparkline(data, width: int = 24, style: str = "bold cyan") -> Text:
    if not data:
        t = Text(" " * width, style=style)
        t.no_wrap = True
        return t
    series = list(data)[-width:]
    if len(series) < width:
        series = ([series[0]] * (width - len(series))) + series
    lo, hi = min(series), max(series)
    rng = max(hi - lo, 1e-9)
    out = Text(style=style)
    for v in series:
        idx = int((v - lo) / rng * (len(SPARK_BLOCKS) - 1))
        out.append(SPARK_BLOCKS[idx])
    out.no_wrap = True
    return out

# ─────────────────────────────────────────────────────────────────────────────
#  fake data generators
# ─────────────────────────────────────────────────────────────────────────────

# Tickers shown in the TICKER STREAM panel. Editable via dashboard.toml.
TICKERS: list[tuple[str, str]] = [tuple(row) for row in CFG["tickers"]]

# System gauges (technical, unlikely to change).
LEVELS = [
    ("CPU",      "system.cpu",      0, 100, "%"),
    ("MEMORY",   "system.memory",   0, 100, "%"),
    ("DISK I/O", "system.disk",     0, 100, "%"),
    ("NETWORK",  "system.network",  0, 100, "%"),
]

# Marquee notifications: (category, message, color). Editable via dashboard.toml.
NOTICES: list[tuple[str, str, str]] = [tuple(row) for row in CFG["notices"]]

# Big-marquee headlines (top row, slow). Editable via dashboard.toml.
NOTICES_BIG: list[tuple[str, str, str]] = [tuple(row) for row in CFG["notices_big"]]

# Rolling event-log messages. Editable via dashboard.toml.
SEED_LOG: list[str] = list(CFG["seed_log"])

# Tunables (also editable via dashboard.toml; CLI flags override per-launch).
FPS              = CFG["refresh"]["fps"]
MARQUEE_STEP     = CFG["refresh"]["marquee_step"]
TICKER_STEP      = CFG["refresh"]["ticker_step"]
ANIM_FRAME_SLEEP = CFG["refresh"]["anim_frame_sleep"]
TERM_DEFAULT_W   = CFG["terminal"]["default_width"]
TERM_DEFAULT_H   = CFG["terminal"]["default_height"]
TERM_MIN_W       = CFG["terminal"]["min_width"]

LAYOUT_SIZES = CFG["layout"]


class MarketState:
    """Holds all mutable state. Single source of truth for the dashboard."""

    def __init__(self) -> None:
        self.start = time.time()
        # KPI numbers
        self.index = 9847.32
        self.index_prev = self.index
        self.volatility = 18.4
        self.volume_b = 2.31
        self.sentiment = 0.72  # 0..1
        # intraday price series (last 60 ticks)
        self.series: deque[float] = deque(
            [100 + 10 * math.sin(i / 6) + random.gauss(0, 1.5) for i in range(60)],
            maxlen=60,
        )
        # gauge levels
        self.levels: dict[str, float] = {
            name: random.uniform(20, 80) for name, *_ in LEVELS
        }
        # rolling log
        self.log: deque[tuple[str, str]] = deque(maxlen=8)
        for line in SEED_LOG:
            self.log.append(self._stamp(line))
        # ticker tape (last 14 rows)
        self.tape: deque[tuple[str, str, float, float, float]] = deque(maxlen=14)
        for sym, name in TICKERS[:8]:
            px = random.uniform(50, 900)
            chg = random.uniform(-2.5, 2.5)
            vol = random.uniform(1, 25)
            self.tape.append((sym, name, px, chg, vol))
        # full tape_stream — every ticker with live price, used for the ticker tape
        # bottom marquee. Format per entry: (sym, name, price, pct_change).
        self.tape_stream: list[tuple[str, str, float, float]] = [
            (sym, name, random.uniform(20, 1000), random.uniform(-3.0, 3.0))
            for sym, name in TICKERS
        ]
        # marquee offsets — big (top, slow) + ticker tape (bottom, fast)
        self.marquee_offset = 0
        self.tape_offset = 0
        self.tick_n = 0

    @staticmethod
    def _stamp(msg: str) -> tuple[str, str]:
        return (datetime.now().strftime("%H:%M:%S"), msg)

    def tick(self) -> None:
        # index random walk
        delta = random.gauss(0, 4.2)
        self.index_prev = self.index
        self.index += delta
        # volatility oscillates
        self.volatility = max(5.0, min(45.0,
            self.volatility + random.gauss(0, 0.4)))
        # volume drifts
        self.volume_b = max(0.4, self.volume_b + random.gauss(0, 0.05))
        # sentiment drifts slowly toward 0.5
        self.sentiment = max(0.05, min(0.95,
            self.sentiment + random.gauss(0, 0.02)))
        # intraday series
        last = self.series[-1] if self.series else 100.0
        nxt = last + random.gauss(0, 1.6) + 0.15 * math.sin(len(self.series) / 4)
        self.series.append(nxt)
        # gauges
        for name in list(self.levels):
            v = self.levels[name] + random.gauss(0, 3.5)
            self.levels[name] = max(0, min(100, v))
        # rolling log — add roughly every other tick to stay readable
        self.tick_n += 1
        if self.tick_n % 2 == 0 and random.random() < 0.6:
            msg = random.choice(SEED_LOG)
            self.log.append(self._stamp(msg))
        # ticker tape — every 3 ticks so the tape doesn't churn
        if self.tick_n % 3 == 0 and random.random() < 0.85:
            sym, name = random.choice(TICKERS)
            px = random.uniform(50, 950)
            chg = random.uniform(-3.5, 3.5)
            vol = random.uniform(0.5, 30)
            self.tape.append((sym, name, px, chg, vol))
        # ticker tape_stream — nudge every entry's price so the bottom marquee
        # shows live-ish movement, not a static list
        new_stream = []
        for sym, name, px, chg in self.tape_stream:
            px = max(0.5, px * (1 + random.gauss(0, 0.0008)))
            chg = max(-9.99, min(9.99, chg + random.gauss(0, 0.04)))
            new_stream.append((sym, name, px, chg))
        self.tape_stream = new_stream
        # marquee — chars per tick driven by config; silky scroll at higher fps
        self.marquee_offset += MARQUEE_STEP
        # ticker tape — fast scroll
        self.tape_offset += TICKER_STEP

    @property
    def uptime(self) -> str:
        s = int(time.time() - self.start)
        d, s = divmod(s, 86400)
        h, s = divmod(s, 3600)
        m, _ = divmod(s, 60)
        return f"{d}d {h:02d}h {m:02d}m"


# ─────────────────────────────────────────────────────────────────────────────
#  panel builders
# ─────────────────────────────────────────────────────────────────────────────

CONSOLE = Console()

CYAN = "cyan"
MAGENTA = "magenta"
GREEN = "green"
RED = "red"
YELLOW = "yellow"
DIM = "grey50"
ACCENT = "bright_cyan"


def _kpi_card(title: str, big: str, sub: str, color: str,
              spark_data: list[float], card_width: int = 30) -> Panel:
    spark_w = max(8, min(28, card_width - 16))
    spark = (sparkline(spark_data, width=spark_w, style=f"bold {color}")
             if spark_data else Text(" " * spark_w))
    grid = Table.grid(expand=True)
    grid.add_column(justify="left", ratio=1)
    grid.add_column(justify="right")
    grid.add_row(
        Text(big, style=f"bold {color}", no_wrap=True),
        Align.right(spark),
    )
    sub_text = Text(sub, style=DIM, overflow="ellipsis", no_wrap=True)
    grid.add_row(sub_text, Text(" "))
    body = Group(
        Text(title.upper(), style=f"bold {ACCENT}"),
        Padding(grid, (1, 0)),
    )
    return Panel(body, border_style=color, box=ROUNDED, padding=(0, 1))


# pre-computed at module load: flat list of (char, style) for all NOTICES
_MARQUEE_CHARS: list[tuple[str, str]] = []


def _build_marquee_chars() -> list[tuple[str, str]]:
    chars: list[tuple[str, str]] = []
    for cat, msg, color in NOTICES:
        prefix = f"● {cat}  "
        for ch in prefix:
            chars.append((ch, f"bold {color}"))
        for ch in msg:
            chars.append((ch, "white"))
        for _ in range(6):
            chars.append((" ", "grey30"))
        for _ in range(4):
            chars.append(("·", f"bold {color}"))
        for _ in range(6):
            chars.append((" ", "grey30"))
    return chars


_MARQUEE_CHARS = _build_marquee_chars()
_MARQUEE_N = len(_MARQUEE_CHARS)


# ── big marquee (top, slow) — uses NOTICES_BIG with bolder visual weight ─────

def _build_marquee_big_chars() -> list[tuple[str, str]]:
    """Build flat (char, style) buffer for the big marquee.

    Visual weight ↑↑: each glyph in the prefix/divider is doubled (rendered
    as two adjacent chars) so the line reads ~2× as tall and bold in the
    terminal, even though it still occupies a single row in the layout.
    Message text is rendered bold-yellow on a coloured block background.
    """
    chars: list[tuple[str, str]] = []
    for cat, msg, color in NOTICES_BIG:
        # ◆◆ ◆ CAT  ▸▸▸▸  — doubled diamond, doubled arrow, padded
        prefix = f" {cat}  "
        # leading doubled diamond in category colour
        for ch in "▰▰":
            chars.append((ch, f"bold {color}"))
        chars.append((" ", "grey30"))
        # category label — doubled space-padded so it reads as a block
        for ch in prefix:
            chars.append((ch, f"bold {color}"))
        # doubled arrow divider
        for ch in " ▸▸":
            chars.append((ch, f"bold {color}"))
        chars.append((" ", "grey30"))
        # message — bold yellow (bright, legible, "heavy" feel)
        for ch in msg:
            chars.append((ch, "bold yellow"))
        # long blank gap
        for _ in range(6):
            chars.append((" ", "grey30"))
        # thick doubled divider in category colour
        for ch in "▰▰▰▰▰▰▰▰":
            chars.append((ch, f"bold {color}"))
        for _ in range(6):
            chars.append((" ", "grey30"))
    return chars


_MARQUEE_BIG_CHARS = _build_marquee_big_chars()
_MARQUEE_BIG_N = len(_MARQUEE_BIG_CHARS)


def marquee_big(width: int, offset: int):
    """Double-height news ticker — each char rendered on two rows so the line
    reads ~2× as tall as a normal marquee. Returns a ``Group`` of two Texts;
    the layout region must be tall enough to host both rows.
    """
    if width <= 4 or _MARQUEE_BIG_N == 0:
        return Group(Text(""), Text(""))
    body_w = width - 4
    line1 = Text(no_wrap=True)
    line2 = Text(no_wrap=True)
    line1.append("◤ ", style="bold white")
    line2.append("  ", style="bold white")
    for i in range(body_w):
        ch, st = _MARQUEE_BIG_CHARS[(offset + i) % _MARQUEE_BIG_N]
        # row 1: full color
        line1.append(ch, style=st)
        # row 2: same char, dim shadow to give a "raised" feel
        line2.append(ch, style=st.replace("bold ", "dim ") if "dim " not in st else st)
    line1.append(" ◥", style="bold white")
    line2.append("  ", style="bold white")
    return Group(line1, line2)


# ── ticker tape (bottom of header, fast) — live prices from tape_stream ──────

def ticker_tape(width: int, offset: int, tape: list[tuple[str, str, float, float]]) -> Text:
    """Fast scrolling price tape, NYSE bottom-of-screen style.

    Each ticker is rendered as `SYM $XXX.XX ▲X.XX%`. Whole tape is re-laid
    flat into (char, style) tuples; the function then slices a window.
    """
    if width <= 4 or not tape:
        return Text("")
    chars: list[tuple[str, str]] = []
    for sym, _name, px, chg in tape:
        arrow = "▲" if chg >= 0 else "▼"
        color = "green" if chg >= 0 else "red"
        # " ◆SYM $1,234.56 ▲0.87%  "
        block = f" ◆{sym:<5} ${px:>8,.2f} {arrow}{abs(chg):.2f}% "
        for ch in f"◆{sym}":
            chars.append((ch, "bold white"))
        chars.append((" ", "grey30"))
        for ch in f"${px:,.2f}":
            chars.append((ch, "white"))
        chars.append((" ", "grey30"))
        for ch in f"{arrow}{abs(chg):.2f}%":
            chars.append((ch, f"bold {color}"))
        chars.append((" ", "grey30"))
        # gap
        for _ in range(3):
            chars.append(("·", "grey30"))
    n = len(chars)
    body_w = width - 4
    out = Text(no_wrap=True)
    out.append("▸ ", style="dim white")
    for i in range(body_w):
        ch, st = chars[(offset + i) % n]
        out.append(ch, style=st)
    out.append(" ◂", style="dim white")
    return out


def marquee(width: int, offset: int) -> Text:
    """Horizontal-scrolling news ticker with per-category colour."""
    if width <= 4 or _MARQUEE_N == 0:
        return Text("")
    body_w = width - 4  # reserve 2 chars on each side for ◀ ▶
    out = Text(no_wrap=True)
    out.append("◀ ", style="bold white")
    for i in range(body_w):
        ch, st = _MARQUEE_CHARS[(offset + i) % _MARQUEE_N]
        out.append(ch, style=st)
    out.append(" ▶", style="bold white")
    return out


def header(state: MarketState, width: int = 140) -> Panel:
    bar = Table.grid(expand=True, padding=(0, 1))
    bar.add_column(justify="left", ratio=1)
    bar.add_column(justify="right")
    delta = state.index - state.index_prev
    arrow = "▲" if delta >= 0 else "▼"
    color = GREEN if delta >= 0 else RED
    left = Text()
    left.append("▰▰▰ ", style=f"bold {MAGENTA}")
    left.append("MARKET SCREEN ", style=f"bold white")
    left.append("// ", style=DIM)
    left.append("COMMAND-LINE DASHBOARD", style=ACCENT)
    right = Text()
    right.append(datetime.now().strftime("%Y-%m-%d  %H:%M:%S"), style="white")
    right.append("   ")
    right.append("● LIVE", style=f"bold {GREEN}")
    bar.add_row(left, right)
    bar.add_row(
        Text(f"index {state.index:,.2f}  {arrow} {delta:+.2f}", style=f"bold {color}"),
        Text("session: morning  ·  feed: nyse+arca+crypto", style=DIM),
    )
    # double marquee — big bold headline (slow) + fast ticker tape (live prices)
    inner_w = max(40, width - 6)
    bar.add_row(marquee_big(inner_w, state.marquee_offset))
    bar.add_row(ticker_tape(inner_w, state.tape_offset, state.tape_stream))
    return Panel(bar, style="on grey11", box=ROUNDED, padding=(0, 1))


def kpi_row(state: MarketState, width: int = 140) -> Layout:
    row = Layout()
    card_w = max(18, width // 4 - 2)
    spark_data = list(state.series)[-24:]
    row.split_row(
        _kpi_card(
            "MARKETS",
            f"{state.index:,.2f}",
            f"{'▲' if state.index >= state.index_prev else '▼'} "
            f"{(state.index - state.index_prev):+.2f}  pts",
            GREEN if state.index >= state.index_prev else RED,
            spark_data,
            card_width=card_w,
        ),
        _kpi_card(
            "VOLATILITY",
            f"{state.volatility:5.2f}%",
            "vix-equiv · 1m rolling",
            YELLOW,
            [state.volatility + random.gauss(0, 0.3) for _ in range(20)],
            card_width=card_w,
        ),
        _kpi_card(
            "VOLUME",
            f"${state.volume_b:.2f}B",
            "notional · 1m",
            CYAN,
            [state.volume_b * (0.8 + 0.4 * random.random()) for _ in range(20)],
            card_width=card_w,
        ),
        _kpi_card(
            "SENTIMENT",
            f"{state.sentiment*100:4.1f}",
            "bullish · v3",
            MAGENTA,
            [state.sentiment + random.gauss(0, 0.05) for _ in range(20)],
            card_width=card_w,
        ),
    )
    return row


def intraday_chart(state: MarketState, width: int = 100) -> Panel:
    data = list(state.series)
    sl = sparkline(data, width=max(40, width - 6), style="bold cyan")
    grid = Table.grid(expand=True)
    grid.add_column(justify="center")
    grid.add_row(Align.center(sl, vertical="middle"))
    # x-axis labels
    grid.add_row(
        Text("09:30        11:00        12:30        14:00        15:30   "
             "16:00",
             style=DIM, justify="center"),
    )
    grid.add_row(Rule(style=DIM))
    # mini summary line
    last = data[-1]
    first = data[0]
    chg = (last - first) / first * 100
    color = GREEN if chg >= 0 else RED
    arrow = "▲" if chg >= 0 else "▼"
    summary = Text()
    summary.append("INTRADAY  ", style=f"bold {ACCENT}")
    summary.append("SPX-equiv · 1m bars  ", style=DIM)
    summary.append(f"last {last:,.2f}  ", style="white")
    summary.append(f"{arrow} {chg:+.2f}%", style=f"bold {color}")
    grid.add_row(summary)
    return Panel(
        Align.center(grid, vertical="middle"),
        title="[bold cyan]INTRADAY",
        border_style="cyan",
        padding=(0, 1),
    )


def gauge_row(name: str, val: float, unit: str, width: int = 20) -> Text:
    """A single-line gauge: 'NAME  79.0%  ████████░░░░░░'"""
    color = (GREEN if val < 60 else YELLOW if val < 85 else RED)
    filled = int(val / 100 * width)
    bar = Text()
    bar.append("█" * filled, style=f"bold {color}")
    bar.append("░" * (width - filled), style="grey30")
    name_t = Text(f"{name:<10}", style="bold white")
    val_t = Text(f"{val:5.1f}{unit}", style=f"bold {color}")
    line = Text()
    line.append(name_t)
    line.append(val_t)
    line.append("  ")
    line.append(bar)
    line.no_wrap = True
    return line


def gauges_panel(state: MarketState, width: int = 30) -> Panel:
    bar_w = max(8, width - 16)
    rows = [gauge_row(n, state.levels[n], "%", width=bar_w)
            for n, *_ in LEVELS]
    body = Group(*rows)
    return Panel(body, title="[bold yellow]SYSTEM", border_style="yellow",
                 padding=(0, 1))


def ticker_panel(state: MarketState) -> Panel:
    grid = Table(expand=True, header_style="bold cyan", show_lines=False,
                 pad_edge=False, padding=(0, 1))
    grid.add_column("TIME", style=DIM, width=8, no_wrap=True)
    grid.add_column("SYM", style="bold white", width=6)
    grid.add_column("NAME", style=DIM, ratio=1)
    grid.add_column("LAST", justify="right", width=10)
    grid.add_column("CHG%", justify="right", width=8)
    grid.add_column("VOL", justify="right", width=10)
    grid.add_column("BAR", width=12)
    now = datetime.now()
    rows = list(state.tape)[-9:]
    for sym, name, px, chg, vol in rows:
        color = GREEN if chg >= 0 else RED
        arrow = "▲" if chg >= 0 else "▼"
        bar_len = int(min(abs(chg), 3.0) / 3.0 * 10)
        bar_chars = "█" * bar_len
        bar = Text(bar_chars, style=color)
        ts = now.strftime("%H:%M:%S")
        grid.add_row(
            ts,
            sym,
            name,
            f"{px:,.2f}",
            Text(f"{arrow} {chg:+.2f}%", style=f"bold {color}"),
            f"{vol:5.1f}M",
            bar,
        )
    return Panel(grid, title="[bold magenta]TICKER STREAM", border_style="magenta", padding=(0, 1))


def log_panel(state: MarketState) -> Panel:
    grid = Table.grid(expand=True, padding=(0, 0))
    for ts, msg in list(state.log)[-7:]:
        line = Text()
        line.append(ts + "  ", style=DIM)
        line.append("› ", style="cyan")
        line.append(msg, style="white")
        grid.add_row(line)
    return Panel(grid, title="[bold green]EVENT LOG", border_style="green", padding=(0, 1))


def footer(state: MarketState) -> Panel:
    bar = Table.grid(expand=True)
    bar.add_column(justify="left", ratio=1)
    bar.add_column(justify="center")
    bar.add_column(justify="right")
    bar.add_row(
        Text("STATUS ", style="bold green") + Text("● NOMINAL", style="green"),
        Text(f"UPTIME {state.uptime}", style="white"),
        Text("LATENCY 12ms · v1.0.0 · q to quit",
             style=DIM),
    )
    return Panel(bar, style="on grey11", box=ROUNDED, padding=(0, 1))


# ─────────────────────────────────────────────────────────────────────────────
#  layout
# ─────────────────────────────────────────────────────────────────────────────

def make_layout() -> Layout:
    layout = Layout(name="root")
    L = LAYOUT_SIZES
    layout.split_column(
        Layout(name="header",  size=L["header_size"]),
        Layout(name="kpi",     size=L["kpi_size"]),
        Layout(name="mid",     size=L["mid_size"]),
        Layout(name="bottom",  size=L["bottom_size"]),
        Layout(name="footer",  size=L["footer_size"]),
    )
    # total height check (warn if taller than typical 42-row console)
    total = sum(int(v) if isinstance(v, (int, float)) else 0
                for v in L.values())
    if total > 42 and not getattr(make_layout, "_warned", False):
        make_layout._warned = True
        import sys
        print(
            f"[layout] total height {total} > 42 — consider trimming "
            f"header/kpi/mid in dashboard.toml",
            file=sys.stderr,
        )
    layout["mid"].split_row(
        Layout(name="chart", ratio=3),
        Layout(name="right", ratio=2),
    )
    layout["right"].split_column(
        Layout(name="gauges", ratio=1),
        Layout(name="log", ratio=1),
    )
    layout["bottom"].split_row(
        Layout(name="ticker", ratio=3),
        Layout(name="side", ratio=1),
    )
    layout["side"].split_column(
        Layout(name="heatmap", ratio=1),
    )
    return layout


def heatmap_panel(state: MarketState) -> Panel:
    sectors = ["TECH", "FIN", "ENGY", "HLTH", "CNSMR", "INDU"]
    grid = Table.grid(expand=True, padding=(0, 0))
    grid.add_column(justify="left", ratio=1)
    grid.add_row(Text("SECTOR HEATMAP", style=f"bold {ACCENT}"))
    for sec in sectors:
        row = Table.grid(expand=True)
        row.add_column(width=6)            # sector name column
        for _ in range(6):
            row.add_column(width=7, justify="right")
        cells = [Text(sec, style=f"bold {ACCENT}")]
        for _ in range(6):
            v = random.uniform(-3, 3)
            color = GREEN if v >= 0 else RED
            cells.append(Text(f"{v:+4.2f}", style=f"bold {color}"))
        row.add_row(*cells)
        grid.add_row(row)
    return Panel(grid, title="[bold red]HEATMAP", border_style="red", padding=(0, 1))


# ─────────────────────────────────────────────────────────────────────────────
#  render
# ─────────────────────────────────────────────────────────────────────────────

def render(state: MarketState, width: int) -> Layout:
    layout = make_layout()
    layout["header"].update(header(state, width=width))
    layout["kpi"].update(kpi_row(state, width=width))
    layout["mid"]["chart"].update(intraday_chart(state, width=int(width * 0.62)))
    layout["mid"]["right"]["gauges"].update(gauges_panel(state, width=int(width * 0.38)))
    layout["mid"]["right"]["log"].update(log_panel(state))
    layout["bottom"]["ticker"].update(ticker_panel(state))
    layout["bottom"]["side"]["heatmap"].update(heatmap_panel(state))
    layout["footer"].update(footer(state))
    return layout


def main() -> None:
    import os
    import sys
    # best-effort UTF-8 stdio for unicode box-drawing on legacy Windows consoles
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

    # --init-config: write a starter dashboard.toml (overwrites if exists)
    if "--init-config" in sys.argv:
        from config import dump_starter
        target = Path(__file__).parent / "dashboard.toml"
        dump_starter(target)
        print(f"wrote {target}")
        return

    # mode flags
    demo = "--demo" in sys.argv
    anim = "--anim" in sys.argv
    frames = 8
    if anim:
        try:
            i = sys.argv.index("--anim")
            frames = int(sys.argv[i + 1])
        except Exception:
            frames = 8

    if not (demo or anim):
        os.system("cls" if os.name == "nt" else "clear")

    state = MarketState()
    for _ in range(20):
        state.tick()

    try:
        term_w = CONSOLE.size.width or TERM_DEFAULT_W
    except Exception:
        term_w = TERM_DEFAULT_W
    term_w = max(TERM_MIN_W, term_w)
    try:
        term_h = CONSOLE.size.height or TERM_DEFAULT_H
    except Exception:
        term_h = TERM_DEFAULT_H

    if demo:
        Console(force_terminal=True, width=term_w, height=term_h).print(
            render(state, term_w))
        return

    if anim:
        out = Console(force_terminal=True, width=term_w, height=term_h)
        for f in range(frames):
            state.tick()
            if f:
                os.system("cls" if os.name == "nt" else "clear")
            out.print(render(state, term_w))
            time.sleep(ANIM_FRAME_SLEEP)
        return

    # interactive fullscreen mode
    console = Console(force_terminal=True)
    term_w = max(TERM_MIN_W, console.size.width or term_w)

    # --fps N overrides the TOML fps for a single launch
    fps = FPS
    if "--fps" in sys.argv:
        try:
            i = sys.argv.index("--fps")
            fps = max(1, min(60, int(sys.argv[i + 1])))
        except Exception:
            pass
    sleep_s = 1.0 / fps

    with Live(render(state, term_w), console=console, screen=True,
              refresh_per_second=fps, transient=False) as live:
        try:
            while True:
                state.tick()
                term_w = max(TERM_MIN_W, console.size.width or term_w)
                live.update(render(state, term_w))
                time.sleep(sleep_s)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()