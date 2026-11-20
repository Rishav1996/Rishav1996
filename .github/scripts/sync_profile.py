#!/usr/bin/env python3
"""
Automated animated SVG engine & live profile sync for Rishav1996/Rishav1996.

Uses Python standard library only so GitHub Actions executes with zero external pip installs.
- Fetches live GitHub user/repo stats, exact daily contributions (tooltip + calendar),
  Credly badges, Medium RSS articles (deduplicated against DOI triads), and YouTube Atom videos.
- Generates 6 adaptive Dark/Light Executive Studio SVGs in assets/ (SMIL <animate*>):
    1. hero-dark.svg / hero-light.svg     (Flowing dual waves, twinkling stars, 3Hz horology wheel)
    2. pulse-dark.svg / pulse-light.svg   (Genuine 52-week contribution area chart + animated language bar)
    3. footer-dark.svg / footer-light.svg (Counter-flowing dual waves + rising signal dots)
- Updates marker blocks in README.md with zero resume highlights and zero duplication.
"""

from __future__ import annotations

import html
import json
import math
import os
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
README_PATH = ROOT / "README.md"
ASSETS_DIR = ROOT / "assets"

SNAKE_DARK = ASSETS_DIR / "github-snake-dark.svg"
SNAKE_LIGHT = ASSETS_DIR / "github-snake-light.svg"
CONTRIB_3D_DARK = ROOT / "profile-3d-contrib" / "profile-night-view.svg"
CONTRIB_3D_LIGHT = ROOT / "profile-3d-contrib" / "profile-green-animate.svg"

GH_USER = "Rishav1996"
CONTRIB_HTML_URL = f"https://github.com/users/{GH_USER}/contributions"
CREDLY_JSON_URL = "https://www.credly.com/users/rishav-saigal.ae0679ae/badges.json"
MEDIUM_RSS_URL = "https://medium.com/feed/@rishavsaigal"
YOUTUBE_ATOM_URL = "https://www.youtube.com/feeds/videos.xml?channel_id=UCh2FmsvvhBsu8L0HsJgh9-A"

# Papers already paired 1:1 with code + Zenodo DOI in Research Labs
TRIAD_PAPER_SLUGS = {
    "e41c3d2d5152",  # The $300B Search Dilemma -> a2ui-ad-component
    "a6505c9053ce",  # Claude Model Routing -> model-router
    "aeaeb904d096",  # Measuring Behavioral Drift in LLMs -> LLMDriftExperiment
}

# Superseded/duplicate drafts intentionally excluded
EXCLUDED_MEDIUM_SLUGS = TRIAD_PAPER_SLUGS | {
    "7935a75f8035",  # Superseded duplicate of AutoML on Autopilot
}

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

