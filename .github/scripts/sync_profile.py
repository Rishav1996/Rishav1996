#!/usr/bin/env python3
"""
Automated profile sync & Executive Studio Dark/Light SVG generator for Rishav1996/Rishav1996.

Uses Python standard library only so GitHub Actions executes with zero external pip installs.
- Fetches live GitHub user/repo stats, Credly badges, Medium RSS articles, and YouTube Atom videos.
- Generates 6 adaptive SVGs in assets/ (hero, KPI scorecard, telemetry) matching Executive Studio tokens.
- Updates designated marker blocks in README.md without duplicating DOI triad papers.
"""

from __future__ import annotations

import html
import json
import os
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
README_PATH = ROOT / "README.md"
ASSETS_DIR = ROOT / "assets"
CONTRIB_3D_DARK = ROOT / "profile-3d-contrib" / "profile-night-view.svg"
CONTRIB_3D_LIGHT = ROOT / "profile-3d-contrib" / "profile-green-animate.svg"

GH_USER = "Rishav1996"
CREDLY_JSON_URL = "https://www.credly.com/users/rishav-saigal.ae0679ae/badges.json"
MEDIUM_RSS_URL = "https://medium.com/feed/@rishavsaigal"
YOUTUBE_ATOM_URL = "https://www.youtube.com/feeds/videos.xml?channel_id=UCh2FmsvvhBsu8L0HsJgh9-A"

# Articles already represented 1:1 in the DOI-Indexed Research Artifacts triad table
TRIAD_PAPER_SLUGS = {
    "e41c3d2d5152",  # The $300B Search Dilemma -> a2ui-ad-component
    "a6505c9053ce",  # Claude Model Routing -> model-router
    "aeaeb904d096",  # Measuring Behavioral Drift in LLMs -> LLMDriftExperiment
}

# Superseded/duplicate Medium posts intentionally excluded from resume & portfolio (v17+)
EXCLUDED_MEDIUM_SLUGS = TRIAD_PAPER_SLUGS | {
    "7935a75f8035",  # From Automation to Autonomy (superseded duplicate of AutoML on Autopilot)
}

# Curated standalone articles (Medium, Towards AI, LinkedIn) so archive stays complete & deduplicated
CURATED_STANDALONE_ARTICLES: list[dict[str, str]] = [
    {
        "title": "The Specialized Frontier: An Inquiry into Gated AI Architectures and the Cooperative Safety Flywheel",
        "venue": "Towards AI",
        "date": "2026-08-14",
        "display_date": "Aug 2026",
        "url": "https://pub.towardsai.net/the-specialized-frontier-an-inquiry-into-gated-ai-architectures-and-the-cooperative-safety-0f10f1546ad6",
        "slug": "0f10f1546ad6",
    },
    {
        "title": "LangGraph Multi-Agent Architecture: Building a Self-Critiquing AI Debate System",
        "venue": "Towards AI",
        "date": "2026-05-02",
        "display_date": "May 2026",
        "url": "https://pub.towardsai.net/langgraph-multi-agent-architecture-building-a-self-critiquing-ai-debate-system-971a7ad881d9",
        "slug": "971a7ad881d9",
    },
    {
        "title": "LLM Drift Explained: Do AI Models Lose Themselves Under Adversarial Pressure?",
        "venue": "Towards AI",
        "date": "2026-05-01",
        "display_date": "May 2026",
        "url": "https://pub.towardsai.net/do-ai-models-lose-themselves-exploring-llm-drift-through-adversarial-debate-a37e0c75012b",
        "slug": "a37e0c75012b",
    },
    {
        "title": "The $1.5 Million Difference: Why Benchmarks are Only 10% of the AI Agent Story",
        "venue": "LinkedIn",
        "date": "2026-03-15",
        "display_date": "Mar 2026",
        "url": "https://www.linkedin.com/pulse/15-million-difference-why-benchmarks-only-10-ai-agent-rishav-saigal-ao4jc/",
        "slug": "ao4jc",
    },
    {
        "title": "AutoML on Autopilot",
        "venue": "Towards AI",
        "date": "2026-03-01",
        "display_date": "Mar 2026",
        "url": "https://pub.towardsai.net/automl-on-autopilot-c8939bca8f8f",
        "slug": "c8939bca8f8f",
    },
    {
        "title": "CognitoEDA",
        "venue": "Medium",
        "date": "2025-08-15",
        "display_date": "Aug 2025",
        "url": "https://medium.com/@rishavsaigal/cognitoeda-bcbd3567e6d2",
        "slug": "bcbd3567e6d2",
    },
    {
        "title": "Beyond Prediction: Generative AI's Probabilistic Future in Time Series",
        "venue": "Medium",
        "date": "2025-06-20",
        "display_date": "Jun 2025",
        "url": "https://medium.com/@rishavsaigal/the-generative-ai-revolution-moving-beyond-what-will-happen-to-what-could-happen-in-time-f820ed5263f1",
        "slug": "f820ed5263f1",
    },
    {
        "title": "Unlocking Time Series with LLMs: A New Era with TimeCAP",
        "venue": "Medium",
        "date": "2025-06-05",
        "display_date": "Jun 2025",
        "url": "https://medium.com/@rishavsaigal/unlocking-time-series-with-llms-99a369f45447",
        "slug": "99a369f45447",
    },
]

