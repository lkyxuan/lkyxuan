#!/usr/bin/env python3
"""Render the profile banner: a six-track sequencer. Five tracks are my commits per day, sorted by
what kind of repo they went to; the sixth is this machine's heartbeat.

  render.py beat  <dir>   run on the machine: record a beat if Kiki is up, refresh commits, render
  render.py watch <dir>   run in CI: re-render from saved state so a dead machine flatlines

<dir> holds state.json and pulse.svg. Only stdlib; no data leaves except beat times and
per-day commit counts (repo names are reduced to a track before they are saved).
"""
import json
import math
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

NAME = "0XMIRACLE"
TAGLINE = "local-first AI agents × crypto · building kiki"

SLOT = 1800          # one heartbeat step per 30 min
STEPS = 48           # 48 steps: 24 h of heartbeat, 48 days of commits
STALE = 3 * 3600     # no beat for this long means flatline

W, H = 900, 540
LEFT, GRID, RIGHT = 36, 168, 864
TOP, LANE = 150, 52
BG, INK, DIM, OFF, OFF2, RED = "#0A0A0A", "#EDEDE6", "#6E6E68", "#1C1C1A", "#232320", "#E24B4A"
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"
SANS = "-apple-system,BlinkMacSystemFont,'Helvetica Neue','PingFang SC','Noto Sans CJK SC',sans-serif"

# (name, 中文, colour). The last track is the heartbeat.
TRACKS = [("HACKER", "黑客", "#5DCAA5"), ("PAINTER", "画家", "#F2A65A"), ("BAZAAR", "集市", "#E8D44D"),
          ("CATHEDRAL", "大教堂", "#B08CFF"), ("DESIGNER", "设计师", "#FF5D8F"), ("TECHNO", "节拍", "#4FB3FF")]
CATHEDRAL = {"kiki", "kiki-core", "kiki-agent"}
DESIGNER = {"SignalStudio", "lkyxuan", "lkyxuan.github.io", "cyberight.capital"}


def track_of(repo):
    """Cathedral is the core; bazaar is anything plugged into it; painter is how it looks; the rest is hacking."""
    if repo in CATHEDRAL:
        return 3
    if repo in DESIGNER:
        return 4
    if repo.startswith("kiki-theme-") or repo in {"kiki-pet", "lumia"}:
        return 1
    if repo.startswith(("kiki-plugin-", "kiki-")) or repo.endswith("-kiki"):
        return 2
    return 0


def machine_name():
    # hw.model is no use here: newer machines report ids like Mac16,10.
    out = subprocess.run(["system_profiler", "SPHardwareDataType"], capture_output=True, text=True).stdout
    for line in out.splitlines():
        if "Model Name:" in line:
            return line.split(":", 1)[1].strip().lower()
    return "mac"


def kiki_running():
    return subprocess.run(["pgrep", "-x", "Kiki"], capture_output=True).returncode == 0


def fetch_tracks(today):
    """Per-day commit counts for the last STEPS days, summed per track. Same numbers as the contribution graph."""
    start = today - timedelta(days=STEPS - 1)
    query = ('query($from:DateTime!,$to:DateTime!){viewer{contributionsCollection(from:$from,to:$to)'
             '{commitContributionsByRepository(maxRepositories:100){repository{name}'
             'contributions(first:100){nodes{occurredAt commitCount}}}}}}')
    out = subprocess.run(["gh", "api", "graphql", "-f", f"query={query}",
                          "-f", f"from={start}T00:00:00Z", "-f", f"to={today}T23:59:59Z"],
                         capture_output=True, text=True, check=True).stdout
    repos = json.loads(out)["data"]["viewer"]["contributionsCollection"]["commitContributionsByRepository"]
    days = {(start + timedelta(days=i)).isoformat(): [0] * 5 for i in range(STEPS)}
    for r in repos:
        t = track_of(r["repository"]["name"])
        for n in r["contributions"]["nodes"]:
            d = n["occurredAt"][:10]
            if d in days:
                days[d][t] += n["commitCount"]
    return [[d, *v] for d, v in sorted(days.items())]