THEMES: dict[str, dict[str, Any]] = {
    "dark": {
        "bg": "#0c1017",
        "surface": "#131922",
        "surface_alt": "#18202c",
        "border": "#222c3a",
        "accent": "#58a6ff",
        "sage": "#52b788",
        "brass": "#c5a059",
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
        "brass": "#b48a3e",
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
    req_headers = {"User-Agent": "Rishav1996-ProfileSync/3.1"}
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
        print(f"[warn] GitHub API fetch failed: {exc}")
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


def fetch_contributions() -> dict[str, Any] | None:
    try:
        raw_html = http_get(CONTRIB_HTML_URL)
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"[warn] GitHub contributions fetch failed: {exc}")
        return None

    m_total = re.search(r"([\d,]+)\s+contributions\s+in\s+the\s+last\s+year", raw_html)
    total_str = m_total.group(1) if m_total else "0"

    # Map component ID -> (date_str, level)
    id_to_meta: dict[str, tuple[str, int]] = {}
    day_fallback: dict[str, int] = {}
    level_weights = {0: 0, 1: 1, 2: 3, 3: 6, 4: 10}

    for tag in re.findall(r"<td\b[^>]*>", raw_html):
        d_m = re.search(r'data-date="(\d{4}-\d{2}-\d{2})"', tag)
        l_m = re.search(r'data-level="(\d)"', tag)
        id_m = re.search(r'id="(contribution-day-component-[^"]+)"', tag)
        if d_m and l_m:
            dt_s = d_m.group(1)
            lvl = int(l_m.group(1))
            day_fallback[dt_s] = level_weights.get(lvl, lvl)
            if id_m:
                id_to_meta[id_m.group(1)] = (dt_s, lvl)

    if not day_fallback:
        return None

    # Parse exact daily contribution counts from <tool-tip> elements
    day_counts: dict[str, int] = {}
    for comp_id, body in re.findall(
        r'<tool-tip\b[^>]*for="(contribution-day-component-[^"]+)"[^>]*>([^<]+)</tool-tip>',
        raw_html,
    ):
        if comp_id not in id_to_meta:
            continue
        dt_s, _ = id_to_meta[comp_id]
        body_clean = body.strip()
        if body_clean.startswith("No "):
            day_counts[dt_s] = 0
        else:
            cnt_m = re.match(r"([\d,]+)\s+contribution", body_clean)
            if cnt_m:
                day_counts[dt_s] = int(cnt_m.group(1).replace(",", ""))

    # Fall back to weighted levels only if tooltips failed to parse
    effective_days = day_counts if len(day_counts) >= len(day_fallback) // 2 else day_fallback
    days_sorted = sorted(effective_days.items(), key=lambda kv: kv[0])

    first_dt = datetime.strptime(days_sorted[0][0], "%Y-%m-%d").date()
    sun_offset = (first_dt.weekday() + 1) % 7
    grid_start = first_dt - timedelta(days=sun_offset)

    week_buckets: dict[int, int] = {}
    for dt_s, cnt in days_sorted:
        dt = datetime.strptime(dt_s, "%Y-%m-%d").date()
        week_idx = (dt - grid_start).days // 7
        week_buckets[week_idx] = week_buckets.get(week_idx, 0) + cnt

    max_week = max(week_buckets)
    weeks: list[dict[str, Any]] = []
    for w in range(max_week + 1):
        w_start = grid_start + timedelta(days=w * 7)
        weeks.append({"week": w, "start_date": w_start, "count": week_buckets.get(w, 0)})

    # Recompute exact total from parsed days if available
    if day_counts and total_str == "0":
        total_str = f"{sum(day_counts.values()):,}"

    return {
        "total_str": total_str,
        "weeks": weeks,
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
        href = (
            link_el.attrib.get("href", f"https://www.youtube.com/watch?v={vid}")
            if link_el is not None
            else f"https://www.youtube.com/watch?v={vid}"
        )
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


def _sine_wave_path(
    width: int, baseline_y: float, amplitude: float, cycles: int, phase: float, bottom_y: float
) -> str:
    step = 18
    pts: list[str] = []
    for x in range(0, width + step, step):
        y = baseline_y + amplitude * math.sin((2.0 * math.pi * cycles * x / 900.0) + phase)
        cmd = "M" if x == 0 else "L"
        pts.append(f"{cmd} {x} {y:.1f}")
    pts.append(f"L {width} {bottom_y:.1f} L 0 {bottom_y:.1f} Z")
    return " ".join(pts)


def build_hero_svg(mode: str) -> str:
    """Style A: Sleek dual-wave hero with subtle twinkling stars & 3Hz brass balance wheel."""
    t = THEMES[mode]
    wave1 = _sine_wave_path(1800, 194, 12, 2, 0.0, 236)
    wave2 = _sine_wave_path(1800, 204, 9, 3, 1.4, 236)

    # Sparse, gentle twinkling accents placed strictly in negative space outside central typography
    stars = [
        (56, 48, 1.6, 3.2, "0.1s", t["accent"]),
        (108, 92, 1.4, 4.4, "0.9s", t["sage"]),
        (68, 146, 1.8, 3.8, "1.6s", t["accent"]),
        (158, 56, 1.3, 5.0, "0.4s", t["sage"]),
        (178, 138, 1.5, 4.1, "1.2s", t["accent"]),
        (736, 54, 1.4, 4.6, "0.7s", t["sage"]),
        (764, 144, 1.7, 3.5, "1.5s", t["accent"]),
        (838, 118, 1.5, 4.3, "0.3s", t["sage"]),
        (812, 162, 1.3, 5.2, "1.9s", t["accent"]),
        (140, 174, 1.4, 3.9, "2.2s", t["brass"]),
    ]
    star_els = [
        f'  <circle cx="{sx}" cy="{sy}" r="{sr}" fill="{scol}">'
        f'<animate attributeName="opacity" values="0.2;0.85;0.2" dur="{sdur}s" begin="{sbeg}" repeatCount="indefinite"/>'
        f"</circle>"
        for sx, sy, sr, sdur, sbeg, scol in stars
    ]

    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 236" width="900" height="236" role="img" aria-label="Rishav Saigal — AI Systems Lab and Open Research">',
            "  <defs>",
            '    <clipPath id="heroInner"><rect x="14" y="14" width="872" height="208" rx="11"/></clipPath>',
            "  </defs>",
            f'  <rect width="900" height="236" rx="14" fill="{t["bg"]}" stroke="{t["border"]}" stroke-width="1.2"/>',
            f'  <rect x="14" y="14" width="872" height="208" rx="11" fill="{t["surface"]}" stroke="{t["border"]}" stroke-width="0.9"/>',
            "",
            "  <!-- Dual-layer flowing aurora waves -->",
            '  <g clip-path="url(#heroInner)">',
            "    <g>",
            f'      <path d="{wave1}" fill="{t["accent"]}" fill-opacity="0.11"/>',
            '      <animateTransform attributeName="transform" type="translate" from="0 0" to="-900 0" dur="14s" repeatCount="indefinite"/>',
            "    </g>",
            "    <g>",
            f'      <path d="{wave2}" fill="{t["sage"]}" fill-opacity="0.13"/>',
            '      <animateTransform attributeName="transform" type="translate" from="-900 0" to="0 0" dur="20s" repeatCount="indefinite"/>',
            "    </g>",
            "  </g>",
            "",
            "  <!-- Subtle negative-space twinkling accents -->",
            *star_els,
            "",
            "  <!-- Subtle Top-Right Horological 3Hz Balance Wheel Emblem -->",
            '  <g transform="translate(842, 46)">',
            f'    <circle cx="0" cy="0" r="13.5" fill="none" stroke="{t["brass"]}" stroke-width="1.1" stroke-opacity="0.5" stroke-dasharray="2 3"/>',
            "    <g>",
            f'      <circle cx="0" cy="0" r="9" fill="none" stroke="{t["brass"]}" stroke-width="1.4"/>',
            f'      <line x1="-9" y1="0" x2="9" y2="0" stroke="{t["brass"]}" stroke-width="1"/>',
            f'      <line x1="0" y1="-9" x2="0" y2="9" stroke="{t["brass"]}" stroke-width="1"/>',
            f'      <circle cx="0" cy="0" r="2.2" fill="{t["brass"]}"/>',
            '      <animateTransform attributeName="transform" type="rotate" values="-28 0 0;28 0 0;-28 0 0" dur="1.6s" repeatCount="indefinite"/>',
            "    </g>",
            "  </g>",
            "",
            "  <!-- Status Pill -->",
            f'  <rect x="275" y="34" width="350" height="22" rx="11" fill="{t["surface_alt"]}" stroke="{t["border"]}" stroke-width="1"/>',
            f'  <circle cx="294" cy="45" r="3.6" fill="{t["sage"]}">',
            '    <animate attributeName="opacity" values="1;0.35;1" dur="2.2s" repeatCount="indefinite"/>',
            "  </circle>",
            f'  <text x="456" y="49" text-anchor="middle" font-family="{MONO_FONT}" font-size="10.2" font-weight="600" letter-spacing="0.9" fill="{t["sage"]}">AI SYSTEMS LAB  ·  OPEN RESEARCH  ·  BUILD IN PUBLIC</text>',
            "",
            "  <!-- Primary Name -->",
            f'  <text x="450" y="108" text-anchor="middle" font-family="{SANS_FONT}" font-size="42" font-weight="800" letter-spacing="2.4" fill="{t["text"]}">RISHAV SAIGAL</text>',
            "",
            "  <!-- Animated Accent Rule -->",
            f'  <line x1="290" y1="124" x2="610" y2="124" stroke="{t["border"]}" stroke-width="1.2"/>',
            f'  <line x1="360" y1="124" x2="540" y2="124" stroke="{t["accent"]}" stroke-width="2" stroke-linecap="round">',
            '    <animate attributeName="x1" values="360;310;360" dur="5s" repeatCount="indefinite"/>',
            '    <animate attributeName="x2" values="540;590;540" dur="5s" repeatCount="indefinite"/>',
            "  </line>",
            "",
            "  <!-- Builder Identity (Zero Resume Highlights) -->",
            f'  <text x="450" y="153" text-anchor="middle" font-family="{SANS_FONT}" font-size="13.5" font-weight="600" letter-spacing="0.4" fill="{t["accent"]}">Multi-Agent Orchestration  ·  LLM Behavioral Drift  ·  Open-Source AI Tooling  ·  Horology</text>',
            "",
            "  <!-- Sub-caption -->",
            f'  <text x="450" y="179" text-anchor="middle" font-family="{MONO_FONT}" font-size="10.8" fill="{t["muted"]}">FastMCP · Google ADK · LangGraph · A2UI · Zenodo Open Benchmarks · Algorhythm Chronicles</text>',
            "</svg>\n",
        ]
    )


