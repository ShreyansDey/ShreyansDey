"""
update_skills.py

Scans every public repo under GITHUB_USERNAME for:
  - its primary language (from the GitHub API)
  - its repo "topics" (the tags you set under Settings > Topics on each repo)

...and rebuilds the "Tech Stack" section of README.md from whatever it finds,
between the <!-- SKILLS:START --> and <!-- SKILLS:END --> markers.

How to add a new skill so it shows up on your profile:
  Just tag the relevant repo with a topic, e.g. add the topic "docker" to a
  repo that uses Docker. Next time the workflow runs (daily, or manually via
  "Run workflow"), that badge appears automatically. No README editing needed.

Known topics get a proper colored badge (see BADGE_MAP below). Unknown/new
topics still get a plain badge so nothing is silently dropped -- add them to
BADGE_MAP over time for nicer styling.
"""

import os
import re
import sys
import urllib.request
import json

USERNAME = os.environ.get("GITHUB_USERNAME", "ShreyansDey")
TOKEN = os.environ.get("GITHUB_TOKEN")
README_PATH = "README.md"

START_MARKER = "<!-- SKILLS:START -->"
END_MARKER = "<!-- SKILLS:END -->"

# topic/language slug -> shields.io badge markdown
BADGE_MAP = {
    "c": "https://img.shields.io/badge/C-00599C?style=for-the-badge&logo=c&logoColor=white",
    "c++": "https://img.shields.io/badge/C++-00599C?style=for-the-badge&logo=c%2B%2B&logoColor=white",
    "cpp": "https://img.shields.io/badge/C++-00599C?style=for-the-badge&logo=c%2B%2B&logoColor=white",
    "python": "https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white",
    "java": "https://img.shields.io/badge/Java-ED8B00?style=for-the-badge&logo=openjdk&logoColor=white",
    "javascript": "https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black",
    "html": "https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white",
    "css": "https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white",
    "react": "https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB",
    "flask": "https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white",
    "sqlalchemy": "https://img.shields.io/badge/SQLAlchemy-D71F00?style=for-the-badge&logo=sqlite&logoColor=white",
    "sql": "https://img.shields.io/badge/SQL-4479A1?style=for-the-badge&logo=mysql&logoColor=white",
    "node": "https://img.shields.io/badge/Node.js-339933?style=for-the-badge&logo=nodedotjs&logoColor=white",
    "nodejs": "https://img.shields.io/badge/Node.js-339933?style=for-the-badge&logo=nodedotjs&logoColor=white",
    "express": "https://img.shields.io/badge/Express-000000?style=for-the-badge&logo=express&logoColor=white",
    "docker": "https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white",
    "git": "https://img.shields.io/badge/Git-F05032?style=for-the-badge&logo=git&logoColor=white",
    "linux": "https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black",
    "jwt": "https://img.shields.io/badge/JWT-000000?style=for-the-badge&logo=jsonwebtokens&logoColor=white",
    "oauth": "https://img.shields.io/badge/OAuth2-3C3C3D?style=for-the-badge&logo=auth0&logoColor=white",
}


def api_get(url):
    req = urllib.request.Request(url)
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def collect_skills():
    skills = set()
    page = 1
    while True:
        repos = api_get(
            f"https://api.github.com/users/{USERNAME}/repos?per_page=100&page={page}"
        )
        if not repos:
            break
        for repo in repos:
            if repo.get("fork"):
                continue
            lang = repo.get("language")
            if lang:
                skills.add(lang.lower())
            for topic in repo.get("topics", []):
                skills.add(topic.lower())
        page += 1
    return skills


def badge_for(skill):
    url = BADGE_MAP.get(skill)
    if url:
        return f'<img src="{url}"/>'
    # fallback: plain grey badge so unknown/new topics still show up
    label = skill.replace("-", "%20").replace(" ", "%20")
    return f'<img src="https://img.shields.io/badge/{label}-555555?style=for-the-badge"/>'


def build_block(skills):
    ordered = sorted(skills)
    badges = "\n".join(badge_for(s) for s in ordered)
    return f"{START_MARKER}\n<p align=\"left\">\n{badges}\n</p>\n{END_MARKER}"


def main():
    skills = collect_skills()
    if not skills:
        print("No skills found, leaving README untouched.")
        return

    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    new_block = build_block(skills)
    pattern = re.compile(
        re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER), re.DOTALL
    )

    if pattern.search(content):
        content = pattern.sub(new_block, content)
    else:
        content += f"\n\n{new_block}\n"

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Updated skills block with: {', '.join(sorted(skills))}")


if __name__ == "__main__":
    main()
