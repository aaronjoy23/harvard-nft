"""Fetch artworks from the Harvard Art Museums API into a static gallery.

Writes site/gallery.json. Images are not downloaded here; the visitor's
browser loads them from Harvard's IIIF image service when the page is viewed.
"""
import argparse
import json
import os
from pathlib import Path

import requests

API_URL = "https://api.harvardartmuseums.org/object"
FIELDS = ("objectid,title,dated,culture,classification,medium,people,"
          "primaryimageurl,url,century,imagepermissionlevel,images")


def image_url(obj, width):
    """Prefer the IIIF service (sizable, CORS-enabled) over the nrs redirect."""
    for im in obj.get("images") or []:
        if im.get("iiifbaseuri"):
            return f"{im['iiifbaseuri']}/full/{width},/0/default.jpg"
    return f"{obj['primaryimageurl']}?width={width}"


def fetch_page(api_key, page, size, classification):
    params = {"apikey": api_key, "size": size, "page": page, "hasimage": 1,
              "fields": FIELDS, "sort": "random"}
    if classification:
        params["classification"] = classification
    r = requests.get(API_URL, params=params, timeout=30)
    r.raise_for_status()
    return r.json().get("records", [])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=48)
    ap.add_argument("--classification", help="e.g. Paintings, Prints, Photographs")
    ap.add_argument("--out", default="site")
    args = ap.parse_args()

    api_key = os.environ.get("HARVARD_API_KEY")
    if not api_key:
        raise SystemExit("Set the HARVARD_API_KEY environment variable.")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    items, seen = [], set()
    for page in range(1, 11):
        if len(items) >= args.count:
            break
        records = fetch_page(api_key, page, 100, args.classification)
        print(f"Page {page}: {len(records)} records")
        if not records:
            break
        for obj in records:
            if len(items) >= args.count:
                break
            # imagepermissionlevel 0 = image may be freely displayed
            if (not obj.get("primaryimageurl") or obj.get("imagepermissionlevel")
                    or obj["objectid"] in seen):
                continue
            seen.add(obj["objectid"])
            items.append({
                "id": obj["objectid"],
                "title": obj.get("title") or "Untitled",
                "artist": ", ".join(p["name"] for p in obj.get("people") or []) or "Unknown artist",
                "dated": obj.get("dated") or "",
                "culture": obj.get("culture"),
                "century": obj.get("century"),
                "classification": obj.get("classification"),
                "medium": obj.get("medium"),
                "url": obj.get("url"),
                "thumb": image_url(obj, 400),
                "image": image_url(obj, 800),
            })
            print(f"  + {obj['objectid']} {items[-1]['title']}")

    if not items:
        raise SystemExit("No usable artworks found - see messages above.")
    (out / "gallery.json").write_text(json.dumps(items, indent=2))
    print(f"Saved {len(items)} artworks")


if __name__ == "__main__":
    main()