def build_stack_svg(mode: str) -> str:
    """Option 1: 900x264 Dark/Light 2x2 Bento Stack & Tooling card matching Executive Studio."""
    t = THEMES[mode]
    quadrants = [
        (
            14,
            14,
            "AGENTIC & LLM SYSTEMS",
            t["accent"],
            "nodes",
            [
                ["Google ADK", "LangGraph", "CrewAI", "LangChain"],
                ["FastMCP", "A2UI", "Ollama", "Hugging Face"],
            ],
        ),
        (
            458,
            14,
            "MODELING, FORECASTING & XAI",
            t["sage"],
            "bars",
            [
                ["Scikit-Learn", "TensorFlow", "Keras", "PyCaret"],
                ["SHAP (XAI)", "Causal Inference", "HLM", "SARIMAX · Prophet"],
            ],
        ),
        (
            14,
            139,
            "CLOUD & MLOPS",
            t["sage"],
            "layers",
            [
                ["GCP Vertex AI", "Cloud Run", "Agent Engine", "Docker"],
                ["AWS SageMaker", "Azure Databricks", "MLflow", "DataRobot"],
            ],
        ),
        (
            458,
            139,
            "LANGUAGES, APIS & DATA",
            t["accent"],
            "code",
            [
                ["Python", "JavaScript", "FastAPI", "Streamlit"],
                ["PySpark", "PostgreSQL", "MySQL", "Redis"],
            ],
        ),
    ]

    card_w, card_h = 428, 111
    clips: list[str] = []
    cards_svg: list[str] = []

    for idx, (cx, cy, title, accent, icon_kind, rows) in enumerate(quadrants):
        clips.append(f'    <clipPath id="qClip{idx}"><rect x="{cx}" y="{cy}" width="{card_w}" height="{card_h}" rx="9"/></clipPath>')

        if icon_kind == "nodes":
            ix, iy = cx + 18, cy + 16
            icon_svg = (
                f'  <line x1="{ix}" y1="{iy+9}" x2="{ix+6}" y2="{iy+1}" stroke="{accent}" stroke-width="1.3"/>'
                f'<line x1="{ix+6}" y1="{iy+1}" x2="{ix+12}" y2="{iy+9}" stroke="{accent}" stroke-width="1.3"/>'
                f'<circle cx="{ix}" cy="{iy+9}" r="2.2" fill="{accent}"/>'
                f'<circle cx="{ix+6}" cy="{iy+1}" r="2.2" fill="{accent}"/>'
                f'<circle cx="{ix+12}" cy="{iy+9}" r="2.2" fill="{accent}"/>'
            )
        elif icon_kind == "bars":
            ix, iy = cx + 17, cy + 16
            icon_svg = (
                f'  <rect x="{ix}" y="{iy+6}" width="3" height="5" rx="1" fill="{accent}"/>'
                f'<rect x="{ix+5}" y="{iy+2}" width="3" height="9" rx="1" fill="{accent}"/>'
                f'<rect x="{ix+10}" y="{iy}" width="3" height="11" rx="1" fill="{accent}"/>'
            )
        elif icon_kind == "layers":
            ix, iy = cx + 17, cy + 16
            icon_svg = (
                f'  <polygon points="{ix+6},{iy} {ix+13},{iy+3.5} {ix+6},{iy+7} {ix-1},{iy+3.5}" fill="none" stroke="{accent}" stroke-width="1.2"/>'
                f'<polyline points="{ix-1},{iy+7.2} {ix+6},{iy+10.7} {ix+13},{iy+7.2}" fill="none" stroke="{accent}" stroke-width="1.2"/>'
            )
        else:
            ix, iy = cx + 17, cy + 16
            icon_svg = (
                f'  <polyline points="{ix+4},{iy+1} {ix},{iy+5.5} {ix+4},{iy+10}" fill="none" stroke="{accent}" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>'
                f'<polyline points="{ix+9},{iy+1} {ix+13},{iy+5.5} {ix+9},{iy+10}" fill="none" stroke="{accent}" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>'
            )

        cards_svg.extend(
            [
                f'  <rect x="{cx}" y="{cy}" width="{card_w}" height="{card_h}" rx="9" fill="{t["surface"]}" stroke="{t["border"]}" stroke-width="1"/>',
                f'  <g clip-path="url(#qClip{idx})">',
                f'    <rect x="{cx}" y="{cy}" width="{card_w}" height="3" fill="{accent}">',
                f'      <animate attributeName="width" from="0" to="{card_w}" dur="1.1s" begin="{idx * 0.12:.2f}s" fill="freeze"/>',
                "    </rect>",
                "  </g>",
                icon_svg,
                f'  <text x="{cx + 38}" y="{cy + 25}" font-family="{MONO_FONT}" font-size="10.6" font-weight="700" letter-spacing="0.8" fill="{t["text"]}">{esc(title)}</text>',
                f'  <line x1="{cx + 14}" y1="{cy + 36}" x2="{cx + card_w - 14}" y2="{cy + 36}" stroke="{t["border"]}" stroke-width="0.9"/>',
            ]
        )

        for r_idx, row in enumerate(rows):
            py = cy + 46 + r_idx * 30
            px = cx + 16
            for label in row:
                pw = max(48, round(len(label) * 6.0 + 18))
                cards_svg.append(
                    f'  <rect x="{px}" y="{py}" width="{pw}" height="24" rx="6" fill="{t["surface_alt"]}" stroke="{t["border"]}" stroke-width="0.9"/>'
                    f'<text x="{px + pw / 2:.1f}" y="{py + 15.6:.1f}" text-anchor="middle" font-family="{SANS_FONT}" font-size="10.4" font-weight="600" fill="{t["text"]}">{esc(label)}</text>'
                )
                px += pw + 7

    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 264" width="900" height="264" role="img" aria-label="Stack and Tooling Bento Matrix">',
            "  <defs>",
            *clips,
            "  </defs>",
            f'  <rect width="900" height="264" rx="12" fill="{t["bg"]}" stroke="{t["border"]}" stroke-width="1.1"/>',
            *cards_svg,
            "</svg>\n",
        ]
    )