THEMES: dict[str, dict[str, str]] = {
    "dark": {
        "bg": "#0c1017",
        "surface": "#131922",
        "surface_alt": "#18202c",
        "border": "#222c3a",
        "accent": "#58a6ff",
        "sage": "#52b788",
        "text": "#e6edf3",
        "muted": "#8b949e",
        "dim": "#6e7681",
        "lang_1": "#58a6ff",
        "lang_2": "#52b788",
        "lang_3": "#79c0ff",
        "lang_4": "#6e7681",
    },
    "light": {
        "bg": "#f8fafc",
        "surface": "#ffffff",
        "surface_alt": "#f1f5f9",
        "border": "#d0d7de",
        "accent": "#0F2942",
        "sage": "#2d6a4f",
        "text": "#1f2328",
        "muted": "#57606a",
        "dim": "#6e7781",
        "lang_1": "#0F2942",
        "lang_2": "#2d6a4f",
        "lang_3": "#2563eb",
        "lang_4": "#94a3b8",
    },
}

SANS_FONT = "'Segoe UI', 'Inter', -apple-system, BlinkMacSystemFont, Helvetica, Arial, sans-serif"
MONO_FONT = "'JetBrains Mono', 'Fira Code', 'SF Mono', Consolas, monospace"


def esc(val: Any) -> str:
    return html.escape(str(val), quote=True)


