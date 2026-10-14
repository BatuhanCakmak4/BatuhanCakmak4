#!/usr/bin/env python3
import datetime as dt
import html
import json
import os
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
README = ROOT / "README.md"
LOGIN = os.environ.get("GH_LOGIN", "BatuhanCakmak4")
TOKEN = os.environ["GITHUB_TOKEN"]

BG = "#0d1117"
BORDER = "#30363d"
FG = "#f0f6fc"
MUTED = "#8b949e"
GREEN = "#3fb950"
BLUE = "#58a6ff"
FONT = "JetBrains Mono, Liberation Mono, DejaVu Sans Mono, monospace"

def graphql(query, variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "BatuhanCakmak4-profile",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        payload = json.load(response)
    if payload.get("errors"):
        raise RuntimeError(payload["errors"])
    return payload["data"]

today = dt.datetime.now(dt.timezone.utc).date()
start_day = today - dt.timedelta(days=364)
from_iso = f"{start_day.isoformat()}T00:00:00Z"
to_iso = f"{today.isoformat()}T23:59:59Z"

QUERY = '''
query($login:String!, $from:DateTime!, $to:DateTime!) {
  user(login:$login) {
    contributionsCollection(from:$from, to:$to) {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
    repositories(first:100, ownerAffiliations:OWNER, privacy:PUBLIC, isFork:false,
      orderBy:{field:UPDATED_AT,direction:DESC}) {
      nodes {
        name
        languages(first:20, orderBy:{field:SIZE,direction:DESC}) {
          edges { size node { name } }
        }
      }
    }
  }
}
'''

user = graphql(QUERY, {"login": LOGIN, "from": from_iso, "to": to_iso})["user"]
calendar = user["contributionsCollection"]["contributionCalendar"]
days = [d for week in calendar["weeks"] for d in week["contributionDays"]]
total = calendar["totalContributions"]
pairs = [(dt.date.fromisoformat(d["date"]), int(d["contributionCount"])) for d in days]

longest = 0
run = 0
for _, count in pairs:
    if count > 0:
        run += 1
        longest = max(longest, run)
    else:
        run = 0

current = 0
for day, count in reversed(pairs):
    if count > 0:
        current += 1
    elif day == today and current == 0:
        continue
    else:
        break

weekly = []
for i in range(0, len(days), 7):
    weekly.append(sum(int(d["contributionCount"]) for d in days[i:i+7]))

lang_bytes = {}
repo_count = 0
for repo in user["repositories"]["nodes"]:
    repo_count += 1
    for edge in repo["languages"]["edges"]:
        name = edge["node"]["name"]
        lang_bytes[name] = lang_bytes.get(name, 0) + int(edge["size"])

top_langs = sorted(lang_bytes.items(), key=lambda kv: kv[1], reverse=True)[:6]
lang_total = sum(v for _, v in top_langs) or 1

def esc(v):
    return html.escape(str(v))

def write_stats():
    w, h = 560, 230
    bars = weekly[-26:]
    max_bar = max(bars) if bars else 1
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
        f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="18" fill="{BG}" stroke="{BORDER}"/>',
        f'<text x="28" y="37" fill="{MUTED}" font-family="{FONT}" font-size="15">CONTRIBUTIONS / 365 DAYS</text>',
        f'<text x="28" y="101" fill="{FG}" font-family="{FONT}" font-size="48">{total}</text>',
        f'<text x="28" y="128" fill="{MUTED}" font-family="{FONT}" font-size="15">total contributions</text>',
    ]
    x0, chart_y, gap, bw = 28, 196, 4, 14
    for i, v in enumerate(bars):
        bh = 0 if max_bar == 0 else 48 * v / max_bar
        x = x0 + i*(bw+gap)
        p.append(f'<rect x="{x}" y="{chart_y-bh:.1f}" width="{bw}" height="{bh:.1f}" rx="2" fill="{GREEN}"/>')
    p += [
        f'<text x="532" y="128" text-anchor="end" fill="{MUTED}" font-family="{FONT}" font-size="14">{len([c for _,c in pairs if c>0])} active days</text>',
        '</svg>'
    ]
    (ASSETS/"stats.svg").write_text("\n".join(p), encoding="utf-8")