def build_pulse_svg(
    mode: str,
    gh: dict[str, Any],
    contribs: dict[str, Any] | None,
    credly_count: int,
) -> str:
    """Option 1: Genuine 52-week GitHub Contribution Area Chart + Animated Language Bar."""
    t = THEMES[mode]
    lang_colors = [t["lang_1"], t["lang_2"], t["lang_3"], t["lang_4"]]
    langs = gh.get("languages") or [("Python", 100.0, 1)]

    total_contribs = contribs["total_str"] if contribs else "345"
    summary = (
        f"{total_contribs} Annual Contributions  ·  "
        f"{gh['public_repos']} Repos  ·  "
        f"{gh['total_stars']} Stars  ·  "
        f"3 Zenodo DOIs  ·  "
        f"{credly_count} Credly Badges"
    )

    chart_x0, chart_x1 = 48.0, 868.0
    chart_y_top, chart_y_bot = 58.0, 146.0
    chart_h = chart_y_bot - chart_y_top

    weeks = (contribs or {}).get("weeks") or []
    chart_svg: list[str] = []

    if len(weeks) >= 2:
        counts = [int(w["count"]) for w in weeks]
        raw_max = max(counts) if counts else 10
        # Nice rounded ceiling >= 4
        y_max = max(4, int(math.ceil(raw_max / 5.0) * 5))
        y_mid = y_max // 2

        # Horizontal hairline grid & Y-axis tick labels
        for val, y_pos in [(y_max, chart_y_top), (y_mid, chart_y_top + chart_h / 2.0), (0, chart_y_bot)]:
            dash = ' stroke-dasharray="3 4"' if val > 0 else ""
            chart_svg.append(
                f'  <line x1="{chart_x0}" y1="{y_pos:.1f}" x2="{chart_x1}" y2="{y_pos:.1f}" stroke="{t["border"]}" stroke-width="0.9"{dash}/>'
            )
            chart_svg.append(
                f'  <text x="{chart_x0 - 8}" y="{y_pos + 3.5:.1f}" text-anchor="end" font-family="{MONO_FONT}" font-size="9.5" fill="{t["dim"]}">{val}</text>'
            )

        # Compute exact data points (x, y)
        n = len(weeks)
        pts: list[tuple[float, float, int, Any]] = []
        for idx, w in enumerate(weeks):
            x = chart_x0 + (idx / (n - 1)) * (chart_x1 - chart_x0)
            y = chart_y_bot - (int(w["count"]) / float(y_max)) * chart_h
            pts.append((x, y, int(w["count"]), w["start_date"]))

        # Smooth horizontal-tangent cubic Bezier curve (monotone-safe: strictly bounded in [y_top, y_bot])
        line_cmds = [f"M {pts[0][0]:.1f} {pts[0][1]:.1f}"]
        for i in range(1, len(pts)):
            x0, y0 = pts[i - 1][0], pts[i - 1][1]
            x1, y1 = pts[i][0], pts[i][1]
            xm = (x0 + x1) / 2.0
            line_cmds.append(f"C {xm:.1f} {y0:.1f}, {xm:.1f} {y1:.1f}, {x1:.1f} {y1:.1f}")
        line_path = " ".join(line_cmds)
        area_path = f"{line_path} L {pts[-1][0]:.1f} {chart_y_bot:.1f} L {pts[0][0]:.1f} {chart_y_bot:.1f} Z"

        # Month tick labels along X-axis (spaced to prevent label overlap)
        last_month = None
        last_label_x = -999.0
        for x, _, _, dt in pts:
            m_key = (dt.year, dt.month)
            if m_key != last_month and (x - last_label_x) >= 48 and x <= (chart_x1 - 14):
                chart_svg.append(
                    f'  <line x1="{x:.1f}" y1="{chart_y_top}" x2="{x:.1f}" y2="{chart_y_bot}" stroke="{t["border"]}" stroke-width="0.6" stroke-opacity="0.5"/>'
                )
                chart_svg.append(
                    f'  <text x="{x:.1f}" y="162" text-anchor="middle" font-family="{MONO_FONT}" font-size="9.5" fill="{t["muted"]}">{dt.strftime("%b")}</text>'
                )
                last_month = m_key
                last_label_x = x

        chart_svg.append(f'  <path d="{area_path}" fill="url(#areaGrad)"/>')
        chart_svg.append(
            f'  <path d="{line_path}" fill="none" stroke="{t["accent"]}" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="1800" stroke-dashoffset="1800">'
            f'<animate attributeName="stroke-dashoffset" from="1800" to="0" dur="1.8s" fill="freeze"/>'
            f"</path>"
        )

        # Highlight top 3 non-zero peak weeks with clean markers and subtle peak count on max week
        non_zero = [(idx, c) for idx, (_, _, c, _) in enumerate(pts) if c > 0]
        top_peaks = sorted(non_zero, key=lambda item: (-item[1], item[0]))
        chosen: list[int] = []
        for idx, _ in top_peaks:
            if all(abs(idx - c_idx) >= 4 for c_idx in chosen):
                chosen.append(idx)
            if len(chosen) == 3:
                break
        max_idx = chosen[0] if chosen else None
        for idx in chosen:
            px, py, pcnt, _ = pts[idx]
            chart_svg.append(
                f'  <circle cx="{px:.1f}" cy="{py:.1f}" r="3.4" fill="{t["sage"]}" stroke="{t["surface"]}" stroke-width="1.4"/>'
            )
            if idx == max_idx:
                lbl_y = max(49.0, py - 7.0)
                chart_svg.append(
                    f'  <text x="{px:.1f}" y="{lbl_y:.1f}" text-anchor="middle" font-family="{MONO_FONT}" font-size="9.2" font-weight="700" fill="{t["sage"]}">{pcnt}/wk</text>'
                )
    else:
        chart_svg.append(
            f'  <text x="450" y="106" text-anchor="middle" font-family="{MONO_FONT}" font-size="12" fill="{t["muted"]}">52-Week Activity Synced via GitHub Actions</text>'
        )

    # Animated Language Bar
    bar_x = 28
    bar_y = 180
    bar_w = 844
    bar_h = 10
    curr_x = float(bar_x)
    bar_rects: list[str] = []
    legend_els: list[str] = []
    for idx, (lname, pct, cnt) in enumerate(langs[:4]):
        color = lang_colors[idx % len(lang_colors)]
        seg_w = max(8.0, (pct / 100.0) * bar_w)
        if idx == len(langs[:4]) - 1:
            seg_w = max(8.0, (bar_x + bar_w) - curr_x)
        bar_rects.append(
            f'  <rect x="{curr_x:.1f}" y="{bar_y}" width="{seg_w:.1f}" height="{bar_h}" fill="{color}" rx="2">'
            f'<animate attributeName="width" from="0" to="{seg_w:.1f}" dur="1.3s" fill="freeze"/>'
            f"</rect>"
        )
        curr_x += seg_w
        lx = 28 + idx * 214
        legend_els.append(
            f'  <circle cx="{lx + 5}" cy="206" r="4" fill="{color}"/>'
            f'<text x="{lx + 15}" y="210" font-family="{SANS_FONT}" font-size="11" font-weight="600" fill="{t["text"]}">{esc(lname)} '
            f'<tspan font-family="{MONO_FONT}" font-weight="400" fill="{t["muted"]}">{pct:.1f}% ({cnt})</tspan></text>'
        )

    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 228" width="900" height="228" role="img" aria-label="52-Week GitHub Activity Chart and Language Distribution">',
            "  <defs>",
            '    <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">',
            f'      <stop offset="0%" stop-color="{t["accent"]}" stop-opacity="0.28"/>',
            f'      <stop offset="100%" stop-color="{t["accent"]}" stop-opacity="0.02"/>',
            "    </linearGradient>",
            "  </defs>",
            f'  <rect width="900" height="228" rx="12" fill="{t["bg"]}" stroke="{t["border"]}" stroke-width="1.1"/>',
            f'  <rect x="14" y="14" width="872" height="200" rx="9" fill="{t["surface"]}" stroke="{t["border"]}" stroke-width="0.9"/>',
            f'  <circle cx="32" cy="34" r="3.5" fill="{t["sage"]}">',
            '    <animate attributeName="opacity" values="1;0.35;1" dur="2.2s" repeatCount="indefinite"/>',
            "  </circle>",
            f'  <text x="44" y="38" font-family="{MONO_FONT}" font-size="11" font-weight="700" letter-spacing="0.8" fill="{t["text"]}">52-WEEK GITHUB ACTIVITY</text>',
            f'  <text x="872" y="38" text-anchor="end" font-family="{MONO_FONT}" font-size="10.8" fill="{t["muted"]}">{esc(summary)}</text>',
            *chart_svg,
            f'  <rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="3" fill="{t["surface_alt"]}"/>',
            *bar_rects,
            *legend_els,
            "</svg>\n",
        ]
    )