def heartbeat(beats, now):
    start = now - STEPS * SLOT
    hit = {int((b - start) // SLOT) for b in beats if start <= b <= now}
    return [1 if i in hit else 0 for i in range(STEPS)]


def render(state, now):
    beats = state["beats"]
    last = max(beats, default=0)
    alive = bool(last) and now - last < STALE
    hb = heartbeat(beats, now) if alive else [0] * STEPS
    rows = state.get("tracks") or []
    lanes = [[r[1 + k] for r in rows[-STEPS:]] for k in range(5)] + [hb]
    stamp = datetime.fromtimestamp(last, timezone.utc).strftime("%b %-d %H:%M utc").lower() if last else "never"
    machine = state.get("machine", "mac")
    if alive:
        big, big_color = f"{sum(hb)}/{STEPS}", TRACKS[5][2]
        sub = f"{machine} · alive · {stamp}"
    else:
        big, big_color = "FLATLINE", RED
        sub = f"{machine} · no beat since {stamp}"
    step = (RIGHT - GRID) / STEPS
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
         f'aria-label="{NAME}: a six-track sequencer. Hacker, painter, bazaar, cathedral and designer are my commits per day; techno is this machine\'s heartbeat. {sub}.">',
         "<style>"
         f".ph{{animation:ph 6s steps({STEPS}) infinite}}@keyframes ph{{to{{transform:translateX({RIGHT - GRID}px)}}}}"
         ".k{animation:k .48s ease-out infinite}@keyframes k{50%{opacity:.4}}"
         "@media (prefers-reduced-motion:reduce){.ph,.k{animation:none}}</style>",
         f'<rect width="{W}" height="{H}" rx="14" fill="{BG}"/>',
         f'<text x="{LEFT}" y="66" fill="{INK}" font-family="{MONO}" font-size="34" font-weight="700" letter-spacing="2">{NAME}</text>',
         f'<text x="{LEFT}" y="98" fill="{DIM}" font-family="{MONO}" font-size="15">{TAGLINE}</text>',
         f'<text x="{RIGHT}" y="66" text-anchor="end" fill="{big_color}" font-family="{MONO}" font-size="34" font-weight="700">{big}</text>',
         f'<text x="{RIGHT}" y="98" text-anchor="end" fill="{DIM}" font-family="{MONO}" font-size="15">{sub}</text>']
    for k, ((name, zh, color), vals) in enumerate(zip(TRACKS, lanes)):
        y = TOP + k * LANE
        if k == 5 and not alive:
            color = RED
        peak = max(vals, default=0) or 1
        o.append(f'<text x="{LEFT}" y="{y + 22}" fill="{color}" font-family="{MONO}" font-size="17" font-weight="700" letter-spacing="1">{name}</text>')
        o.append(f'<text x="{LEFT}" y="{y + 42}" fill="{DIM}" font-family="{SANS}" font-size="13">{zh}</text>')
        for i in range(STEPS):
            v = vals[i] if i < len(vals) else 0
            x = GRID + i * step
            box = f'x="{x + 1.5:.1f}" y="{y + 6}" width="{step - 3:.1f}" height="36" rx="3"'
            if v:
                op = .35 + .65 * min(1, math.sqrt(v / peak))
                cls = ' class="k"' if k == 5 else ""
                o.append(f'<rect{cls} {box} fill="{color}" opacity="{op:.2f}"/>')
            else:
                o.append(f'<rect {box} fill="{OFF2 if (i // 4) % 2 else OFF}"/>')
    if not alive:
        y = TOP + 5 * LANE + 24
        o.append(f'<line x1="{GRID}" x2="{RIGHT}" y1="{y}" y2="{y}" stroke="{RED}" stroke-width="2"/>')
    o.append(f'<rect class="ph" x="{GRID}" y="{TOP}" width="{step:.1f}" height="{6 * LANE}" fill="#fff" opacity=".08"/>')
    o.append(f'<text x="{LEFT}" y="{H - 24}" fill="{DIM}" font-family="{MONO}" font-size="13">'
             f'rows 1-5: my commits per day, last {STEPS} days · row 6: this machine&#8217;s heartbeat, every 30 min</text>')
    o.append("</svg>\n")
    return "\n".join(o)


def load(folder):
    path = folder / "state.json"
    return json.loads(path.read_text()) if path.exists() else {"beats": [], "tracks": [], "machine": "mac"}


def main():
    mode, folder = sys.argv[1], Path(sys.argv[2])
    folder.mkdir(parents=True, exist_ok=True)
    state = load(folder)
    state.pop("days", None)  # the old candlestick data
    now = time.time()
    if mode == "beat":
        state["machine"] = machine_name()
        state["tracks"] = fetch_tracks(datetime.now(timezone.utc).date())
        if kiki_running():
            state["beats"].append(int(now))
        state["beats"] = [b for b in state["beats"] if now - b <= STEPS * SLOT]
    elif mode == "watch":
        if now - max(state["beats"], default=0) < STALE:
            return
    elif mode == "preview":  # render from saved state without touching it
        pass
    else:
        sys.exit(f"unknown mode: {mode}")
    if mode != "preview":
        (folder / "state.json").write_text(json.dumps(state))
    (folder / "pulse.svg").write_text(render(state, now))


if __name__ == "__main__":
    main()
