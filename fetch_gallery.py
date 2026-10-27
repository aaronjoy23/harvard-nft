"""Fetch artworks from the Harvard Art Museums API into a static gallery.

Writes site/gallery.json and site/img/<objectid>.jpg. Images are stored
alongside the page so the browser can draw them onto a canvas (no CORS issues).
"""
import argparse
import io
import json
import os
from pathlib import Path

import requests
from PIL import Image

API_URL = "https://api.harvardartmuseums.org/object"
FIELDS = ("objectid,title,dated,culture,classification,medium,people,"
          "primaryimageurl,url,century,imagepermissionlevel")


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
    (out / "img").mkdir(parents=True, exist_ok=True)
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
            try:
                resp = requests.get(obj["primaryimageurl"] + "?width=800", timeout=60)
                resp.raise_for_status()
                img = Image.open(io.BytesIO(resp.content)).convert("RGB")
                img.thumbnail((800, 800))
                img.save(out / "img" / f"{obj['objectid']}.jpg", quality=85)
            except Exception as e:
                print(f"  skip {obj['objectid']}: {e}")
                continue
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
                "image": f"img/{obj['objectid']}.jpg",
            })
            print(f"  + {obj['objectid']} {items[-1]['title']}")

    if not items:
        raise SystemExit("No usable artworks found - see messages above.")
    (out / "gallery.json").write_text(json.dumps(items, indent=2))
    print(f"Saved {len(items)} artworks")


if __name__ == "__main__":
    main()