def build_footer_svg(mode: str) -> str:
    t = THEMES[mode]
    wave1 = _sine_wave_path(1800, 56, 12, 2, 0.2, 110)
    wave2 = _sine_wave_path(1800, 68, 9, 3, 2.0, 110)
    dots = []
    for idx, x in enumerate([95, 210, 330, 570, 690, 805]):
        dur = 3.2 + (idx % 3) * 0.8
        beg = f"{idx * 0.45:.2f}s"
        col = t["accent"] if idx % 2 == 0 else t["sage"]
        dots.append(
            f'  <circle cx="{x}" cy="86" r="2.6" fill="{col}">'
            f'<animate attributeName="cy" values="88;24" dur="{dur:.1f}s" begin="{beg}" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="0;0.85;0" dur="{dur:.1f}s" begin="{beg}" repeatCount="indefinite"/>'
            f"</circle>"
        )

    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 110" width="900" height="110" role="img" aria-label="Build Measure Self-Correct">',
            "  <defs>",
            '    <clipPath id="footClip"><rect x="14" y="10" width="872" height="90" rx="10"/></clipPath>',
            "  </defs>",
            f'  <rect width="900" height="110" rx="12" fill="{t["bg"]}" stroke="{t["border"]}" stroke-width="1"/>',
            f'  <rect x="14" y="10" width="872" height="90" rx="10" fill="{t["surface"]}" stroke="{t["border"]}" stroke-width="0.9"/>',
            '  <g clip-path="url(#footClip)">',
            "    <g>",
            f'      <path d="{wave1}" fill="{t["accent"]}" fill-opacity="0.14"/>',
            '      <animateTransform attributeName="transform" type="translate" from="0 0" to="-900 0" dur="15s" repeatCount="indefinite"/>',
            "    </g>",
            "    <g>",
            f'      <path d="{wave2}" fill="{t["sage"]}" fill-opacity="0.16"/>',
            '      <animateTransform attributeName="transform" type="translate" from="-900 0" to="0 0" dur="22s" repeatCount="indefinite"/>',
            "    </g>",
            *dots,
            "  </g>",
            f'  <text x="450" y="54" text-anchor="middle" font-family="{MONO_FONT}" font-size="13.5" font-weight="700" letter-spacing="3.2" fill="{t["text"]}">BUILD  ·  MEASURE  ·  SELF-CORRECT</text>',
            f'  <text x="450" y="74" text-anchor="middle" font-family="{SANS_FONT}" font-size="10.8" fill="{t["muted"]}">Rishav1996  ·  Open-Source AI Systems &amp; Behavioral Research Lab</text>',
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
        '<div align="center">\n\n'
        f"{row}\n\n"
        f"<sub><b>{len(badges)} Live Credly Digital Badges</b> · Auto-synced via GitHub Actions · Click any badge to verify</sub>\n\n"
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
        return "_Watch on [Algorhythm Chronicles](https://www.youtube.com/@algorythmchronicles)._"
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