def http_get(url: str, headers: dict[str, str] | None = None, timeout: int = 15) -> str:
    req_headers = {"User-Agent": "Rishav1996-ProfileSync/2.0"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, headers=req_headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def replace_marker(text: str, name: str, content: str) -> str:
    start = f"<!-- {name}:START -->"
    end = f"<!-- {name}:END -->"
    pattern = re.compile(rf"{re.escape(start)}.*?{re.escape(end)}", re.DOTALL)
    replacement = f"{start}\n{content.strip()}\n{end}"
    if pattern.search(text):
        return pattern.sub(lambda _: replacement, text, count=1)
    return text


def fetch_github_stats() -> dict[str, Any] | None:
    headers: dict[str, str] = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        user_data = json.loads(http_get(f"https://api.github.com/users/{GH_USER}", headers=headers))
        repos_data = json.loads(
            http_get(f"https://api.github.com/users/{GH_USER}/repos?per_page=100&type=owner", headers=headers)
        )
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as exc:
        print(f"[warn] GitHub fetch failed: {exc}")
        return None

    owned = [r for r in repos_data if not r.get("fork")]
    source_set = owned if owned else repos_data
    total_stars = sum(int(r.get("stargazers_count", 0)) for r in repos_data)

    lang_counts: dict[str, int] = {}
    for repo in source_set:
        lang = repo.get("language")
        if lang:
            lang_counts[lang] = lang_counts.get(lang, 0) + 1

    total_lang_repos = sum(lang_counts.values()) or 1
    sorted_langs = sorted(lang_counts.items(), key=lambda kv: (-kv[1], kv[0]))
    top_langs: list[tuple[str, float, int]] = []
    if len(sorted_langs) <= 4:
        for name, cnt in sorted_langs:
            top_langs.append((name, round((cnt / total_lang_repos) * 100, 1), cnt))
    else:
        for name, cnt in sorted_langs[:3]:
            top_langs.append((name, round((cnt / total_lang_repos) * 100, 1), cnt))
        other_cnt = sum(cnt for _, cnt in sorted_langs[3:])
        top_langs.append(("Other", round((other_cnt / total_lang_repos) * 100, 1), other_cnt))

    return {
        "public_repos": int(user_data.get("public_repos", len(repos_data))),
        "followers": int(user_data.get("followers", 0)),
        "total_stars": total_stars,
        "languages": top_langs,
    }


def fetch_credly_badges() -> list[dict[str, str]] | None:
    try:
        payload = json.loads(http_get(CREDLY_JSON_URL))
        raw_items = payload.get("data", [])
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as exc:
        print(f"[warn] Credly fetch failed: {exc}")
        return None

    badges: list[dict[str, str]] = []
    for item in raw_items:
        bid = str(item.get("id", "")).strip()
        tpl = item.get("badge_template", {}) or {}
        name = str(tpl.get("name", "")).strip()
        issued = str(item.get("issued_at_date", "")).strip()
        image_url = str(item.get("image_url") or (tpl.get("image") or {}).get("url") or "").strip()
        issuer_entities = (item.get("issuer") or {}).get("entities") or []
        issuer = "Credly"
        if issuer_entities:
            issuer = str((issuer_entities[0].get("entity") or {}).get("name") or "Credly").strip()

        if bid and name and image_url:
            try:
                disp_date = datetime.strptime(issued, "%Y-%m-%d").strftime("%b %Y")
            except ValueError:
                disp_date = issued
            badges.append(
                {
                    "id": bid,
                    "title": name,
                    "issuer": issuer,
                    "issued_at_date": issued,
                    "display_date": disp_date,
                    "url": f"https://www.credly.com/badges/{bid}/public_url",
                    "image_url": image_url,
                }
            )

    badges.sort(key=lambda b: b["issued_at_date"], reverse=True)
    return badges


def _extract_medium_slug(url: str) -> str:
    clean = url.split("?", 1)[0].rstrip("/")
    m = re.search(r"-([0-9a-f]{10,16})$", clean)
    return m.group(1) if m else clean


def _infer_venue(clean_url: str) -> str:
    if "towardsdeeplearning.com" in clean_url:
        return "Towards Deep Learning"
    if "towardsai.net" in clean_url or "towards-artificial-intelligence" in clean_url:
        return "Towards AI"
    if "linkedin.com" in clean_url:
        return "LinkedIn"
    return "Medium"


def fetch_standalone_articles() -> list[dict[str, str]] | None:
    by_slug: dict[str, dict[str, str]] = {a["slug"]: dict(a) for a in CURATED_STANDALONE_ARTICLES}
    try:
        xml_text = http_get(MEDIUM_RSS_URL)
        root = ET.fromstring(xml_text)
    except (urllib.error.URLError, ET.ParseError, TimeoutError) as exc:
        print(f"[warn] Medium RSS fetch failed: {exc}")
        return None

    for item in root.findall(".//item"):
        raw_link = (item.findtext("link") or "").strip()
        clean_url = raw_link.split("?", 1)[0]
        slug = _extract_medium_slug(clean_url)
        if not clean_url or slug in EXCLUDED_MEDIUM_SLUGS:
            continue

        title = (item.findtext("title") or "").strip()
        pub_raw = (item.findtext("pubDate") or "").strip()
        iso_date = "2025-01-01"
        disp_date = ""
        if pub_raw:
            try:
                dt = datetime.strptime(pub_raw[:25].strip(), "%a, %d %b %Y %H:%M:%S")
                iso_date = dt.strftime("%Y-%m-%d")
                disp_date = dt.strftime("%b %Y")
            except ValueError:
                pass

        # Preserve curated non-truncated title if slug already curated, while updating URL/date cleanly
        if slug in by_slug:
            if disp_date:
                by_slug[slug]["display_date"] = disp_date
                by_slug[slug]["date"] = iso_date
        else:
            by_slug[slug] = {
                "title": title,
                "venue": _infer_venue(clean_url),
                "date": iso_date,
                "display_date": disp_date or iso_date[:7],
                "url": clean_url,
                "slug": slug,
            }

    articles = list(by_slug.values())
    articles.sort(key=lambda a: a["date"], reverse=True)
    return articles


def fetch_youtube_videos(limit: int = 3) -> list[dict[str, str]] | None:
    try:
        xml_text = http_get(YOUTUBE_ATOM_URL)
        root = ET.fromstring(xml_text)
    except (urllib.error.URLError, ET.ParseError, TimeoutError) as exc:
        print(f"[warn] YouTube Atom fetch failed: {exc}")
        return None

    ns = {
        "a": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
    }
    videos: list[dict[str, str]] = []
    for entry in root.findall("a:entry", ns)[:limit]:
        vid = (entry.findtext("yt:videoId", "", ns) or "").strip()
        title = (entry.findtext("a:title", "", ns) or "").strip()
        pub = (entry.findtext("a:published", "", ns) or "")[:10]
        link_el = entry.find("a:link", ns)
        href = link_el.attrib.get("href", f"https://www.youtube.com/watch?v={vid}") if link_el is not None else f"https://www.youtube.com/watch?v={vid}"
        if vid and title:
            videos.append(
                {
                    "id": vid,
                    "title": title,
                    "published": pub,
                    "url": href,
                    "thumb": f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg",
                }
            )
    return videos


def build_hero_svg(mode: str, credly_count: int, pub_count: int) -> str:
    t = THEMES[mode]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 205" width="900" height="205" role="img" aria-label="Rishav Saigal — Executive AI Architect and Ph.D. Candidate">
  <rect width="900" height="205" rx="14" fill="{t['bg']}" stroke="{t['border']}" stroke-width="1.2"/>
  <rect x="14" y="14" width="872" height="177" rx="10" fill="{t['surface']}" stroke="{t['border']}" stroke-width="0.9"/>

  <!-- Architectural corner brackets (no neon glow) -->
  <path d="M 28 42 L 28 28 L 46 28" fill="none" stroke="{t['accent']}" stroke-width="1.8" stroke-linecap="round"/>
  <path d="M 854 28 L 872 28 L 872 42" fill="none" stroke="{t['accent']}" stroke-width="1.8" stroke-linecap="round"/>
  <path d="M 28 163 L 28 177 L 46 177" fill="none" stroke="{t['sage']}" stroke-width="1.8" stroke-linecap="round"/>
  <path d="M 854 177 L 872 177 L 872 163" fill="none" stroke="{t['sage']}" stroke-width="1.8" stroke-linecap="round"/>

  <!-- Status pill -->
  <rect x="330" y="31" width="240" height="22" rx="11" fill="{t['surface_alt']}" stroke="{t['border']}" stroke-width="1"/>
  <circle cx="346" cy="42" r="3.5" fill="{t['sage']}"/>
  <text x="456" y="46" text-anchor="middle" font-family="{MONO_FONT}" font-size="10.2" font-weight="600" letter-spacing="0.9" fill="{t['sage']}">EXECUTIVE AI ARCHITECT  ·  PH.D. CANDIDATE</text>

  <!-- Primary Name -->
  <text x="450" y="101" text-anchor="middle" font-family="{SANS_FONT}" font-size="40" font-weight="800" letter-spacing="2.2" fill="{t['text']}">RISHAV SAIGAL</text>

  <!-- Canonical ATS Role Headline -->
  <text x="450" y="128" text-anchor="middle" font-family="{SANS_FONT}" font-size="13.2" font-weight="600" letter-spacing="0.4" fill="{t['accent']}">Senior Data Scientist  |  Machine Learning Engineer  |  Generative AI / Agentic AI Engineer  |  AI Architect</text>

  <line x1="80" y1="145" x2="820" y2="145" stroke="{t['border']}" stroke-width="1"/>

  <!-- Bottom Verified Telemetry Line -->
  <text x="450" y="169" text-anchor="middle" font-family="{MONO_FONT}" font-size="11.2" fill="{t['muted']}">Manager @ Cognizant (8+ Yrs)  •  Ph.D. Scholar @ IIT Patna (2026–2029)  •  {esc(credly_count)} Credly Badges  •  {esc(pub_count)} Publications  •  3 Zenodo DOIs</text>
</svg>
"""


def build_kpi_svg(mode: str) -> str:
    t = THEMES[mode]
    cards = [
        ("5–14d → &lt;6h", "GenAI Video Pipeline", "Google ADK · FastMCP", t["accent"]),
        ("$2.3M Saved", "Healthcare Causal ML", "90%+ Model Accuracy", t["sage"]),
        ("80% Resolved", "Policy QA + RBAC Flow", "Semantic Retrieval", t["accent"]),
        ("70% Faster", "BRD → Gherkin / TMMi", "100% Req. Coverage", t["sage"]),
        ("3d → 2 hrs", "Distributed MLOps", "Azure Databricks · -60% Ops", t["accent"]),
    ]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 112" width="900" height="112" role="img" aria-label="Production AI and ML Operational Impact Scorecard">',
        f'  <rect width="900" height="112" rx="12" fill="{t["bg"]}" stroke="{t["border"]}" stroke-width="1.1"/>',
    ]
    card_w = 166
    gap = 10
    start_x = 15
    for idx, (metric, title, sub, accent) in enumerate(cards):
        x = start_x + idx * (card_w + gap)
        parts.append(f'  <rect x="{x}" y="12" width="{card_w}" height="88" rx="8" fill="{t["surface"]}" stroke="{t["border"]}" stroke-width="1"/>')
        parts.append(f'  <rect x="{x}" y="12" width="{card_w}" height="3" rx="1.5" fill="{accent}"/>')
        parts.append(f'  <text x="{x + 12}" y="41" font-family="{MONO_FONT}" font-size="16" font-weight="700" fill="{accent}">{metric}</text>')
        parts.append(f'  <text x="{x + 12}" y="62" font-family="{SANS_FONT}" font-size="11.5" font-weight="700" fill="{t["text"]}">{esc(title)}</text>')
        parts.append(f'  <text x="{x + 12}" y="81" font-family="{SANS_FONT}" font-size="10.2" fill="{t["muted"]}">{esc(sub)}</text>')
    parts.append("</svg>\n")
    return "\n".join(parts)


def build_telemetry_svg(mode: str, gh: dict[str, Any], credly_count: int) -> str:
    t = THEMES[mode]
    lang_colors = [t["lang_1"], t["lang_2"], t["lang_3"], t["lang_4"]]
    langs = gh.get("languages") or [("Python", 100.0, 1)]

    # Build stacked horizontal bar segments (total width = 390)
    bar_x = 466
    bar_y = 68
    bar_w = 390
    bar_h = 12
    curr_x = float(bar_x)
    bar_rects: list[str] = []
    legend_items: list[str] = []

    for idx, (lname, pct, cnt) in enumerate(langs[:4]):
        color = lang_colors[idx % len(lang_colors)]
        seg_w = max(4.0, (pct / 100.0) * bar_w)
        if idx == len(langs[:4]) - 1:
            seg_w = max(4.0, (bar_x + bar_w) - curr_x)
        bar_rects.append(
            f'  <rect x="{curr_x:.1f}" y="{bar_y}" width="{seg_w:.1f}" height="{bar_h}" fill="{color}" rx="2"/>'
        )
        curr_x += seg_w

        col = idx % 2
        row = idx // 2
        lx = bar_x + col * 195
        ly = 104 + row * 24
        legend_items.append(
            f'  <circle cx="{lx + 5}" cy="{ly - 4}" r="4.5" fill="{color}"/>'
            f'<text x="{lx + 16}" y="{ly}" font-family="{SANS_FONT}" font-size="11.5" font-weight="600" fill="{t["text"]}">{esc(lname)}</text>'
            f'<text x="{lx + 180}" y="{ly}" text-anchor="end" font-family="{MONO_FONT}" font-size="11" fill="{t["muted"]}">{pct:.1f}% ({cnt})</text>'
        )

    metrics = [
        ("Public Repos", str(gh["public_repos"]), t["accent"]),
        ("Total Stars", str(gh["total_stars"]), t["sage"]),
        ("Followers", str(gh["followers"]), t["accent"]),
        ("Curated OSS", "8", t["sage"]),
        ("Zenodo DOIs", "3", t["accent"]),
        ("Credly Badges", str(credly_count), t["sage"]),
    ]

    stat_cells: list[str] = []
    for idx, (label, val, col) in enumerate(metrics):
        c = idx % 3
        r = idx // 3
        sx = 34 + c * 130
        sy = 62 + r * 44
        stat_cells.append(
            f'  <text x="{sx}" y="{sy}" font-family="{MONO_FONT}" font-size="18" font-weight="700" fill="{col}">{esc(val)}</text>'
            f'<text x="{sx}" y="{sy + 15}" font-family="{SANS_FONT}" font-size="10.5" fill="{t["muted"]}">{esc(label)}</text>'
        )

    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 156" width="900" height="156" role="img" aria-label="GitHub and Research Telemetry">',
            f'  <rect width="900" height="156" rx="12" fill="{t["bg"]}" stroke="{t["border"]}" stroke-width="1.1"/>',
            f'  <rect x="14" y="14" width="414" height="128" rx="9" fill="{t["surface"]}" stroke="{t["border"]}" stroke-width="1"/>',
            f'  <rect x="444" y="14" width="442" height="128" rx="9" fill="{t["surface"]}" stroke="{t["border"]}" stroke-width="1"/>',
            f'  <text x="34" y="37" font-family="{MONO_FONT}" font-size="11" font-weight="700" letter-spacing="0.8" fill="{t["muted"]}">LIVE GITHUB &amp; RESEARCH TELEMETRY</text>',
            *stat_cells,
            f'  <text x="466" y="37" font-family="{MONO_FONT}" font-size="11" font-weight="700" letter-spacing="0.8" fill="{t["muted"]}">OWNED REPOSITORY LANGUAGE DISTRIBUTION</text>',
            f'  <rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="3" fill="{t["surface_alt"]}"/>',
            *bar_rects,
            *legend_items,
            "</svg>\n",
        ]
    )


def render_credly_block(badges: list[dict[str, str]]) -> str:
    links = []
    for b in badges:
        label = esc(f"{b['title']} — {b['issuer']} ({b['display_date']})")
        links.append(
            f'  <a href="{esc(b["url"])}" title="{label}">'
            f'<img src="{esc(b["image_url"])}" width="72" height="72" alt="{label}" />'
            f"</a>"
        )
    row = "&nbsp;\n".join(links)
    return (
        "<div align=\"center\">\n\n"
        f"{row}\n\n"
        f"<sub><b>{len(badges)} Live Credly Digital Badges</b> · Auto-synced from Credly · Click any badge to verify</sub>\n\n"
        "</div>"
    )


def render_writing_blocks(articles: list[dict[str, str]]) -> tuple[str, str]:
    latest = articles[:4]
    archive = articles[4:]
    latest_lines = [
        f"- **[{a['title']}]({a['url']})** — *{a['venue']}* · `{a['display_date']}`"
        for a in latest
    ]
    archive_lines = [
        f"{idx + 1}. **[{a['title']}]({a['url']})** — *{a['venue']}* · `{a['display_date']}`"
        for idx, a in enumerate(archive)
    ]
    return "\n".join(latest_lines), "\n".join(archive_lines)


def render_youtube_block(videos: list[dict[str, str]]) -> str:
    if not videos:
        return "_Videos available at [Algorhythm Chronicles on YouTube](https://www.youtube.com/@algorythmchronicles)._"
    cells = []
    for v in videos:
        t_esc = esc(v["title"])
        u_esc = esc(v["url"])
        th_esc = esc(v["thumb"])
        d_esc = esc(v["published"])
        cells.append(
            f'<td width="33%" align="center" valign="top">\n'
            f'  <a href="{u_esc}">\n'
            f'    <img src="{th_esc}" width="260" alt="{t_esc}" /><br/>\n'
            f'    <sub><b>{t_esc}</b><br/>{d_esc}</sub>\n'
            f"  </a>\n"
            f"</td>"
        )
    return "<table><tr>\n" + "\n".join(cells) + "\n</tr></table>"


def render_contrib_3d_block() -> str:
    if CONTRIB_3D_DARK.exists() and CONTRIB_3D_LIGHT.exists():
        return (
            "<div align=\"center\">\n\n"
            "<picture>\n"
            '  <source media="(prefers-color-scheme: dark)" srcset="./profile-3d-contrib/profile-night-view.svg" />\n'
            '  <source media="(prefers-color-scheme: light)" srcset="./profile-3d-contrib/profile-green-animate.svg" />\n'
            '  <img width="100%" src="./profile-3d-contrib/profile-night-view.svg" alt="3D GitHub Contribution Skyline" />\n'
            "</picture>\n\n"
            "</div>"
        )
    return "<!-- 3D contribution skyline renders automatically once profile-3d-contrib workflow generates SVGs -->"


def main() -> int:
    if not README_PATH.exists():
        raise FileNotFoundError(f"Missing {README_PATH}")

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    readme_text = README_PATH.read_text(encoding="utf-8")

    gh_stats = fetch_github_stats()
    credly_badges = fetch_credly_badges()
    articles = fetch_standalone_articles()
    videos = fetch_youtube_videos()

    credly_count = len(credly_badges) if credly_badges is not None else 9
    pub_count = 12  # 3 DOI research works (+ companion paper) + standalone articles = 12 entries in v25

    for mode in ("dark", "light"):
        (ASSETS_DIR / f"hero-{mode}.svg").write_text(
            build_hero_svg(mode, credly_count=credly_count, pub_count=pub_count), encoding="utf-8"
        )
        (ASSETS_DIR / f"kpi-{mode}.svg").write_text(build_kpi_svg(mode), encoding="utf-8")
        if gh_stats is not None:
            (ASSETS_DIR / f"telemetry-{mode}.svg").write_text(
                build_telemetry_svg(mode, gh_stats, credly_count=credly_count), encoding="utf-8"
            )

    if credly_badges is not None and credly_badges:
        readme_text = replace_marker(readme_text, "CREDLY-BADGES", render_credly_block(credly_badges))

    if articles is not None and articles:
        feed_md, archive_md = render_writing_blocks(articles)
        readme_text = replace_marker(readme_text, "WRITING-FEED", feed_md)
        readme_text = replace_marker(readme_text, "WRITING-ARCHIVE", archive_md)

    if videos is not None and videos:
        readme_text = replace_marker(readme_text, "YOUTUBE-FEED", render_youtube_block(videos))

    readme_text = replace_marker(readme_text, "CONTRIB-3D", render_contrib_3d_block())

    README_PATH.write_text(readme_text, encoding="utf-8")
    print(
        f"[ok] Synced profile assets & README "
        f"(gh={bool(gh_stats)}, credly={credly_count}, articles={len(articles or [])}, videos={len(videos or [])})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