def write_streak():
    w, h = 560, 230
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
        f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="18" fill="{BG}" stroke="{BORDER}"/>',
        f'<text x="28" y="37" fill="{MUTED}" font-family="{FONT}" font-size="15">STREAKS</text>',
        f'<text x="28" y="103" fill="{FG}" font-family="{FONT}" font-size="44">{current}</text>',
        f'<text x="28" y="130" fill="{MUTED}" font-family="{FONT}" font-size="15">current streak / days</text>',
        f'<line x1="280" y1="58" x2="280" y2="190" stroke="{BORDER}"/>',
        f'<text x="310" y="103" fill="{FG}" font-family="{FONT}" font-size="44">{longest}</text>',
        f'<text x="310" y="130" fill="{MUTED}" font-family="{FONT}" font-size="15">longest streak / days</text>',
        f'<text x="28" y="190" fill="{GREEN}" font-family="{FONT}" font-size="15">public activity, whole UTC days</text>',
        '</svg>'
    ]
    (ASSETS/"streak.svg").write_text("\n".join(p), encoding="utf-8")

def write_langs():
    w, h = 560, 265
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
        f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="18" fill="{BG}" stroke="{BORDER}"/>',
        f'<text x="28" y="37" fill="{MUTED}" font-family="{FONT}" font-size="15">TOP LANGUAGES / PUBLIC OWNED REPOS</text>',
    ]
    y = 70
    for name, size in top_langs:
        pct = size / lang_total * 100
        p += [
            f'<text x="28" y="{y}" fill="{FG}" font-family="{FONT}" font-size="15">{esc(name)}</text>',
            f'<text x="526" y="{y}" text-anchor="end" fill="{MUTED}" font-family="{FONT}" font-size="14">{pct:.1f}%</text>',
            f'<rect x="28" y="{y+10}" width="498" height="7" rx="3.5" fill="#21262d"/>',
            f'<rect x="28" y="{y+10}" width="{498*pct/100:.1f}" height="7" rx="3.5" fill="{BLUE}"/>',
        ]
        y += 32
    p += [
        f'<text x="28" y="246" fill="{MUTED}" font-family="{FONT}" font-size="13">{repo_count} public owned repositories scanned</text>',
        '</svg>'
    ]
    (ASSETS/"langs.svg").write_text("\n".join(p), encoding="utf-8")

def write_year():
    w, h = 560, 265
    ramp = " .`:-=+*cs#%@"
    max_count = max((c for _,c in pairs), default=1) or 1
    chars = "".join(ramp[min(len(ramp)-1, round(c/max_count*(len(ramp)-1)))] for _,c in pairs)
    rows = [chars[i:i+61] for i in range(0, len(chars), 61)]
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
        f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="18" fill="{BG}" stroke="{BORDER}"/>',
        f'<text x="28" y="37" fill="{MUTED}" font-family="{FONT}" font-size="15">YEAR / ONE CHARACTER PER DAY</text>',
    ]
    y = 75
    for row in rows[:6]:
        p.append(f'<text x="28" y="{y}" fill="{GREEN}" font-family="{FONT}" font-size="12" xml:space="preserve">{esc(row)}</text>')
        y += 27
    p += [
        f'<text x="28" y="246" fill="{MUTED}" font-family="{FONT}" font-size="13">quiet → loud: space  .  `  :  -  =  +  *  c  s  #  %  @</text>',
        '</svg>'
    ]
    (ASSETS/"year.svg").write_text("\n".join(p), encoding="utf-8")

write_stats()
write_streak()
write_langs()
write_year()

text = README.read_text(encoding="utf-8")
start = "<!-- GENERATED_STATS_START -->"
end = "<!-- GENERATED_STATS_END -->"
block = (
    '<!-- GENERATED_STATS_START -->\n'
    '<p align="center">\n'
    '  <img src="./assets/stats.svg" width="49%" alt="365-day contribution summary">\n'
    '  <img src="./assets/streak.svg" width="49%" alt="Contribution streaks">\n'
    '</p>\n'
    '<p align="center">\n'
    '  <img src="./assets/langs.svg" width="49%" alt="Top public repository languages">\n'
    '  <img src="./assets/year.svg" width="49%" alt="One character per day yearly activity">\n'
    '</p>\n'
    '<!-- GENERATED_STATS_END -->'
)
a = text.index(start)
b = text.index(end) + len(end)
README.write_text(text[:a] + block + text[b:], encoding="utf-8")
