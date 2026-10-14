import json, os, urllib.request, datetime, html
from pathlib import Path

OUT = Path("assets")
OUT.mkdir(exist_ok=True)

LOGIN = os.environ.get("GH_LOGIN", "BatuhanCakmak4")
TOKEN = os.environ["GITHUB_TOKEN"]

def gql(query, variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as response:
        payload = json.load(response)
    if "errors" in payload:
        raise RuntimeError(payload["errors"])
    return payload["data"]

today = datetime.datetime.now(datetime.timezone.utc).date()
frm = datetime.datetime.combine(today - datetime.timedelta(days=364), datetime.time.min, tzinfo=datetime.timezone.utc).isoformat()
to = datetime.datetime.combine(today, datetime.time.max, tzinfo=datetime.timezone.utc).isoformat()

query = '''
query($login:String!, $from:DateTime!, $to:DateTime!) {
  user(login:$login) {
    contributionsCollection(from:$from, to:$to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
    repositories(
      first: 100,
      ownerAffiliations: OWNER,
      privacy: PUBLIC,
      orderBy: {field: UPDATED_AT, direction: DESC}
    ) {
      nodes {
        name
        languages(first: 20, orderBy: {field: SIZE, direction: DESC}) {
          edges {
            size
            node { name }
          }
        }
      }
    }
  }
}
'''

data = gql(query, {"login": LOGIN, "from": frm, "to": to})["user"]
calendar = data["contributionsCollection"]["contributionCalendar"]
days = [d for w in calendar["weeks"] for d in w["contributionDays"]]
total = calendar["totalContributions"]

# Current + longest streak
pairs = [(datetime.date.fromisoformat(d["date"]), d["contributionCount"]) for d in days]
longest = 0
current = 0
run = 0
for dt, count in pairs:
    if count > 0:
        run += 1
        longest = max(longest, run)
    else:
        run = 0

for dt, count in reversed(pairs):
    if count > 0:
        current += 1
    elif dt == today and current == 0:
        continue
    else:
        break

# Weekly sparkline
weekly = []
for i in range(0, len(days), 7):
    weekly.append(sum(day["contributionCount"] for day in days[i:i+7]))
blocks = "▁▂▃▄▅▆▇█"
max_week = max(weekly) if weekly else 1
spark = "".join(blocks[min(7, int(v / max_week * 7))] if max_week else blocks[0] for v in weekly[-28:])

# Languages
lang_bytes = {}
for repo in data["repositories"]["nodes"]:
    for edge in repo["languages"]["edges"]:
        name = edge["node"]["name"]
        lang_bytes[name] = lang_bytes.get(name, 0) + edge["size"]

top_langs = sorted(lang_bytes.items(), key=lambda x: x[1], reverse=True)[:5]
total_lang_bytes = sum(v for _, v in top_langs) or 1

def card(title, lines, path, width=480, height=220):
    pieces = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" rx="18" fill="#0d1117" stroke="#30363d"/>',
        f'<text x="26" y="38" fill="#8b949e" font-family="monospace" font-size="15">{html.escape(title)}</text>',
    ]
    y = 78
    for text, size, color in lines:
        pieces.append(f'<text x="26" y="{y}" fill="{color}" font-family="monospace" font-size="{size}">{html.escape(str(text))}</text>')
        y += int(size * 1.65)
    pieces.append("</svg>")
    path.write_text("\n".join(pieces), encoding="utf-8")

card(
    "CONTRIBUTIONS / LAST 365 DAYS",
    [
        (total, 46, "#f0f6fc"),
        ("contributions", 16, "#8b949e"),
        (spark, 14, "#3fb950"),
    ],
    OUT / "stats.svg",
)

card(
    "STREAKS",
    [
        (f"{current} days", 40, "#f0f6fc"),
        ("current streak", 16, "#8b949e"),
        (f"{longest} days", 30, "#f0f6fc"),
        ("longest streak", 16, "#8b949e"),
    ],
    OUT / "streak.svg",
)

# Top languages card
lang_parts = [
    '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="220" viewBox="0 0 480 220">',
    '<rect width="100%" height="100%" rx="18" fill="#0d1117" stroke="#30363d"/>',
    '<text x="26" y="38" fill="#8b949e" font-family="monospace" font-size="15">TOP LANGUAGES / PUBLIC REPOS</text>',
]
y = 70
for name, size in top_langs:
    pct = size / total_lang_bytes * 100
    lang_parts.append(f'<text x="26" y="{y}" fill="#f0f6fc" font-family="monospace" font-size="16">{html.escape(name)}</text>')
    lang_parts.append(f'<text x="420" y="{y}" text-anchor="end" fill="#8b949e" font-family="monospace" font-size="14">{pct:.1f}%</text>')
    lang_parts.append(f'<rect x="26" y="{y+10}" width="394" height="7" rx="3.5" fill="#21262d"/>')
    lang_parts.append(f'<rect x="26" y="{y+10}" width="{394 * pct / 100:.1f}" height="7" rx="3.5" fill="#58a6ff"/>')
    y += 30
lang_parts.append("</svg>")
(OUT / "langs.svg").write_text("\n".join(lang_parts), encoding="utf-8")

# One character per day
ramp = " .:-=+*#%@"
max_count = max((d["contributionCount"] for d in days), default=1)
chars = "".join(
    ramp[min(len(ramp) - 1, round(day["contributionCount"] / max_count * (len(ramp) - 1)))] if max_count else ramp[0]
    for day in days
)
rows = [chars[i:i+61] for i in range(0, len(chars), 61)]
year_parts = [
    '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="220" viewBox="0 0 480 220">',
    '<rect width="100%" height="100%" rx="18" fill="#0d1117" stroke="#30363d"/>',
    '<text x="26" y="38" fill="#8b949e" font-family="monospace" font-size="15">YEAR / ONE CHARACTER PER DAY</text>',
]
y = 70
for row in rows[:6]:
    year_parts.append(f'<text x="26" y="{y}" fill="#3fb950" font-family="monospace" font-size="12" xml:space="preserve">{html.escape(row)}</text>')
    y += 22
year_parts.append("</svg>")
(OUT / "year.svg").write_text("\n".join(year_parts), encoding="utf-8")
