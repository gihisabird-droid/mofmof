#!/usr/bin/env python3
"""もふもふ不動産 /column/ から RSS(docs/feed.xml) を生成する。
- /column/ (日付つき) と /column/articles/ (全件) を取得
- 日付が取れない記事は「初めて見つけた時刻」を公開日にする(docs/state.json に保存)
"""
import json, re, sys, datetime as dt
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse
from xml.sax.saxutils import escape
import requests
from bs4 import BeautifulSoup

BASE = "https://mofmof-investor.com"
PAGES = [f"{BASE}/column/", f"{BASE}/column/articles/"]
CATS = ["企業分析", "技術解説", "経済解説", "コラム"]
JST = dt.timezone(dt.timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "docs" / "state.json"
OUT = ROOT / "docs" / "feed.xml"
MAX_ITEMS = 40
EXCLUDE = re.compile(r"^/(column|invest|chart|topics|expertise|membership|press|tieup|consulting|contact|company|privacy|search|news)(/|\.html|$)|^/$|^/#")

def norm(url):
    p = urlparse(urljoin(BASE, url))
    path = re.sub(r"\.html$", "", p.path).rstrip("/")
    return f"{BASE}{path}"

def parse(html):
    soup = BeautifulSoup(html, "html.parser")
    found = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        path = urlparse(urljoin(BASE, href)).path
        if urlparse(urljoin(BASE, href)).netloc not in ("", "mofmof-investor.com"):
            continue
        if EXCLUDE.search(path):
            continue
        text = re.sub(r"\s+", " ", a.get_text(" ", strip=True))
        text = re.sub(r"^\d{1,2}\s*", "", text)  # ランキング欄の先頭番号を除去
        cat = next((c for c in CATS if text.startswith(c)), None)
        if not cat:
            continue
        rest = text[len(cat):].strip()
        m = re.search(r"(\d{4})\.(\d{2})\.(\d{2})", rest)
        date = None
        if m:
            date = dt.datetime(int(m[1]), int(m[2]), int(m[3]), 9, 0, tzinfo=JST)
            rest = rest.replace(m[0], "")
        title = re.sub(r"^更新\s*", "", rest.strip()).strip()
        if title:
            found.append({"url": norm(href), "title": title, "category": cat, "date": date})
    return found

def main():
    items = {}
    for page in PAGES:
        r = requests.get(page, timeout=30, headers={"User-Agent": "Mozilla/5.0 (feed-builder)"})
        r.raise_for_status()
        r.encoding = r.apparent_encoding if r.encoding in (None, "ISO-8859-1") else r.encoding
        for it in parse(r.text):
            cur = items.get(it["url"])
            if cur is None:
                items[it["url"]] = it
            else:  # 日付つきの方を優先
                if it["date"] and not cur["date"]:
                    cur["date"] = it["date"]
                if len(it["title"]) > len(cur["title"]) and not cur["date"]:
                    cur["title"] = it["title"]
    if not items:
        sys.exit("記事が1件も取得できませんでした(サイト構造が変わった可能性)")

    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    now = dt.datetime.now(JST)
    first_run = not state
    order = list(items.keys())  # 掲載順(新しい順)
    for i, url in enumerate(order):
        it = items[url]
        if it["date"]:
            state[url] = it["date"].isoformat()
        elif url not in state:
            # 初回は掲載順を保つため古い方から少しずつずらす。以降は取得時刻。
            state[url] = (now - dt.timedelta(minutes=i) if first_run else now).isoformat()
        it["date"] = dt.datetime.fromisoformat(state[url])
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1))

    ordered = sorted(items.values(), key=lambda x: x["date"], reverse=True)[:MAX_ITEMS]
    feed_url = (ROOT / "docs" / "FEED_URL.txt").read_text().strip() if (ROOT / "docs" / "FEED_URL.txt").exists() else f"{BASE}/column/"
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>',
             "<title>投資・テクノロジー解説 | もふもふ不動産</title>",
             f"<link>{BASE}/column/</link>",
             "<description>決算分析・相場・半導体/AIの技術解説(非公式に自動生成したフィード)</description>",
             "<language>ja</language>",
             f"<lastBuildDate>{format_datetime(now)}</lastBuildDate>",
             f'<atom:link href="{escape(feed_url)}" rel="self" type="application/rss+xml"/>']
    for it in ordered:
        parts.append(
            f"<item><title>{escape(it['title'])}</title><link>{escape(it['url'])}</link>"
            f'<guid isPermaLink="true">{escape(it["url"])}</guid>'
            f"<pubDate>{format_datetime(it['date'])}</pubDate>"
            f"<category>{escape(it['category'])}</category>"
            f"<description>{escape(it['title'])}</description></item>")
    parts.append("</channel></rss>")
    OUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"{len(ordered)} items written")

if __name__ == "__main__":
    main()
