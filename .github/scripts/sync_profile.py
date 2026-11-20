#!/usr/bin/env python3
"""
Automated animated SVG engine & live profile sync for Rishav1996/Rishav1996.

Uses Python standard library only so GitHub Actions executes with zero external pip installs.
- Fetches live GitHub user/repo stats, 365-day contribution calendar, Credly badges,
  Medium RSS articles (deduplicated against DOI triad labs), and YouTube Atom videos.
- Generates 8 animated Dark/Light Executive Studio SVGs in assets/ (SMIL <animate*>):
    1. hero-dark.svg / hero-light.svg          (Neural Agent Graph + 3Hz Horology Wheel + Sine Waves)
    2. lab-console-dark.svg / lab-console-light.svg (lab.toml Console + 22-Signal Drift Oscilloscope)
    3. pulse-dark.svg / pulse-light.svg        (Live 365-Day Heatmap + Scanner + Animated Language Bar)
    4. footer-dark.svg / footer-light.svg      (Counter-Flowing Dual Waves + Rising Signal Nodes)
- Updates marker blocks in README.md without touching or repeating any resume details.
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
        "heat": ["#161b22", "#163554", "#1f5382", "#3478bd", "#58a6ff"],
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
        "heat": ["#ebedf0", "#cfe1f5", "#8ebae5", "#3b7ec2", "#0F2942"],
    },
}

SANS_FONT = "'Segoe UI', 'Inter', -apple-system, BlinkMacSystemFont, Helvetica, Arial, sans-serif"
MONO_FONT = "'JetBrains Mono', 'Fira Code', 'SF Mono', Consolas, monospace"


def esc(val: Any) -> str:
    return html.escape(str(val), quote=True)


def http_get(url: str, headers: dict[str, str] | None = None, timeout: int = 15) -> str:
    req_headers = {"User-Agent": "Rishav1996-ProfileSync/3.0"}
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

    day_levels: dict[str, int] = {}
    for tag in re.findall(r"<td\b[^>]*>", raw_html):
        d_m = re.search(r'data-date="(\d{4}-\d{2}-\d{2})"', tag)
        l_m = re.search(r'data-level="(\d)"', tag)
        if d_m and l_m:
            day_levels[d_m.group(1)] = int(l_m.group(1))

    if not day_levels:
        return None

    days_sorted = sorted(day_levels.items(), key=lambda kv: kv[0])
    # Organize into Sunday-first weekly columns
    first_dt = datetime.strptime(days_sorted[0][0], "%Y-%m-%d").date()
    sun_offset = (first_dt.weekday() + 1) % 7
    grid_start = first_dt - timedelta(days=sun_offset)

    cells: list[tuple[int, int, int]] = []
    max_col = 0
    for date_str, lvl in days_sorted:
        dt = datetime.strptime(date_str, "%Y-%m-%d").date()
        delta = (dt - grid_start).days
        col = delta // 7
        row = delta % 7
        if col > max_col:
            max_col = col
        cells.append((col, row, lvl))

    return {
        "total_str": total_str,
        "num_weeks": max_col + 1,
        "cells": cells,
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


def _sine_stroke_path(width: int, baseline_y: float, amplitude: float, cycles: float, phase: float) -> str:
    step = 8
    pts: list[str] = []
    for x in range(0, width + step, step):
        y = baseline_y + amplitude * math.sin((2.0 * math.pi * cycles * x / 320.0) + phase)
        cmd = "M" if x == 0 else "L"
        pts.append(f"{cmd} {x} {y:.1f}")
    return " ".join(pts)


def build_hero_svg(mode: str) -> str:
    t = THEMES[mode]
    wave1 = _sine_wave_path(1800, 196, 12, 2, 0.0, 240)
    wave2 = _sine_wave_path(1800, 206, 9, 3, 1.4, 240)

    # Left and right Multi-Agent Neural Constellation paths + animated signal packets
    edges = [
        ("M 42 74 Q 95 45 142 96", 3.6, "0s", t["accent"]),
        ("M 42 150 Q 95 168 142 96", 4.4, "0.8s", t["sage"]),
        ("M 42 74 Q 58 112 42 150", 5.2, "1.6s", t["accent"]),
        ("M 142 96 Q 178 134 114 166", 4.1, "2.1s", t["sage"]),
        ("M 758 96 Q 804 54 856 84", 3.9, "0.4s", t["accent"]),
        ("M 758 96 Q 804 148 854 156", 4.7, "1.3s", t["sage"]),
    ]
    edge_paths = []
    packet_circles = []
    for idx, (d, dur, beg, col) in enumerate(edges):
        edge_paths.append(
            f'  <path id="edge{idx}" d="{d}" fill="none" stroke="{col}" stroke-width="1.2" stroke-opacity="0.32" stroke-dasharray="4 4">'
            f'<animate attributeName="stroke-dashoffset" from="0" to="-16" dur="2.2s" repeatCount="indefinite"/>'
            f"</path>"
        )
        packet_circles.append(
            f'  <circle r="3" fill="{col}">'
            f'<animateMotion path="{d}" dur="{dur}s" begin="{beg}" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="0;1;1;0" dur="{dur}s" begin="{beg}" repeatCount="indefinite"/>'
            f"</circle>"
        )

    nodes = [
        (42, 74, 4.5, t["accent"], "0s"),
        (42, 150, 4.0, t["sage"], "0.9s"),
        (142, 96, 5.2, t["accent"], "0.4s"),
        (114, 166, 3.8, t["sage"], "1.4s"),
        (758, 96, 5.2, t["accent"], "0.6s"),
        (856, 84, 4.2, t["sage"], "1.1s"),
        (854, 156, 4.0, t["accent"], "0.2s"),
    ]
    node_circles = [
        f'  <circle cx="{cx}" cy="{cy}" r="{r}" fill="{col}" fill-opacity="0.85">'
        f'<animate attributeName="r" values="{r};{r+1.6};{r}" dur="3.2s" begin="{beg}" repeatCount="indefinite"/>'
        f'<animate attributeName="fill-opacity" values="0.65;1;0.65" dur="3.2s" begin="{beg}" repeatCount="indefinite"/>'
        f"</circle>"
        for cx, cy, r, col, beg in nodes
    ]

    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 240" width="900" height="240" role="img" aria-label="Rishav Saigal — AI Systems Lab and Open Research">',
            "  <defs>",
            '    <clipPath id="heroInner"><rect x="14" y="14" width="872" height="212" rx="11"/></clipPath>',
            "  </defs>",
            f'  <rect width="900" height="240" rx="14" fill="{t["bg"]}" stroke="{t["border"]}" stroke-width="1.2"/>',
            f'  <rect x="14" y="14" width="872" height="212" rx="11" fill="{t["surface"]}" stroke="{t["border"]}" stroke-width="0.9"/>',
            "",
            "  <!-- Dual-layer flowing sine waves -->",
            '  <g clip-path="url(#heroInner)">',
            '    <g>',
            f'      <path d="{wave1}" fill="{t["accent"]}" fill-opacity="0.11"/>',
            f'      <animateTransform attributeName="transform" type="translate" from="0 0" to="-900 0" dur="14s" repeatCount="indefinite"/>',
            "    </g>",
            '    <g>',
            f'      <path d="{wave2}" fill="{t["sage"]}" fill-opacity="0.13"/>',
            f'      <animateTransform attributeName="transform" type="translate" from="-900 0" to="0 0" dur="20s" repeatCount="indefinite"/>',
            "    </g>",
            "  </g>",
            "",
            "  <!-- Multi-Agent Neural Constellations -->",
            *edge_paths,
            *node_circles,
            *packet_circles,
            "",
            "  <!-- Horological 3Hz Balance Wheel Micro-Emblem (top-right) -->",
            f'  <g transform="translate(842, 46)">',
            f'    <circle cx="0" cy="0" r="14" fill="none" stroke="{t["brass"]}" stroke-width="1.2" stroke-opacity="0.55" stroke-dasharray="2 3"/>',
            "    <g>",
            f'      <circle cx="0" cy="0" r="9.5" fill="none" stroke="{t["brass"]}" stroke-width="1.5"/>',
            f'      <line x1="-9.5" y1="0" x2="9.5" y2="0" stroke="{t["brass"]}" stroke-width="1.1"/>',
            f'      <line x1="0" y1="-9.5" x2="0" y2="9.5" stroke="{t["brass"]}" stroke-width="1.1"/>',
            f'      <circle cx="0" cy="0" r="2.3" fill="{t["brass"]}"/>',
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
            f'  <text x="450" y="110" text-anchor="middle" font-family="{SANS_FONT}" font-size="42" font-weight="800" letter-spacing="2.4" fill="{t["text"]}">RISHAV SAIGAL</text>',
            "",
            "  <!-- Animated Accent Rule -->",
            f'  <line x1="290" y1="126" x2="610" y2="126" stroke="{t["border"]}" stroke-width="1.2"/>',
            f'  <line x1="360" y1="126" x2="540" y2="126" stroke="{t["accent"]}" stroke-width="2" stroke-linecap="round">',
            '    <animate attributeName="x1" values="360;310;360" dur="5s" repeatCount="indefinite"/>',
            '    <animate attributeName="x2" values="540;590;540" dur="5s" repeatCount="indefinite"/>',
            "  </line>",
            "",
            "  <!-- Builder Identity (Zero Resume Highlights) -->",
            f'  <text x="450" y="156" text-anchor="middle" font-family="{SANS_FONT}" font-size="13.5" font-weight="600" letter-spacing="0.4" fill="{t["accent"]}">Multi-Agent Orchestration  ·  LLM Behavioral Drift  ·  Open-Source AI Tooling  ·  Horology</text>',
            "",
            "  <!-- Sub-caption -->",
            f'  <text x="450" y="182" text-anchor="middle" font-family="{MONO_FONT}" font-size="10.8" fill="{t["muted"]}">FastMCP · Google ADK · LangGraph · A2UI · Zenodo Open Benchmarks · Algorhythm Chronicles</text>',
            "</svg>\n",
        ]
    )


def build_lab_console_svg(mode: str) -> str:
    t = THEMES[mode]
    osc_wave1 = _sine_stroke_path(640, 108, 18, 2.0, 0.0)
    osc_wave2 = _sine_stroke_path(640, 108, 12, 3.0, 1.3)

    # 22 signal equalizer bars at the base of the oscilloscope (representing 22 drift signals)
    bars: list[str] = []
    for i in range(22):
        bx = 562 + i * 14
        base_h = 5 + ((i * 5) % 9)
        peak_h = 17 + ((i * 7) % 11)
        dur = 1.35 + (i % 5) * 0.35
        col = t["accent"] if i % 2 == 0 else t["sage"]
        bars.append(
            f'  <rect x="{bx}" y="{182 - base_h}" width="7" height="{base_h}" rx="2" fill="{col}" fill-opacity="0.82">'
            f'<animate attributeName="height" values="{base_h};{peak_h};{base_h}" dur="{dur:.2f}s" repeatCount="indefinite"/>'
            f'<animate attributeName="y" values="{182 - base_h};{182 - peak_h};{182 - base_h}" dur="{dur:.2f}s" repeatCount="indefinite"/>'
            f"</rect>"
        )

    lines = [
        ("focus", '["Multi-Agent Systems", "A2UI", "Model Routing"]'),
        ("research", '"LLM Drift &amp; Self-Coined Calcification Effect"'),
        ("shipping", '["a2ui-ad-component", "model-router", "PyCaretAgent"]'),
        ("creating", '["Algorhythm Chronicles", "Mechanical Horology"]'),
        ("resume", '"rishavsaigal.web.app/resume"  # full CV link'),
    ]
    toml_els = []
    for idx, (k, v) in enumerate(lines):
        y = 80 + idx * 24
        toml_els.append(
            f'  <text x="34" y="{y}" font-family="{MONO_FONT}" font-size="11.3" font-weight="700" fill="{t["sage"]}">{k:<8}</text>'
            f'<text x="98" y="{y}" font-family="{MONO_FONT}" font-size="11.3" fill="{t["muted"]}">=</text>'
            f'<text x="112" y="{y}" font-family="{MONO_FONT}" font-size="11.3" fill="{t["text"]}">{v}</text>'
        )

    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 218" width="900" height="218" role="img" aria-label="AI Lab Terminal Console and 22-Signal Behavioral Drift Oscilloscope">',
            "  <defs>",
            '    <clipPath id="oscClip"><rect x="558" y="64" width="314" height="90" rx="6"/></clipPath>',
            "  </defs>",
            f'  <rect width="900" height="218" rx="12" fill="{t["bg"]}" stroke="{t["border"]}" stroke-width="1.1"/>',
            "",
            "  <!-- Left Terminal Panel -->",
            f'  <rect x="14" y="14" width="514" height="190" rx="9" fill="{t["surface"]}" stroke="{t["border"]}" stroke-width="1"/>',
            f'  <path d="M 14 23 A 9 9 0 0 1 23 14 L 519 14 A 9 9 0 0 1 528 23 L 528 44 L 14 44 Z" fill="{t["surface_alt"]}"/>',
            f'  <line x1="14" y1="44" x2="528" y2="44" stroke="{t["border"]}" stroke-width="1"/>',
            f'  <circle cx="34" cy="29" r="4.5" fill="{t["dim"]}"/>',
            f'  <circle cx="50" cy="29" r="4.5" fill="{t["brass"]}"/>',
            f'  <circle cx="66" cy="29" r="4.5" fill="{t["sage"]}"/>',
            f'  <text x="275" y="33" text-anchor="middle" font-family="{MONO_FONT}" font-size="11" font-weight="600" fill="{t["muted"]}">lab.toml  —  rishav@ai-lab</text>',
            *toml_els,
            f'  <rect x="34" y="186" width="8" height="12" rx="1.5" fill="{t["accent"]}">',
            '    <animate attributeName="opacity" values="1;1;0;0;1" dur="1.1s" repeatCount="indefinite"/>',
            "  </rect>",
            f'  <text x="48" y="196" font-family="{MONO_FONT}" font-size="10.5" fill="{t["muted"]}">status: experimenting · measuring · open-sourcing</text>',
            "",
            "  <!-- Right Animated 22-Signal Drift Oscilloscope -->",
            f'  <rect x="544" y="14" width="342" height="190" rx="9" fill="{t["surface"]}" stroke="{t["border"]}" stroke-width="1"/>',
            f'  <text x="562" y="36" font-family="{MONO_FONT}" font-size="10.8" font-weight="700" letter-spacing="0.7" fill="{t["muted"]}">DRIFT OSCILLOSCOPE</text>',
            f'  <circle cx="858" cy="32" r="4" fill="{t["sage"]}">',
            '    <animate attributeName="opacity" values="1;0.3;1" dur="1.8s" repeatCount="indefinite"/>',
            "  </circle>",
            f'  <text x="846" y="36" text-anchor="end" font-family="{MONO_FONT}" font-size="10" fill="{t["sage"]}">LIVE</text>',
            f'  <rect x="558" y="64" width="314" height="90" rx="6" fill="{t["surface_alt"]}" stroke="{t["border"]}" stroke-width="0.8"/>',
            f'  <line x1="558" y1="109" x2="872" y2="109" stroke="{t["border"]}" stroke-dasharray="3 4" stroke-width="0.9"/>',
            f'  <line x1="558" y1="86" x2="872" y2="86" stroke="{t["border"]}" stroke-dasharray="2 5" stroke-width="0.7"/>',
            f'  <line x1="558" y1="132" x2="872" y2="132" stroke="{t["border"]}" stroke-dasharray="2 5" stroke-width="0.7"/>',
            '  <g clip-path="url(#oscClip)">',
            '    <g transform="translate(558, 0)">',
            f'      <path d="{osc_wave1}" fill="none" stroke="{t["accent"]}" stroke-width="1.8">',
            '        <animateTransform attributeName="transform" type="translate" from="0 0" to="-320 0" dur="5.2s" repeatCount="indefinite"/>',
            "      </path>",
            f'      <path d="{osc_wave2}" fill="none" stroke="{t["sage"]}" stroke-width="1.5" stroke-opacity="0.85">',
            '        <animateTransform attributeName="transform" type="translate" from="-320 0" to="0 0" dur="7.6s" repeatCount="indefinite"/>',
            "      </path>",
            "    </g>",
            f'    <line x1="558" y1="64" x2="558" y2="154" stroke="{t["brass"]}" stroke-width="1.4" stroke-opacity="0.65">',
            '      <animateTransform attributeName="transform" type="translate" from="0 0" to="314 0" dur="4.8s" repeatCount="indefinite"/>',
            "    </line>",
            "  </g>",
            *bars,
            f'  <text x="715" y="198" text-anchor="middle" font-family="{MONO_FONT}" font-size="9.6" letter-spacing="0.7" fill="{t["muted"]}">22 SIGNALS  ·  5 DIMENSIONS  ·  CALCIFICATION MONITOR</text>',
            "</svg>\n",
        ]
    )


def build_pulse_svg(
    mode: str,
    gh: dict[str, Any],
    contribs: dict[str, Any] | None,
    credly_count: int,
) -> str:
    t = THEMES[mode]
    heat_palette = t["heat"]
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

    # Heatmap geometry: 53 weeks centered inside 868px card
    cells_svg: list[str] = []
    if contribs and contribs["cells"]:
        num_weeks = max(1, min(54, contribs["num_weeks"]))
        pitch = 15
        grid_w = num_weeks * pitch
        start_x = (900 - grid_w) / 2.0
        start_y = 54
        for col, row, lvl in contribs["cells"]:
            cx = start_x + col * pitch
            cy = start_y + row * pitch
            fill = heat_palette[min(4, max(0, lvl))]
            cells_svg.append(
                f'  <rect x="{cx:.1f}" y="{cy}" width="11" height="11" rx="2.5" fill="{fill}"/>'
            )
    else:
        cells_svg.append(
            f'  <text x="450" y="106" text-anchor="middle" font-family="{MONO_FONT}" font-size="12" fill="{t["muted"]}">GitHub Contribution Heatmap Synced via Actions</text>'
        )

    # Animated Language Bar
    bar_x = 28
    bar_y = 178
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
            f'  <circle cx="{lx + 5}" cy="204" r="4" fill="{color}"/>'
            f'<text x="{lx + 15}" y="208" font-family="{SANS_FONT}" font-size="11" font-weight="600" fill="{t["text"]}">{esc(lname)} '
            f'<tspan font-family="{MONO_FONT}" font-weight="400" fill="{t["muted"]}">{pct:.1f}% ({cnt})</tspan></text>'
        )

    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 226" width="900" height="226" role="img" aria-label="Live GitHub Contribution Pulse and Language Distribution">',
            "  <defs>",
            '    <clipPath id="heatClip"><rect x="28" y="50" width="844" height="114" rx="6"/></clipPath>',
            '    <linearGradient id="scanGrad" x1="0" y1="0" x2="1" y2="0">',
            f'      <stop offset="0%" stop-color="{t["accent"]}" stop-opacity="0"/>',
            f'      <stop offset="50%" stop-color="{t["accent"]}" stop-opacity="0.16"/>',
            f'      <stop offset="100%" stop-color="{t["accent"]}" stop-opacity="0"/>',
            "    </linearGradient>",
            "  </defs>",
            f'  <rect width="900" height="226" rx="12" fill="{t["bg"]}" stroke="{t["border"]}" stroke-width="1.1"/>',
            f'  <rect x="14" y="14" width="872" height="198" rx="9" fill="{t["surface"]}" stroke="{t["border"]}" stroke-width="0.9"/>',
            f'  <circle cx="32" cy="34" r="3.5" fill="{t["sage"]}">',
            '    <animate attributeName="opacity" values="1;0.35;1" dur="2.2s" repeatCount="indefinite"/>',
            "  </circle>",
            f'  <text x="44" y="38" font-family="{MONO_FONT}" font-size="11" font-weight="700" letter-spacing="0.8" fill="{t["text"]}">LIVE GITHUB PULSE</text>',
            f'  <text x="872" y="38" text-anchor="end" font-family="{MONO_FONT}" font-size="10.8" fill="{t["muted"]}">{esc(summary)}</text>',
            *cells_svg,
            '  <g clip-path="url(#heatClip)">',
            '    <rect x="-120" y="50" width="120" height="114" fill="url(#scanGrad)">',
            '      <animateTransform attributeName="transform" type="translate" from="0 0" to="1040 0" dur="7s" repeatCount="indefinite"/>',
            "    </rect>",
            "  </g>",
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
        (ASSETS_DIR / f"lab-console-{mode}.svg").write_text(build_lab_console_svg(mode), encoding="utf-8")
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
        f"[ok] Synced kinetic lab SVGs & README "
        f"(gh={bool(gh_stats)}, contrib_days={len(contribs['cells']) if contribs else 0}, "
        f"credly={credly_count}, articles={len(articles or [])}, videos={len(videos or [])})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
