# Harvard Art NFT Cards

Pulls public-domain artworks from the [Harvard Art Museums API](https://github.com/harvardartmuseums/api-docs) and renders each as a pixelated, rarity-framed collectible card with ERC-721-style metadata.

## Setup
1. Repo → Settings → Secrets and variables → Actions → **New repository secret** named `HARVARD_API_KEY`.
2. Actions tab → **Generate NFT cards** → Run workflow. Download the `nft-cards` artifact.

## Run locally
```bash
pip install -r requirements.txt
export HARVARD_API_KEY=your_key
python make_nfts.py --count 10 --classification Paintings
```
Output goes to `output/images/` and `output/metadata/`.
