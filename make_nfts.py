"""Fetch artworks from the Harvard Art Museums API and render NFT-style cards.

Each artwork produces:
  output/images/<token_id>.png  - pixelated, framed "collectible" card
  output/metadata/<token_id>.json - ERC-721 / OpenSea-style metadata
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps

API_URL = "https://api.harvardartmuseums.org/object"
CARD_W, CARD_H = 600, 800
ART_BOX = 520

PALETTES = {
    "Common": ((40, 40, 48), (180, 180, 190)),
    "Rare": ((20, 40, 90), (90, 160, 255)),
    "Epic": ((60, 20, 90), (200, 110, 255)),
    "Legendary": ((90, 60, 10), (255, 200, 60)),
}


def fetch_objects(api_key, count, classification=None, page=1):
    params = {
        "apikey": api_key,
        "size": count,
        "page": page,
        "hasimage": 1,
        "fields": "objectid,title,dated,culture,classification,medium,"
                  "people,primaryimageurl,url,century,imagepermissionlevel",
        "sort": "random",
    }
    if classification:
        params["classification"] = classification
    r = requests.get(API_URL, params=params, timeout=30)
    r.raise_for_status()
    records = r.json().get("records", [])
    print(f"API returned {len(records)} records")
    # imagepermissionlevel 0 = image may be freely displayed
    return [o for o in records
            if o.get("primaryimageurl") and not o.get("imagepermissionlevel")]


def traits_for(obj):
    """Deterministic 'rarity' traits derived from a hash of the object id."""
    h = hashlib.sha256(str(obj["objectid"]).encode()).digest()
    roll = h[0] / 255
    rarity = ("Legendary" if roll > 0.95 else "Epic" if roll > 0.8
              else "Rare" if roll > 0.5 else "Common")
    pixel = [8, 12, 16, 24, 32][h[1] % 5]
    return rarity, pixel, h.hex()


def load_font(size):
    for name in ("DejaVuSans-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def render_card(img, obj, token_id, rarity, pixel):
    bg, accent = PALETTES[rarity]
    card = Image.new("RGB", (CARD_W, CARD_H), bg)
    d = ImageDraw.Draw(card)

    # Pixelate: shrink then upscale with nearest-neighbour.
    art = ImageOps.fit(img.convert("RGB"), (ART_BOX, ART_BOX))
    small = art.resize((ART_BOX // pixel, ART_BOX // pixel), Image.BILINEAR)
    small = small.quantize(colors=32).convert("RGB")
    art = small.resize((ART_BOX, ART_BOX), Image.NEAREST)

    x0 = (CARD_W - ART_BOX) // 2
    d.rectangle([x0 - 6, 34, x0 + ART_BOX + 5, 40 + ART_BOX + 5], fill=accent)
    card.paste(art, (x0, 40))

    title = (obj.get("title") or "Untitled")[:38]
    artist = ", ".join(p["name"] for p in obj.get("people") or [])[:45] or "Unknown artist"
    d.text((x0, 590), title, font=load_font(26), fill=(255, 255, 255))
    d.text((x0, 628), artist, font=load_font(18), fill=accent)
    d.text((x0, 656), obj.get("dated") or "", font=load_font(16), fill=(200, 200, 200))
    d.text((x0, 740), f"#{token_id:04d}", font=load_font(28), fill=accent)
    d.text((CARD_W - x0 - 160, 748), rarity.upper(), font=load_font(20), fill=accent)
    d.rectangle([2, 2, CARD_W - 3, CARD_H - 3], outline=accent, width=4)
    return card


def build_metadata(obj, token_id, rarity, pixel, digest, image_uri):
    attrs = [
        {"trait_type": "Rarity", "value": rarity},
        {"trait_type": "Pixel Size", "value": pixel},
        {"trait_type": "Classification", "value": obj.get("classification")},
        {"trait_type": "Culture", "value": obj.get("culture")},
        {"trait_type": "Century", "value": obj.get("century")},
        {"trait_type": "Medium", "value": obj.get("medium")},
    ]
    return {
        "name": f"{obj.get('title') or 'Untitled'} #{token_id}",
        "description": f"Pixel tribute to Harvard Art Museums object "
                       f"{obj['objectid']}. Original: {obj.get('url')}",
        "image": image_uri,
        "external_url": obj.get("url"),
        "attributes": [a for a in attrs if a["value"] not in (None, "")],
        "source": {"museum": "Harvard Art Museums", "object_id": obj["objectid"],
                   "fingerprint": digest},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=10)
    ap.add_argument("--classification", help="e.g. Paintings, Prints, Photographs")
    ap.add_argument("--out", default="output")
    ap.add_argument("--image-base-uri", default="ipfs://REPLACE_ME/",
                    help="Prefix used for the 'image' field in metadata")
    args = ap.parse_args()

    api_key = os.environ.get("HARVARD_API_KEY")
    if not api_key:
        raise SystemExit("Set the HARVARD_API_KEY environment variable.")

    out = Path(args.out)
    (out / "images").mkdir(parents=True, exist_ok=True)
    (out / "metadata").mkdir(parents=True, exist_ok=True)

    # Over-fetch since some records lack usable images.
    objs = fetch_objects(api_key, min(args.count * 3, 100), args.classification)[:args.count]
    print(f"Fetched {len(objs)} objects with images")
    token_id = 0
    for obj in objs:
        try:
            resp = requests.get(obj["primaryimageurl"] + "?width=800", timeout=60)
            resp.raise_for_status()
            img = Image.open(io.BytesIO(resp.content))
        except Exception as e:
            print(f"  skip {obj['objectid']}: {e}")
            continue
        token_id += 1
        rarity, pixel, digest = traits_for(obj)
        render_card(img, obj, token_id, rarity, pixel).save(out / "images" / f"{token_id}.png")
        meta = build_metadata(obj, token_id, rarity, pixel, digest,
                              f"{args.image_base_uri}{token_id}.png")
        (out / "metadata" / f"{token_id}.json").write_text(json.dumps(meta, indent=2))
        print(f"  #{token_id} [{rarity}] {obj.get('title')}")

    if token_id == 0:
        raise SystemExit("No cards were generated - see messages above.")


if __name__ == "__main__":
    main()
