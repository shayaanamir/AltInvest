"""
nft_sentiment/run.py

Dry run of the NFT sentiment pipeline from the command line: fetches the feeds, scores and prints the
readings. Nothing is saved, and no market signal is used (that comes from the backend's database).

Run from sentiment_engine/:
    python -m nft_sentiment.run                      # every collection and the NFT market
    python -m nft_sentiment.run --slug azuki milady
    python -m nft_sentiment.run --collect-only       # just show which headlines matched
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nft_sentiment import config as cfg  # noqa: E402
from nft_sentiment.aggregator import ScoringUnavailable, run_collection_pipeline  # noqa: E402
from nft_sentiment.collector import collect  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="NFT sentiment dry run (nothing is saved)")
    parser.add_argument("--slug", nargs="*", help=f"collections to run (default: all of {list(cfg.NFT_COLLECTIONS)})")
    parser.add_argument("--no-market", action="store_true", help="leave out the NFT market pseudo-collection")
    parser.add_argument("--collect-only", action="store_true", help="print matched headlines, do not score")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # Windows consoles default to cp1252

    articles = collect(args.slug, include_market=not args.no_market)

    for target_id, items in articles.items():
        name = cfg.NFT_MARKET["name"] if target_id == cfg.NFT_MARKET_ID else cfg.NFT_COLLECTIONS[target_id]["name"]
        print(f"\n=== {name} ({target_id}): {len(items)} articles ===")
        if args.collect_only:
            for a in items:
                print(f"  [{a['age_hours']:6.1f}h] {a['source']}: {a['title']}")
            continue
        try:
            result = run_collection_pipeline(target_id, name, items)
        except ScoringUnavailable as exc:
            print(f"  scoring unavailable: {exc}")
            continue
        print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
