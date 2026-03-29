# %%
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

import feedparser
import opml

CONTENT_DIR = Path("content/feeds")
OPML_PATH = "static/feeds.opml"
MAX_POSTS_PER_FEED = 10


# %%
def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text.strip("-")


def get_existing_urls(feed_dir: Path) -> set:
    urls = set()
    if not feed_dir.exists():
        return urls
    for md_file in feed_dir.glob("*.md"):
        content = md_file.read_text()
        match = re.search(r'^link\s*=\s*["\']?(.+?)["\']?\s*$', content, re.MULTILINE)
        if match:
            urls.add(match.group(1))
    return urls


def parse_date(date_str: str) -> str:
    if not date_str:
        return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    # handle most date formats
    try:
        dt = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %Z")
        return dt.strftime("%Y-%m-%dT%H:%M:%S")
    except ValueError:
        dt = None

    # handle grist date formats
    try:
        dt = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
        return dt.strftime("%Y-%m-%dT%H:%M:%S")
    except ValueError:
        dt = None

    # if all else fails
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def calc_expiry_time(date_str: str, hours: int) -> str:
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S")
        dt += timedelta(hours=hours)
        return dt.strftime("%Y-%m-%dT%H:%M:%S")
    except Exception:
        dt = datetime.now()
        dt += timedelta(hours=hours)
        return dt.strftime("%Y-%m-%dT%H:%M:%S")


# %%
def main():
    lp = opml.parse(OPML_PATH)
    os.makedirs("content/feeds", exist_ok=True)

    for feed in lp._outlines:
        feed_title = feed.title
        feed_url = feed.xmlURL
        feed_dir = CONTENT_DIR / slugify(feed_title)

        existing_urls = get_existing_urls(feed_dir)

        parsed = feedparser.parse(feed_url)

        entries = sorted(
            parsed.entries,
            key=lambda e: e.get("published", e.get("updated", "")),
            reverse=True,
        )

        new_count = 0
        for entry in entries:
            if new_count >= MAX_POSTS_PER_FEED:
                break

            link = entry.get("link", "")
            if link in existing_urls:
                continue

            title = entry.get("title", "Untitled")
            summary = entry.get("summary", "")
            summary = re.sub(r"<[^>]+>", "", summary)
            summary = summary.strip()
            author = entry.get("author", "")
            date_str = entry.get("published", entry.get("updated", ""))
            print(date_str)
            date = parse_date(date_str)
            expiry_date = calc_expiry_time(date, 72)

            entry_slug = f"{date[:10]}-{slugify(title)}"

            feed_dir.mkdir(parents=True, exist_ok=True)
            md_path = Path(os.path.join(feed_dir, f"{entry_slug}.md"))

            front_matter = f"""---
date: {date}
expiryDate: {expiry_date}
title: >
  {title}
link: '{link}'
feed: '{feed_title}'
author: '{author}'
---

{summary}
"""
            md_path.write_text(front_matter)
            existing_urls.add(link)
            new_count += 1
            print(f"Created: {md_path}")

        if new_count > 0:
            print(f"Processed {feed_title}: {new_count} new posts")


# %%
if __name__ == "__main__":
    main()
