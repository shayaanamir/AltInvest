"""
main.py

Standalone entry point for the sentiment engine.
Run this to execute the full pipeline for one or all assets.

Usage:
    python main.py --asset btc
    python main.py --asset eth
    python main.py --asset all
    python main.py --asset btc --no-save     (skip MongoDB write)
    python main.py --asset btc --mock-cmc    (use neutral CMC signals if API key missing)
"""

from __future__ import annotations

import argparse
import json
import sys
import os

# Make sure imports resolve from project root
sys.path.insert(0, os.path.dirname(__file__))

from aggregator.sentiment_aggregator import run_pipeline
from storage.mongo_handler import (
    get_sentiment_history,
    save_sentiment,
    save_raw_articles,
)
from collectors.rss_collector import fetch_articles_for_asset
from nlp.finbert_scorer import warmup_pipeline
from utils.config import ASSETS
from utils.logger import get_logger

logger = get_logger("main")


def run_asset(asset_id: str, save: bool = True) -> dict:
    """
    Runs the full sentiment pipeline for a single asset.

    Args:
        asset_id: e.g. "btc"
        save:     If True, persists results to MongoDB

    Returns:
        The sentiment output dict.
    """
    logger.info(f"Starting pipeline for: {asset_id.upper()}")

    # Load trend history from MongoDB (empty list if DB unavailable)
    history = get_sentiment_history(asset_id, days=1)

    # Run the main pipeline (returns output and raw_articles if return_raw_articles=True)
    result, raw_articles = run_pipeline(asset_id, history=history, return_raw_articles=True)

    # Save to MongoDB
    if save:
        save_sentiment(result)
        save_raw_articles(raw_articles, asset_id)

    # Pretty-print to console
    print(f"\n{'═'*60}")
    print(f"  Sentiment result for {asset_id.upper()}")
    print(f"{'═'*60}")
    print(json.dumps(result, indent=2))
    print(f"{'═'*60}\n")

    return result


def main():
    parser = argparse.ArgumentParser(
        description="AltInvest Sentiment Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --asset btc
  python main.py --asset all
  python main.py --asset eth --no-save
        """
    )
    parser.add_argument(
        "--asset",
        type=str,
        default="btc",
        help=f"Asset to analyse. One of: {list(ASSETS.keys())} or 'all'",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Skip MongoDB write (useful for testing without a DB connection)",
    )

    args = parser.parse_args()
    asset  = args.asset.lower()
    save   = not args.no_save

    # ── Warm up FinBERT/PyTorch once before any pipeline runs ─────────────────
    # The model is cached at module level in finbert_scorer.py, so it loads
    # exactly once here and is reused for every subsequent asset in this process.
    # When running --asset all, this saves N-1 model load cycles.
    logger.info("Warming up NLP models (loads once, reused for all assets)...")
    warmup_pipeline()

    if asset == "all":
        results = {}
        for asset_id in ASSETS:
            results[asset_id] = run_asset(asset_id, save=save)
        print(f"\n✓ Completed pipeline for {len(results)} assets.")
    elif asset in ASSETS:
        run_asset(asset, save=save)
    else:
        print(f"Error: Unknown asset '{asset}'. Must be one of {list(ASSETS.keys())} or 'all'")
        sys.exit(1)


if __name__ == "__main__":
    main()