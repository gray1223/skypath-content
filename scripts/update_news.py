#!/usr/bin/env python3
"""
Fetches aviation news from RSS feeds and writes news_feed.json.
Run manually or via GitHub Actions on a schedule.
"""

import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from urllib.error import URLError
import re
import hashlib

FEEDS = [
    {
        "url": "https://avweb.com/feed/",
        "source": "AvWeb",
        "default_category": "industry",
        "category_map": {
            "flight training": "training",
            "flight-training": "training",
            "safety": "training",
            "aviation news": "industry",
            "company news": "industry",
            "avweb insider": "industry",
            "regulations": "regulatory",
            "ntsb": "regulatory",
            "faa": "regulatory",
            "military": "military",
        }
    },
    {
        "url": "https://simpleflying.com/feed/",
        "source": "Simple Flying",
        "default_category": "industry",
        "category_map": {
            "airlines": "industry",
            "airline news": "industry",
            "military": "military",
            "aircraft": "industry",
            "airports": "industry",
            "training": "training",
        }
    },
    {
        "url": "https://www.flyingmag.com/feed/",
        "source": "Flying Magazine",
        "default_category": "industry",
        "category_map": {
            "training": "training",
            "pilot reports": "industry",
            "safety": "training",
        }
    },
]

# Keywords that indicate articles relevant to pilot career planning
RELEVANT_KEYWORDS = [
    "pilot", "airline", "hiring", "training", "flight school", "faa",
    "atp", "checkride", "certificate", "rating", "instrument", "commercial",
    "regional", "captain", "first officer", "cadet", "military", "air force",
    "navy", "skillbridge", "scholarship", "pay", "salary", "contract",
    "fleet", "order", "delivery", "new route", "base", "domicile",
    "retirement", "shortage", "furlough", "cargo", "freight", "netjets",
    "fractional", "corporate", "charter", "cfi", "instructor",
    "aviate", "propel", "envoy", "skywest", "republic", "endeavor",
    "delta", "united", "american", "southwest", "alaska", "jetblue",
    "frontier", "breeze", "avelo", "allegiant", "fedex", "ups",
]

VALID_CATEGORIES = ["hiring", "industry", "regulatory", "training", "military", "pay"]

def fetch_feed(url):
    """Fetch and parse an RSS feed."""
    try:
        req = Request(url, headers={"User-Agent": "ClearedDirect/1.0"})
        with urlopen(req, timeout=15) as resp:
            return ET.fromstring(resp.read())
    except (URLError, ET.ParseError) as e:
        print(f"  Error fetching {url}: {e}")
        return None

def is_relevant(title, description):
    """Check if article is relevant to pilot career planning."""
    text = f"{title} {description}".lower()
    return any(kw in text for kw in RELEVANT_KEYWORDS)

def classify_category(categories, category_map, default, title="", description=""):
    """Classify using content analysis first, then RSS categories as fallback."""
    text = f"{title} {description}".lower()

    hiring_words = ["hiring", "new hire", "class size", "pilot shortage", "furlough",
                    "job fair", "cadet", "pathway program", "flow-through", "upgrade time"]
    pay_words = ["pay raise", "salary", "compensation", "bonus", "contract ratif", "wage"]
    regulatory_words = ["faa rule", "ntsb", "regulation", "nprm", "airworthiness directive",
                        "advisory circular", "basicmed", "14 cfr"]
    training_words = ["flight school", "flight training", "checkride", "student pilot",
                      "cfi", "instructor", "learn to fly", "scholarship", "written exam"]
    military_words = ["military pilot", "air force pilot", "navy pilot", "skillbridge",
                      "veteran pilot", "guard unit", "reserve unit", "upt"]

    if any(w in text for w in hiring_words):
        return "hiring"
    if any(w in text for w in pay_words):
        return "pay"
    if any(w in text for w in regulatory_words):
        return "regulatory"
    if any(w in text for w in training_words):
        return "training"
    if any(w in text for w in military_words):
        return "military"

    for cat in categories:
        cat_lower = cat.lower()
        for key, value in category_map.items():
            if key in cat_lower:
                return value
    return default

def make_id(title, source):
    """Generate a stable unique ID from title."""
    raw = f"{source}_{title}".lower()
    return hashlib.md5(raw.encode()).hexdigest()[:12]

def parse_date(date_str):
    """Parse RSS date formats to ISO 8601."""
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%a, %d %b %Y %H:%M:%S GMT",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            continue
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def detect_airline_tag(title, description):
    """Extract airline name if mentioned."""
    text = f"{title} {description}"
    airlines = {
        "United": "United Airlines", "Delta": "Delta Air Lines",
        "American Airlines": "American Airlines", "Southwest": "Southwest Airlines",
        "Alaska Airlines": "Alaska Airlines", "JetBlue": "JetBlue Airways",
        "Frontier": "Frontier Airlines", "Breeze": "Breeze Airways",
        "SkyWest": "SkyWest Airlines", "Republic": "Republic Airways",
        "Envoy": "Envoy Air", "FedEx": "FedEx Express",
        "UPS": "UPS Airlines", "NetJets": "NetJets",
    }
    for keyword, full_name in airlines.items():
        if keyword in text:
            return full_name
    return None

def main():
    all_items = []

    for feed_config in FEEDS:
        print(f"Fetching {feed_config['source']}...")
        root = fetch_feed(feed_config["url"])
        if root is None:
            continue

        channel = root.find("channel")
        if channel is None:
            continue

        items = channel.findall("item")
        print(f"  Found {len(items)} items")

        for item in items:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            desc = (item.findtext("description") or "").strip()
            pub_date = (item.findtext("pubDate") or "").strip()
            categories = [c.text for c in item.findall("category") if c.text]

            # Clean HTML from description
            desc = re.sub(r"<[^>]+>", "", desc).strip()
            desc = re.sub(r"\s+", " ", desc)
            if len(desc) > 280:
                desc = desc[:277] + "..."

            if not title or not link:
                continue

            if not is_relevant(title, desc):
                continue

            category = classify_category(
                categories, feed_config["category_map"], feed_config["default_category"],
                title=title, description=desc
            )

            news_item = {
                "id": make_id(title, feed_config["source"]),
                "title": title,
                "summary": desc,
                "source": feed_config["source"],
                "category": category,
                "publishedDate": parse_date(pub_date),
                "url": link,
                "airlineTag": detect_airline_tag(title, desc),
                "isBreaking": False,
            }
            all_items.append(news_item)

    # Sort by date, newest first, keep top 20
    all_items.sort(key=lambda x: x["publishedDate"], reverse=True)
    all_items = all_items[:40]

    print(f"\n{len(all_items)} relevant articles selected")

    # Write output
    output_path = "v1/news_feed.json"
    with open(output_path, "w") as f:
        json.dump(all_items, f, indent=2)

    print(f"Written to {output_path}")

    # Print summary
    for item in all_items[:5]:
        print(f"  [{item['category']}] {item['title'][:60]}...")

if __name__ == "__main__":
    main()
