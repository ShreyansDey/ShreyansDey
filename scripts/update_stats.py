"""
update_stats.py

Queries GitHub's GraphQL API directly for your real contribution calendar
(this correctly includes private contributions, since it's authenticated as
you via PAT_TOKEN) and renders a small SVG card showing:
  - Total contributions (last 12 months)
  - Current streak
  - Longest streak

...then saves it to generated/streak-stats.svg, which the README embeds as a
plain local file. Because it's a file living in your own repo instead of a
request to an external caching service, GitHub renders whatever the latest
commit contains -- no stale-cache problem like the herokuapp widget had.
"""

import os
import json
import datetime
import urllib.request

USERNAME = os.environ.get("GITHUB_USERNAME", "ShreyansDey")
TOKEN = os.environ["GITHUB_TOKEN"]
OUT_PATH = "generated/streak-stats.svg"

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      totalCommitContributions
      totalIssueContributions
      totalPullRequestContributions
      totalRepositoriesWithContributedCommits
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
    repositories(first: 100, ownerAffiliations: [OWNER], isFork: false, privacy: PUBLIC) {
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges {
            size
            node { name color }
          }
        }
      }
    }
  }
}
"""


def fetch_data():
    body = json.dumps({"query": QUERY, "variables": {"login": USERNAME}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
    return data["data"]["user"]


def fetch_calendar(user_data):
    return user_data["contributionsCollection"]["contributionCalendar"]


def compute_languages(user_data):
    totals = {}
    colors = {}
    for repo in user_data["repositories"]["nodes"]:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            totals[name] = totals.get(name, 0) + edge["size"]
            colors[name] = edge["node"]["color"] or "#858585"
    grand_total = sum(totals.values()) or 1
    ranked = sorted(totals.items(), key=lambda x: x[1], reverse=True)[:5]
    return [(name, size / grand_total * 100, colors[name]) for name, size in ranked]


def compute_stars(user_data):
    return sum(r["stargazerCount"] for r in user_data["repositories"]["nodes"])


def compute_streaks(calendar):
    days = []
    for week in calendar["weeks"]:
        for d in week["contributionDays"]:
            days.append((datetime.date.fromisoformat(d["date"]), d["contributionCount"]))
    days.sort(key=lambda x: x[0])

    longest = 0
    current_run = 0
    for _, count in days:
        if count > 0:
            current_run += 1
            longest = max(longest, current_run)
        else:
            current_run = 0

    # current streak: walk backward from most recent day
    current = 0
    today = datetime.date.today()
    for date, count in reversed(days):
        if date > today:
            continue
        if count > 0:
            current += 1
        else:
            # allow today to be zero (day not over yet) without breaking streak
            if date == today:
                continue
            break

    return current, longest


def render_svg(total, current, longest):
    return f"""<svg width="400" height="210" viewBox="0 0 400 210" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="borderGrad3" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#2f81f7"/>
      <stop offset="100%" stop-color="#1f2937"/>
    </linearGradient>
  </defs>
  <rect x="1" y="1" width="398" height="208" rx="12" fill="#0d1117" stroke="url(#borderGrad3)" stroke-width="1.2"/>

  <text x="83" y="90" font-family="Segoe UI, sans-serif" font-size="30" font-weight="700" fill="#58a6ff" text-anchor="middle">{total}</text>
  <text x="83" y="115" font-family="Segoe UI, sans-serif" font-size="12.5" fill="#8b949e" text-anchor="middle">Total Contributions</text>

  <line x1="155" y1="55" x2="155" y2="155" stroke="#21262d" stroke-width="1"/>

  <text x="200" y="90" font-family="Segoe UI, sans-serif" font-size="30" font-weight="700" fill="#e3b341" text-anchor="middle">{current}</text>
  <text x="200" y="115" font-family="Segoe UI, sans-serif" font-size="12.5" fill="#8b949e" text-anchor="middle">Current Streak</text>

  <line x1="245" y1="55" x2="245" y2="155" stroke="#21262d" stroke-width="1"/>

  <text x="317" y="90" font-family="Segoe UI, sans-serif" font-size="30" font-weight="700" fill="#3fb950" text-anchor="middle">{longest}</text>
  <text x="317" y="115" font-family="Segoe UI, sans-serif" font-size="12.5" fill="#8b949e" text-anchor="middle">Longest Streak</text>

  <text x="200" y="190" font-family="Segoe UI, sans-serif" font-size="10.5" fill="#484f58" text-anchor="middle">updated {datetime.date.today().isoformat()}</text>