def render_snake_block() -> str:
    if SNAKE_DARK.exists() and SNAKE_LIGHT.exists():
        return (
            '<div align="center">\n\n'
            "<picture>\n"
            '  <source media="(prefers-color-scheme: dark)" srcset="./assets/github-snake-dark.svg" />\n'
            '  <source media="(prefers-color-scheme: light)" srcset="./assets/github-snake-light.svg" />\n'
            '  <img width="100%" src="./assets/github-snake-dark.svg" alt="Contribution Snake Animation" />\n'
            "</picture>\n\n"
            "</div>"
        )
    return "<!-- Contribution snake renders automatically once Platane/snk runs in GitHub Actions -->"


def render_contrib_3d_block() -> str:
    if CONTRIB_3D_DARK.exists() and CONTRIB_3D_LIGHT.exists():
        return (
            "<details>\n"
            "<summary><strong>🌌 Explore 3D Isometric Contribution Skyline</strong></summary>\n\n"
            "<br/>\n\n"
            '<div align="center">\n'
            "<picture>\n"
            '  <source media="(prefers-color-scheme: dark)" srcset="./profile-3d-contrib/profile-night-view.svg" />\n'
            '  <source media="(prefers-color-scheme: light)" srcset="./profile-3d-contrib/profile-green-animate.svg" />\n'
            '  <img width="100%" src="./profile-3d-contrib/profile-night-view.svg" alt="3D GitHub Contribution Skyline" />\n'
            "</picture>\n"
            "</div>\n\n"
            "</details>"
        )
    return "<!-- 3D contribution skyline renders automatically once profile-3d-contrib workflow generates SVGs -->"


