#!/usr/bin/env python3
"""Render the profile banner: a machine heartbeat above a commit candlestick chart.

  render.py beat  <dir>   run on the machine: record a beat if Kiki is up, refresh commits, render
  render.py watch <dir>   run in CI: re-render from saved state so a dead machine flatlines

<dir> holds state.json and pulse.svg. Only stdlib; no data leaves except beat times and
public contribution counts.
"""
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HEADLINE = ("My agent lives on this machine.", "Not in your cloud.")
TICKER = "$MIRACLE"

SLOT = 1800          # one ECG slot per 30 min
SLOTS = 48           # 24 hours on screen
STALE = 3 * 3600     # no beat for this long means flatline
WEEKS = 52

W, H = 900, 540
LEFT, RIGHT = 36, 864
GREEN, RED, INK, DIM, BG, RULE = "#5DCAA5", "#E24B4A", "#F5F5F0", "#9A9A94", "#0B0B0B", "#262624"
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"
SERIF = "Georgia,'Times New Roman','Noto Serif',serif"

QUERY = ("query{viewer{contributionsCollection{contributionCalendar{weeks{contributionDays"
         "{date contributionCount}}}}}}")


def machine_name():
    # hw.model is no use here: newer machines report ids like Mac16,10.
    out = subprocess.run(["system_profiler", "SPHardwareDataType"], capture_output=True, text=True).stdout
    for line in out.splitlines():
        if "Model Name:" in line:
            return line.split(":", 1)[1].strip().lower()
    return "mac"


def kiki_running():
    return subprocess.run(["pgrep", "-x", "Kiki"], capture_output=True).returncode == 0


