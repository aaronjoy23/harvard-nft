# Harvard Art NFT Studio

A gallery of artworks from the [Harvard Art Museums API](https://github.com/harvardartmuseums/api-docs). Pick one to turn it into a pixelated, rarity-framed collectible card, then download the PNG and ERC-721-style metadata JSON.

## Setup (one time)
1. **Settings → Secrets and variables → Actions → New repository secret**, named `HARVARD_API_KEY`.
2. **Settings → Pages → Build and deployment → Source: GitHub Actions**.

## Use it
1. **Actions → Build gallery → Run workflow** (optionally set a count or classification such as `Paintings`).
2. Open `https://<your-username>.github.io/harvard-nft/`, click an artwork, adjust rarity / pixel size / token number, and download.

The API key is only used inside the workflow; the published site contains just the images and artwork info.

## Run locally
```bash
pip install -r requirements.txt
export HARVARD_API_KEY=your_key
python fetch_gallery.py --count 48
cd site && python -m http.server 8000   # open http://localhost:8000
```

`make_nfts.py` is the older batch script that renders cards for random artworks without the gallery.
