"""
nft_sentiment/compare.py

Scorer agreement report on live NFT headlines. There are no human labels, so this measures AGREEMENT,
not accuracy:

  llm_self      the LLM run twice on the same articles (cache cleared in between): how stable its
                labels, relevance calls and scores are from one run to the next
  llm_vs_finbert  the LLM against the crypto pipeline's VADER + FinBERT ensemble, on the articles the
                LLM judged relevant (the ones the pipeline actually uses)

Labels: the LLM's label; for the ensemble, positive above +0.1, negative below -0.1 (the crypto
pipeline's sentiment_distribution thresholds).

Run from sentiment_engine/ (costs two Groq calls per collection with news, loads FinBERT):
    python -m nft_sentiment.compare [--out data/reports/nft_scorer_agreement.json]
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nft_sentiment import config as cfg  # noqa: E402
from nft_sentiment import groq_scorer  # noqa: E402
from nft_sentiment.collector import collect  # noqa: E402

LABELS = ("positive", "neutral", "negative")


def ensemble_label(score: float) -> str:
    return "positive" if score > 0.1 else "negative" if score < -0.1 else "neutral"


def cohen_kappa(a: list[str], b: list[str]) -> float | None:
    n = len(a)
    if n == 0:
        return None
    observed = sum(x == y for x, y in zip(a, b)) / n
    expected = sum((a.count(lab) / n) * (b.count(lab) / n) for lab in LABELS)
    return None if expected == 1 else round((observed - expected) / (1 - expected), 3)


def pearson(x: list[float], y: list[float]) -> float | None:
    n = len(x)
    if n < 3:
        return None
    mx, my = sum(x) / n, sum(y) / n
    sx = math.sqrt(sum((v - mx) ** 2 for v in x))
    sy = math.sqrt(sum((v - my) ** 2 for v in y))
    if sx == 0 or sy == 0:
        return None
    return round(sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy), 3)


def confusion(a: list[str], b: list[str]) -> dict:
    return {ra: {rb: sum(1 for x, y in zip(a, b) if x == ra and y == rb) for rb in LABELS} for ra in LABELS}


def agreement(a: list[str], b: list[str]) -> dict:
    n = len(a)
    return {
        "n": n,
        "label_agreement": round(sum(x == y for x, y in zip(a, b)) / n, 3) if n else None,
        "cohen_kappa": cohen_kappa(a, b),
        "confusion_rows_first_cols_second": confusion(a, b),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", default=os.path.join("data", "reports", "nft_scorer_agreement.json"))
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if not groq_scorer.is_configured():
        sys.exit("GROQ_API_KEY is not set")

    from nlp.ensemble_scorer import score_articles as ensemble_score

    articles = collect()
    rows = []
    for target, items in articles.items():
        items = sorted(items, key=lambda a: a["age_hours"])[: cfg.NFT_MAX_ARTICLES_SCORED]
        if not items:
            continue
        name = cfg.NFT_MARKET["name"] if target == cfg.NFT_MARKET_ID else cfg.NFT_COLLECTIONS[target]["name"]
        groq_scorer.clear_cache()
        run_a, _ = groq_scorer.score_articles(target, name, items)
        groq_scorer.clear_cache()
        run_b, _ = groq_scorer.score_articles(target, name, items)
        ens = ensemble_score(items)
        by_title = lambda xs: {x["title"]: x for x in xs}  # noqa: E731
        a_map, b_map, e_map = by_title(run_a), by_title(run_b), by_title(ens)
        for it in items:
            a, b, e = a_map.get(it["title"]), b_map.get(it["title"]), e_map.get(it["title"])
            if a and b and e:
                rows.append({
                    "target": target, "title": it["title"], "source": it["source"],
                    "llm_a": {"relevant": a["relevant"], "label": a["llm_label"], "score": a["nlp_score"]},
                    "llm_b": {"relevant": b["relevant"], "label": b["llm_label"], "score": b["nlp_score"]},
                    "ensemble": {"score": round(e["nlp_score"], 4), "label": ensemble_label(e["nlp_score"]),
                                 "models": e.get("nlp_models")},
                })

    relevant = [r for r in rows if r["llm_a"]["relevant"]]
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": cfg.model_name(),
        "note": "Agreement between scorers on live headlines, NOT accuracy: there are no human labels.",
        "articles_scored": len(rows),
        "llm_self": {
            "relevance_agreement": round(sum(r["llm_a"]["relevant"] == r["llm_b"]["relevant"] for r in rows) / len(rows), 3) if rows else None,
            **agreement([r["llm_a"]["label"] for r in rows], [r["llm_b"]["label"] for r in rows]),
            "score_mean_abs_diff": round(sum(abs(r["llm_a"]["score"] - r["llm_b"]["score"]) for r in rows) / len(rows), 3) if rows else None,
        },
        "llm_vs_finbert_on_relevant": {
            **agreement([r["llm_a"]["label"] for r in relevant], [r["ensemble"]["label"] for r in relevant]),
            "score_pearson": pearson([r["llm_a"]["score"] for r in relevant], [r["ensemble"]["score"] for r in relevant]),
        },
        "rows": rows,
    }
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    summary = {k: v for k, v in report.items() if k != "rows"}
    print(json.dumps(summary, indent=2))
    print(f"\nwritten to {args.out}")


if __name__ == "__main__":
    main()