def main() -> int:
    if not README_PATH.exists():
        raise FileNotFoundError(f"Missing {README_PATH}")

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    readme_text = README_PATH.read_text(encoding="utf-8")

    gh_stats = fetch_github_stats()
    contribs = fetch_contributions()
    credly_badges = fetch_credly_badges()
    articles = fetch_standalone_articles()
    videos = fetch_youtube_videos()

    credly_count = len(credly_badges) if credly_badges is not None else 9

    for mode in ("dark", "light"):
        (ASSETS_DIR / f"hero-{mode}.svg").write_text(build_hero_svg(mode), encoding="utf-8")
        (ASSETS_DIR / f"stack-{mode}.svg").write_text(build_stack_svg(mode), encoding="utf-8")
        (ASSETS_DIR / f"footer-{mode}.svg").write_text(build_footer_svg(mode), encoding="utf-8")
        if gh_stats is not None:
            (ASSETS_DIR / f"pulse-{mode}.svg").write_text(
                build_pulse_svg(mode, gh_stats, contribs, credly_count=credly_count),
                encoding="utf-8",
            )

    if credly_badges:
        readme_text = replace_marker(readme_text, "CREDLY-BADGES", render_credly_block(credly_badges))

    if articles:
        feed_md, archive_md = render_writing_blocks(articles)
        readme_text = replace_marker(readme_text, "WRITING-FEED", feed_md)
        readme_text = replace_marker(readme_text, "WRITING-ARCHIVE", archive_md)

    if videos:
        readme_text = replace_marker(readme_text, "YOUTUBE-FEED", render_youtube_block(videos))

    readme_text = replace_marker(readme_text, "SNAKE-ANIM", render_snake_block())
    readme_text = replace_marker(readme_text, "CONTRIB-3D", render_contrib_3d_block())

    README_PATH.write_text(readme_text, encoding="utf-8")
    print(
        f"[ok] Synced polished kinetic SVGs & README "
        f"(gh={bool(gh_stats)}, weeks={len(contribs['weeks']) if contribs else 0}, "
        f"credly={credly_count}, articles={len(articles or [])}, videos={len(videos or [])})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