def fetch_contributions():
    out = subprocess.run(["gh", "api", "graphql", "-f", f"query={QUERY}"],
                         capture_output=True, text=True, check=True).stdout
    weeks = json.loads(out)["data"]["viewer"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [[d["date"], d["contributionCount"]] for w in weeks for d in w["contributionDays"]]


def candles(days):
    """Price is commits in the trailing 7 days; each candle is one 7-day span of that price, newest last."""
    counts = [c for _, c in days]
    price = [sum(counts[max(0, i - 6):i + 1]) for i in range(len(counts))]
    end = len(price) - 1
    out = []
    while end >= 7 and len(out) < WEEKS:
        span = price[end - 7:end + 1]
        out.append((span[0], span[-1], min(span), max(span)))
        end -= 7
    return out[::-1], price


def change_label(price):
    now, before = price[-1], price[-8] if len(price) > 7 else 0
    if before == 0:
        return ("+∞%", GREEN) if now else ("0%", DIM)
    pct = round((now - before) / before * 100)
    return (f"{pct:+d}%", GREEN if pct >= 0 else RED)


def ecg_path(beats, now, top, base):
    """One slot per 30 min; a QRS complex where the machine actually reported in, flat where it did not."""
    start = now - SLOTS * SLOT
    hit = {int((b - start) // SLOT) for b in beats if start <= b <= now}
    step = (RIGHT - LEFT) / SLOTS
    amp = base - top
    d = [f"M{LEFT} {base}"]
    for i in range(SLOTS):
        x = LEFT + i * step
        if i in hit:
            for fx, fy in ((.15, 0), (.25, -.1), (.35, 0), (.42, .12), (.5, -1), (.6, .3), (.68, 0)):
                d.append(f"L{x + fx * step:.1f} {base + fy * amp:.1f}")
        d.append(f"L{x + step:.1f} {base}")
    return "".join(d)


def candle_marks(data, top, bottom):
    peak = max((c[3] for c in data), default=0) or 1
    y = lambda v: bottom - v / peak * (bottom - top)
    step = (RIGHT - LEFT) / max(len(data), 1)
    width = max(step * .62, 2)
    out = []
    for i, (o, c, lo, hi) in enumerate(data):
        x = LEFT + i * step
        mid = x + width / 2
        color = GREEN if c >= o else RED
        if hi == 0:
            color = "#3A3A37"
        body_top = y(max(o, c))
        body_h = max(y(min(o, c)) - body_top, 2)
        delay = i * 0.03
        out.append(f'<g class="candle" style="animation-delay:{delay:.2f}s">'
                   f'<line x1="{mid:.1f}" x2="{mid:.1f}" y1="{y(hi):.1f}" y2="{y(lo):.1f}" stroke="{color}" stroke-width="1.5"/>'
                   f'<rect x="{x:.1f}" y="{body_top:.1f}" width="{width:.1f}" height="{body_h:.1f}" fill="{color}"/></g>')
    return "".join(out)


def render(state, now):
    beats = state["beats"]
    last = max(beats, default=0)
    alive = bool(last) and now - last < STALE
    data, price = candles(state["days"])
    label, label_color = change_label(price)
    color = GREEN if alive else RED
    stamp = datetime.fromtimestamp(last, timezone.utc).strftime("%b %-d %H:%M utc").lower() if last else "never"
    status = (f"alive · {state['machine']} · last beat {stamp}" if alive
              else f"flatline · {state['machine']} · no beat since {stamp}")
    anim = 'class="ecg"' if alive else ""
    dot = 'class="dot"' if alive else ""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{HEADLINE[0]} {HEADLINE[1]} {status}. {TICKER} chart of weekly commits.">
<style>
.ecg{{stroke-dasharray:1;animation:scan 6s linear infinite}}
.dot{{animation:pulse 1.6s ease-in-out infinite}}
.candle{{animation:in .3s ease-out backwards}}
@keyframes scan{{0%{{stroke-dashoffset:1}}85%,100%{{stroke-dashoffset:0}}}}
@keyframes pulse{{50%{{opacity:.25}}}}
@keyframes in{{from{{opacity:0}}}}
@media (prefers-reduced-motion:reduce){{.ecg,.dot,.candle{{animation:none}}}}
</style>
<rect width="{W}" height="{H}" rx="14" fill="{BG}"/>
<text x="{LEFT}" y="84" fill="{INK}" font-family="{SERIF}" font-size="56" textLength="{RIGHT - LEFT}" lengthAdjust="spacingAndGlyphs">{HEADLINE[0]}</text>
<text x="{LEFT}" y="148" fill="{INK}" font-family="{SERIF}" font-size="56" textLength="470" lengthAdjust="spacingAndGlyphs">{HEADLINE[1]}</text>
<path fill="none" stroke="{color}" stroke-opacity=".3" stroke-width="2" stroke-linejoin="round" d="{ecg_path(beats, now, 170, 228)}"/>
<path {anim} pathLength="1" fill="none" stroke="{color}" stroke-width="2.5" stroke-linejoin="round" d="{ecg_path(beats, now, 170, 228)}"/>
<circle {dot} cx="{LEFT + 6}" cy="264" r="5" fill="{color}"/>
<text x="{LEFT + 22}" y="270" fill="{DIM}" font-family="{MONO}" font-size="18">{status}</text>
<line x1="{LEFT}" x2="{RIGHT}" y1="298" y2="298" stroke="{RULE}"/>
<text x="{LEFT}" y="342" fill="{INK}" font-family="{MONO}" font-size="30">{TICKER}</text>
<text x="{LEFT + 170}" y="342" fill="{label_color}" font-family="{MONO}" font-size="22">{label} wk</text>
<text x="{RIGHT}" y="342" text-anchor="end" fill="{DIM}" font-family="{MONO}" font-size="18">ath {max(price, default=0)} commits/wk</text>
<g>{candle_marks(data, 360, 486)}</g>
<text x="{LEFT}" y="520" fill="{DIM}" font-family="{MONO}" font-size="16">my real commits, priced weekly. not financial advice.</text>
</svg>
'''


def load(folder):
    path = folder / "state.json"
    return json.loads(path.read_text()) if path.exists() else {"beats": [], "days": [], "machine": "mac"}


def main():
    mode, folder = sys.argv[1], Path(sys.argv[2])
    folder.mkdir(parents=True, exist_ok=True)
    state = load(folder)
    now = time.time()
    if mode == "beat":
        state["machine"] = machine_name()
        state["days"] = fetch_contributions()
        if kiki_running():
            state["beats"].append(int(now))
        state["beats"] = [b for b in state["beats"] if now - b <= SLOTS * SLOT]
    elif mode == "watch":
        if now - max(state["beats"], default=0) < STALE:
            return
    else:
        sys.exit(f"unknown mode: {mode}")
    (folder / "state.json").write_text(json.dumps(state))
    (folder / "pulse.svg").write_text(render(state, now))


if __name__ == "__main__":
    main()
