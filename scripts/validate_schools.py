#!/usr/bin/env python3
"""Validate flight school URLs in v1/flight_schools.json.

Reads the JSON file, performs HTTP HEAD requests on each school's URL,
and reports any broken links to stdout.
"""

import json
import sys
import urllib.request
import urllib.error
from pathlib import Path


def validate_schools():
    json_path = Path(__file__).resolve().parent.parent / "v1" / "flight_schools.json"

    with open(json_path, "r", encoding="utf-8") as f:
        schools = json.load(f)

    total = len(schools)
    schools_with_urls = [s for s in schools if s.get("url")]
    broken = []

    print(f"Checking {len(schools_with_urls)} URLs out of {total} total schools...\n")

    for school in schools_with_urls:
        name = school["name"]
        url = school["url"]
        try:
            req = urllib.request.Request(url, method="HEAD")
            req.add_header("User-Agent", "SkyPath-Validator/1.0")
            with urllib.request.urlopen(req, timeout=10) as resp:
                status = resp.status
                if status == 404:
                    broken.append({"name": name, "url": url, "error": f"HTTP {status}"})
                    print(f"  BROKEN  {name}: {url} (HTTP {status})")
                else:
                    print(f"  OK      {name}: {url}")
        except urllib.error.HTTPError as e:
            if e.code == 405:
                # HEAD not allowed, try GET
                try:
                    req = urllib.request.Request(url, method="GET")
                    req.add_header("User-Agent", "SkyPath-Validator/1.0")
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        print(f"  OK      {name}: {url}")
                        continue
                except Exception as e2:
                    error_msg = str(e2)
            elif e.code == 404:
                error_msg = f"HTTP {e.code}"
            else:
                # Other HTTP errors (403, 500, etc.) — not necessarily broken
                print(f"  OK      {name}: {url} (HTTP {e.code})")
                continue
            if e.code in (404,):
                broken.append({"name": name, "url": url, "error": error_msg})
                print(f"  BROKEN  {name}: {url} ({error_msg})")
            elif e.code == 405:
                broken.append({"name": name, "url": url, "error": error_msg})
                print(f"  BROKEN  {name}: {url} ({error_msg})")
        except Exception as e:
            error_msg = str(e)
            broken.append({"name": name, "url": url, "error": error_msg})
            print(f"  BROKEN  {name}: {url} ({error_msg})")

    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION REPORT")
    print("=" * 60)
    print(f"Total schools:      {total}")
    print(f"Schools with URLs:  {len(schools_with_urls)}")
    print(f"Broken URLs:        {len(broken)}")

    if broken:
        print("\nBroken URL details:")
        print("-" * 60)
        for entry in broken:
            print(f"  School: {entry['name']}")
            print(f"  URL:    {entry['url']}")
            print(f"  Error:  {entry['error']}")
            print()

    return len(broken)


if __name__ == "__main__":
    broken_count = validate_schools()
    sys.exit(1 if broken_count > 0 else 0)
