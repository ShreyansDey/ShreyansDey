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
  }
}
"""


def fetch_calendar():
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
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]


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


def main():
    calendar = fetch_calendar()
    total = calendar["totalContributions"]
    current, longest = compute_streaks(calendar)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(render_svg(total, current, longest))

    print(f"total={total} current_streak={current} longest_streak={longest}")


if __name__ == "__main__":
    main()
