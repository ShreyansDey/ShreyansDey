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
    return f"""<svg width="495" height="200" viewBox="0 0 495 200" xmlns="http://www.w3.org/2000/svg">
  <rect x="0.5" y="0.5" width="494" height="199" rx="10" fill="#1a1b27" stroke="#2C5364"/>
  <text x="82" y="70" font-family="Segoe UI, sans-serif" font-size="28" font-weight="bold" fill="#2C5364" text-anchor="middle">{total}</text>
  <text x="82" y="95" font-family="Segoe UI, sans-serif" font-size="13" fill="#a9b1d6" text-anchor="middle">Total Contributions</text>

  <line x1="185" y1="40" x2="185" y2="160" stroke="#2C5364" stroke-width="1"/>

  <text x="247" y="70" font-family="Segoe UI, sans-serif" font-size="28" font-weight="bold" fill="#e0af68" text-anchor="middle">{current}</text>
  <text x="247" y="95" font-family="Segoe UI, sans-serif" font-size="13" fill="#a9b1d6" text-anchor="middle">Current Streak</text>

  <line x1="310" y1="40" x2="310" y2="160" stroke="#2C5364" stroke-width="1"/>

  <text x="410" y="70" font-family="Segoe UI, sans-serif" font-size="28" font-weight="bold" fill="#7dcfff" text-anchor="middle">{longest}</text>
  <text x="410" y="95" font-family="Segoe UI, sans-serif" font-size="13" fill="#a9b1d6" text-anchor="middle">Longest Streak</text>

  <text x="247" y="185" font-family="Segoe UI, sans-serif" font-size="10" fill="#565f89" text-anchor="middle">updated {datetime.date.today().isoformat()}</text>
</svg>"""


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
        y = 55 + i * 28
        row_svgs.append(
            f'<text x="25" y="{y}" font-family="Segoe UI, sans-serif" font-size="14" fill="#a9b1d6">{label}:</text>'
            f'<text x="315" y="{y}" font-family="Segoe UI, sans-serif" font-size="14" font-weight="bold" fill="#7dcfff" text-anchor="end">{value}</text>'
        )
    body = "\n  ".join(row_svgs)
    return f"""<svg width="340" height="200" viewBox="0 0 340 200" xmlns="http://www.w3.org/2000/svg">
  <rect x="0.5" y="0.5" width="339" height="199" rx="10" fill="#1a1b27" stroke="#2C5364"/>
  <text x="25" y="30" font-family="Segoe UI, sans-serif" font-size="15" font-weight="bold" fill="#2C5364">Shreyans Dey's GitHub Stats</text>
  {body}
</svg>"""


def render_languages_svg(languages):
    bar_w = 300
    x = 20
    segments = []
    for name, pct, color in languages:
        w = max(bar_w * pct / 100, 2)
        segments.append(f'<rect x="{x:.1f}" y="35" width="{w:.1f}" height="14" rx="3" fill="{color}"/>')
        x += w
    legend = []
    for i, (name, pct, color) in enumerate(languages):
        col = i % 2
        row = i // 2
        lx = 20 + col * 170
        ly = 75 + row * 26
        legend.append(
            f'<circle cx="{lx}" cy="{ly - 4}" r="5" fill="{color}"/>'
            f'<text x="{lx + 12}" y="{ly}" font-family="Segoe UI, sans-serif" font-size="12" fill="#a9b1d6">{name} {pct:.1f}%</text>'
        )
    legend_svg = "\n  ".join(legend)
    return f"""<svg width="340" height="200" viewBox="0 0 340 200" xmlns="http://www.w3.org/2000/svg">
  <rect x="0.5" y="0.5" width="339" height="199" rx="10" fill="#1a1b27" stroke="#2C5364"/>
  <text x="20" y="25" font-family="Segoe UI, sans-serif" font-size="15" font-weight="bold" fill="#2C5364">Most Used Languages</text>
  {''.join(segments)}
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