</svg>"""


ICONS = {
    "Total Stars Earned": "\u2605",
    "Total Commits (last year)": "\u25C8",
    "Total PRs": "\u2387",
    "Total Issues": "\u2298",
    "Repos Contributed To": "\u25A3",
}


def render_overview_svg(stars, commits, prs, issues, contributed_to):
    rows = [
        ("Total Stars Earned", stars),
        ("Total Commits (last year)", commits),
        ("Total PRs", prs),
        ("Total Issues", issues),
        ("Repos Contributed To", contributed_to),
    ]
    row_svgs = []
    for i, (label, value) in enumerate(rows):
        y = 70 + i * 26
        icon = ICONS[label]
        row_svgs.append(
            f'<text x="30" y="{y}" font-family="Segoe UI, sans-serif" font-size="14" fill="#e3b341">{icon}</text>'
            f'<text x="52" y="{y}" font-family="Segoe UI, sans-serif" font-size="13.5" fill="#c9d1d9">{label}:</text>'
            f'<text x="365" y="{y}" font-family="Segoe UI, sans-serif" font-size="13.5" font-weight="600" fill="#58a6ff" text-anchor="end">{value}</text>'
        )
    body = "\n  ".join(row_svgs)
    return f"""<svg width="400" height="210" viewBox="0 0 400 210" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="borderGrad" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#2f81f7"/>
      <stop offset="100%" stop-color="#1f2937"/>
    </linearGradient>
  </defs>
  <rect x="1" y="1" width="398" height="208" rx="12" fill="#0d1117" stroke="url(#borderGrad)" stroke-width="1.2"/>
  <text x="30" y="35" font-family="Segoe UI, sans-serif" font-size="16" font-weight="700" fill="#e6edf3">Shreyans Dey's GitHub Stats</text>
  <line x1="30" y1="45" x2="370" y2="45" stroke="#21262d" stroke-width="1"/>
  {body}
</svg>"""


def render_languages_svg(languages):
    bar_w = 340
    x0 = 30
    segments = []
    x = x0
    for name, pct, color in languages:
        w = max(bar_w * pct / 100, 2)
        segments.append(f'<rect x="{x:.1f}" y="50" width="{w:.1f}" height="12" fill="{color}"/>')
        x += w
    legend = []
    for i, (name, pct, color) in enumerate(languages):
        col = i % 2
        row = i // 2
        lx = 30 + col * 190
        ly = 90 + row * 26
        legend.append(
            f'<circle cx="{lx}" cy="{ly - 4}" r="5" fill="{color}"/>'
            f'<text x="{lx + 14}" y="{ly}" font-family="Segoe UI, sans-serif" font-size="12.5" fill="#c9d1d9">{name} <tspan fill="#8b949e">{pct:.1f}%</tspan></text>'
        )
    legend_svg = "\n  ".join(legend)
    bar_bg = f'<rect x="{x0}" y="50" width="{bar_w}" height="12" rx="6" fill="#21262d"/>'
    return f"""<svg width="400" height="210" viewBox="0 0 400 210" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <clipPath id="barClip"><rect x="{x0}" y="50" width="{bar_w}" height="12" rx="6"/></clipPath>
    <linearGradient id="borderGrad2" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#2f81f7"/>
      <stop offset="100%" stop-color="#1f2937"/>
    </linearGradient>
  </defs>
  <rect x="1" y="1" width="398" height="208" rx="12" fill="#0d1117" stroke="url(#borderGrad2)" stroke-width="1.2"/>
  <text x="30" y="35" font-family="Segoe UI, sans-serif" font-size="16" font-weight="700" fill="#e6edf3">Most Used Languages</text>
  {bar_bg}
  <g clip-path="url(#barClip)">
    {''.join(segments)}
  </g>
  {legend_svg}
</svg>"""


def main():
    user_data = fetch_data()
    calendar = fetch_calendar(user_data)
    total = calendar["totalContributions"]
    current, longest = compute_streaks(calendar)

    cc = user_data["contributionsCollection"]
    stars = compute_stars(user_data)
    languages = compute_languages(user_data)

    os.makedirs("generated", exist_ok=True)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(render_svg(total, current, longest))

    with open("generated/overview.svg", "w", encoding="utf-8") as f:
        f.write(render_overview_svg(
            stars=stars,
            commits=cc["totalCommitContributions"],
            prs=cc["totalPullRequestContributions"],
            issues=cc["totalIssueContributions"],
            contributed_to=cc["totalRepositoriesWithContributedCommits"],
        ))

    with open("generated/languages.svg", "w", encoding="utf-8") as f:
        f.write(render_languages_svg(languages))

    print(f"total={total} current_streak={current} longest_streak={longest} stars={stars}")


if __name__ == "__main__":
    main()
