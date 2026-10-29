#!/usr/bin/env python3
"""Create a GitHub overview and multi-language repository distribution SVG.

Uses only the Python standard library and GitHub's public REST API.
A language counts for a repo if it represents at least 5% of source bytes.
"""

from __future__ import annotations

import collections
import html
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

OWNER = "asilgumus"
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets"
MIN_SHARE = 0.05
MAX_LANGUAGES = 6

COLORS = {
    "Python": "#3572A5", "Java": "#B07219", "JavaScript": "#F1E05A",
    "TypeScript": "#3178C6", "Rust": "#DEA584", "C++": "#F34B7D",
    "C": "#555555", "C#": "#178600", "HTML": "#E34C26",
    "CSS": "#563D7C", "Dart": "#00B4AB", "Kotlin": "#A97BFF",
    "Shell": "#89E051", "Go": "#00ADD8", "PHP": "#4F5D95",
    "Jupyter Notebook": "#DA5B0B", "Vue": "#41B883", "Swift": "#F05138",
}


def api(path: str, params: dict | None = None):
    url = "https://api.github.com" + path
    if params:
        url += "?" + urlencode(params)
    token = os.getenv("GH_TOKEN", "")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "asilgumus-profile-cards",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = "Bearer " + token
    try:
        with urlopen(Request(url, headers=headers), timeout=25) as response:
            return json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f"GitHub API returned {exc.code} for {path}") from exc


def list_public_repositories():
    all_repos = []
    for page in range(1, 21):
        batch = api(f"/users/{OWNER}/repos", {"per_page": 100, "page": page, "type": "owner"})
        if not isinstance(batch, list):
            raise RuntimeError("Unexpected repository API response")
        all_repos.extend(batch)
        if len(batch) < 100:
            break
    return [
        repo for repo in all_repos
        if repo.get("owner", {}).get("login", "").lower() == OWNER
        and not repo.get("fork")
        and not repo.get("archived")
        and not repo.get("disabled")
        and repo.get("name", "").lower() != OWNER  # exclude profile README repository
    ]


def esc(value):
    return html.escape(str(value), quote=True)


def make_overview(total_repos: int, stars: int, followers: int, lang_count: int):
    """Curated engineering highlights, rather than vanity metrics."""
    projects = [
        ("01", "AETHER OS", "Systems programming", "Rust  /  x86-64"),
        ("02", "CYBERRCORE", "Autonomous robotics", "Embedded  /  Control"),
        ("03", "NEUROMETRIC", "Applied machine learning", "Python  /  3D CNN"),
    ]
    parts = []
    for i, (number, name, subtitle, stack) in enumerate(projects):
        x = 40 + i * 267
        parts.extend([
            f'<text x="{x}" y="83" fill="#8b7cf6" font-size="13" font-weight="700">{number} /</text>',
            f'<text x="{x}" y="115" fill="#f0f3ff" font-size="21" font-weight="700">{esc(name)}</text>',
            f'<text x="{x}" y="142" fill="#c2c7d8" font-size="14">{esc(subtitle)}</text>',
            f'<text x="{x}" y="169" fill="#8b949e" font-size="12">{esc(stack)}</text>',
        ])
        if i < 2:
            parts.append(f'<line x1="{x + 241}" y1="74" x2="{x + 241}" y2="173" stroke="#30363d"/>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="840" height="205" viewBox="0 0 840 205" font-family="Segoe UI, Arial, sans-serif" role="img" aria-label="Selected engineering work: AETHER OS, CYBERRCORE, NeuroMetric">
<rect x="1" y="1" width="838" height="203" rx="14" fill="#0d1117" stroke="#30363d"/>
<text x="40" y="37" fill="#e6edf3" font-size="19" font-weight="700">Selected engineering work</text>
<text x="40" y="56" fill="#8b949e" font-size="12">Systems  /  Robotics  /  Applied AI</text>
{''.join(parts)}
</svg>'''


def make_language_card(language_counts: collections.Counter, total: int):
    entries = sorted(language_counts.items(), key=lambda it: (-it[1], it[0]))[:MAX_LANGUAGES]
    row_height = 40
    height = 96 + len(entries) * row_height + 45
    parts = []
    for i, (language, count) in enumerate(entries):
        y = 102 + i * row_height
        percent = 100 * count / total
        color = COLORS.get(language, "#8b7cf6")
        parts.append(f'<circle cx="48" cy="{y - 5}" r="6" fill="{color}"/>')
        parts.append(f'<text x="66" y="{y}" font-size="14" font-weight="600" fill="#e6edf3">{esc(language)}</text>')
        # Keep the repository count and percentage on the SAME baseline.
        # Reserve separate horizontal columns so no label can slip below its bar.
        bar_width = 415
        parts.append(f'<rect x="251" y="{y - 12}" width="{bar_width}" height="11" rx="5.5" fill="#21262d"/>')
        parts.append(f'<rect x="251" y="{y - 12}" width="{bar_width * min(percent, 100)/100:.2f}" height="11" rx="5.5" fill="{color}"/>')
        parts.append(f'<text x="690" y="{y}" font-size="11.5" fill="#8b949e" text-anchor="start">{count} repos</text>')
        parts.append(f'<text x="805" y="{y}" font-size="14" fill="#e6edf3" font-weight="700" text-anchor="end">{percent:.1f}%</text>')
    footer_y = height - 20
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="840" height="{height}" viewBox="0 0 840 {height}" font-family="Segoe UI, Arial, sans-serif" role="img" aria-label="Share of public code repositories containing each programming language">
<rect x="1" y="1" width="838" height="{height - 2}" rx="14" fill="#0d1117" stroke="#30363d"/>
<text x="40" y="36" font-size="19" font-weight="700" fill="#e6edf3">Languages across projects</text>
<text x="40" y="59" font-size="12" fill="#8b949e">Share of {total} public code repositories · all qualifying languages counted</text>
{''.join(parts)}
<line x1="40" y1="{height - 44}" x2="800" y2="{height - 44}" stroke="#30363d"/>
<text x="40" y="{footer_y}" font-size="11" fill="#8b949e">Language must account for ≥5% of a repo's code bytes · percentages can overlap</text>
</svg>'''


def collect():
    repos = list_public_repositories()
    counts = collections.Counter()
    included = 0
    for repo in repos:
        langs = api(f"/repos/{OWNER}/{repo['name']}/languages")
        if not isinstance(langs, dict):
            raise RuntimeError("Unexpected language API response")
        total_bytes = sum(v for v in langs.values() if isinstance(v, (int, float)))
        if total_bytes <= 0:
            continue
        included += 1
        for language, num_bytes in langs.items():
            if num_bytes / total_bytes >= MIN_SHARE:
                counts[language] += 1
    return included, counts, sum(repo.get("stargazers_count", 0) for repo in repos)


def main():
    total, counts, stars = collect()
    if total == 0:
        raise RuntimeError("No qualifying repositories; refusing to overwrite cards")
    user = api(f"/users/{OWNER}")
    OUTPUT.mkdir(exist_ok=True)
    (OUTPUT / "overview.svg").write_text(
        make_overview(total, stars, int(user.get("followers", 0)), len(counts)), encoding="utf-8"
    )
    (OUTPUT / "languages.svg").write_text(make_language_card(counts, total), encoding="utf-8")
    print(f"Generated overview and language cards from {total} repositories: {dict(counts)}")


if __name__ == "__main__":
    main()
