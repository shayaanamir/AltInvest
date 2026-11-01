"""Performance scorecard (Phase 6d): one place that shows how every model did, read from the existing reports.

    python -m ml.evaluation.scorecard          (from the repo root)

Reads ONLY ml/reports/{asset}/walkforward_{risk,price,direction}.json, backtest.json and power_check.json; trains
nothing and reads no data (AGENTS rules 5, 8). Writes ml/reports/scorecard.json and ml/reports/SCORECARD.md, both
generated, never hand-typed. Every number is copied from a source report; `gain` is the paired difference signed so
that > 0 means the model beat its baseline (D25, D28, D31). Served comes from config and D27, D33, D35, D36.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from ml import config
from ml.data.snapshot_guard import require_snapshot
from ml.gitinfo import git_metadata

REPORTS = Path(__file__).resolve().parent.parent / "reports"
OUT_JSON = REPORTS / "scorecard.json"
OUT_MD = REPORTS / "SCORECARD.md"

# model -> (report, metric name, model field, baseline name, baseline field, paired-diff field, higher is better)
MODELS = {
    "risk": ("walkforward_risk", "Spearman (rank of 30-day vol)", "spearman_top", "persistence",
             "spearman_persistence", "paired_diff_spearman_top_minus_persistence", True),
    "price": ("walkforward_price", "MAE of 30-day return", "mae_return_top", "last-value (no change)",
              "mae_return_last_value", "paired_diff_mae_last_value_minus_top", False),
    "direction": ("walkforward_direction", "log loss (UP/DOWN/FLAT)", "logloss_top", "class frequencies (prior)",
                  "logloss_prior", "paired_diff_logloss_prior_minus_top", False),
}
SERVED_REASON = {
    "risk": "not served: persistence vol_30d is served instead (D27, D36)",
    "price": "not served: the last-value baseline (0%) is served instead (D35)",
    "direction": "not served: signal UNCERTAIN, confidence null (D33)",
}
BACKTEST_ROWS = (("served", "strategies"), ("reference", "strategies"),
                 ("buy_and_hold", "baselines"), ("always_hold", "baselines"))
BACKTEST_FIELDS = ("mean_window_return", "mean_window_return_ci95", "cumulative_return", "max_drawdown",
                   "sharpe_annualised", "hit_rate", "trades")


def _load(asset: str, name: str) -> dict:
    return json.loads((REPORTS / asset / f"{name}.json").read_text(encoding="utf-8"))


def _ci(d: dict) -> dict:
    return {k: d[k] for k in ("estimate", "low", "high")}


def model_row(asset: str, model: str) -> dict:
    report, metric, mfield, bname, bfield, dfield, _ = MODELS[model]
    r = _load(asset, report)
    conf = r["confirmation_last_40pct"]
    served = model == "direction" and config.DIRECTION_SERVED[asset]
    return {
        "metric": metric, "top_config": r["verdict"]["top_config"],
        "model": conf[mfield], "baseline_name": bname, "baseline": conf[bfield],
        "gain_ci95": _ci(conf[dfield]),
        "n_effective": conf["n_effective"], "date_range": conf["date_range"],
        "approved": r["verdict"]["approved"], "rule": r["verdict"]["rule"],
        "served": served, "served_reason": "served" if served else SERVED_REASON[model],
        "source": f"ml/reports/{asset}/{report}.json",
    }


def backtest_rows(asset: str) -> dict:
    b = _load(asset, "backtest")
    rows = {name: {f: b[group][name].get(f) for f in BACKTEST_FIELDS} for name, group in BACKTEST_ROWS}
    for r in rows.values():
        r["mean_window_return_ci95"] = {k: r["mean_window_return_ci95"][k] for k in ("low", "high")}
    return {
        "n_windows": b["protocol"]["n_windows"],
        "window_dates": [b["protocol"]["first_window_date"], b["protocol"]["last_window_date"]],
        "rows": rows,
        "reference_config": b["protocol"]["reference_config"],
        "source": f"ml/reports/{asset}/backtest.json",
    }


def verdict(asset: str, models: dict, bt: dict) -> str:
    """One plain-English sentence per asset, built only from the fields above."""
    beat = [m for m, r in models.items() if r["approved"]]
    lost = [m for m, r in models.items() if not r["approved"]]
    served = [m for m, r in models.items() if r["served"]]
    parts = []
    if beat:
        parts.append(f"{' and '.join(beat)} beat its baseline in walk-forward"
                     + ("" if set(beat) <= set(served) else " but is not served"))
    if lost:
        parts.append(f"{' and '.join(lost) if len(lost) < 3 else ', '.join(lost[:-1]) + ' and ' + lost[-1]} "
                     "did not beat the baseline")
    s = bt["rows"]["served"]
    bh = bt["rows"]["buy_and_hold"]
    parts.append(f"the served signal made {s['trades']} trades over {bt['n_windows']} windows "
                 f"({s['mean_window_return']:+.2%} per 30-day window vs buy-and-hold {bh['mean_window_return']:+.2%})")
    return f"{asset.upper()}: " + "; ".join(parts) + "."


def build(assets=config.ASSETS) -> dict:
    out = {"assets": {}}
    for a in assets:
        models = {m: model_row(a, m) for m in MODELS}
        bt = backtest_rows(a)
        power = _load(a, "power_check")
        out["assets"][a] = {"verdict": verdict(a, models, bt), "models": models, "backtest": bt,
                            "power_note": power["note"]}
    out["summary"] = {
        "models_approved": sum(r["approved"] for x in out["assets"].values() for r in x["models"].values()),
        "models_served": sum(r["served"] for x in out["assets"].values() for r in x["models"].values()),
        "models_total": len(assets) * len(MODELS),
    }
    out["metadata"] = {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                       **git_metadata(),
                       "sources": sorted({r["source"] for x in out["assets"].values() for r in x["models"].values()}
                                         | {x["backtest"]["source"] for x in out["assets"].values()}),
                       "note": "Copied from the reports; nothing recomputed. Last 40% of walk-forward folds (D25)."}
    return out


def _f(x, pct=False) -> str:
    if x is None:
        return "n/a"
    return f"{x:+.2%}" if pct else f"{x:.4f}"


def markdown(card: dict) -> str:
    s = card["summary"]
    lines = ["# SCORECARD (generated by `python -m ml.evaluation.scorecard`; do not edit)", "",
             f"Generated {card['metadata']['generated_at']} at commit `{card['metadata']['git_commit']}`. "
             f"Models approved: {s['models_approved']} of {s['models_total']}; served: {s['models_served']}.", "",
             "Gain = paired 95% CI of (baseline - model) for losses, (model - baseline) for Spearman: "
             "> 0 means the model is better. Approved only if the whole CI is above 0.", ""]
    for a, x in card["assets"].items():
        lines += [f"## {a.upper()}", "", x["verdict"], "",
                  "| Model | Metric | Top config | Model | Baseline | Gain [95% CI] | n_eff | Approved | Served |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for m, r in x["models"].items():
            g = r["gain_ci95"]
            lines.append(f"| {m} | {r['metric']} | {r['top_config']} | {_f(r['model'])} | {_f(r['baseline'])} "
                         f"({r['baseline_name']}) | {_f(g['estimate'])} [{_f(g['low'])}, {_f(g['high'])}] | "
                         f"{r['n_effective']} | {'yes' if r['approved'] else 'no'} | "
                         f"{'yes' if r['served'] else r['served_reason']} |")
        bt = x["backtest"]
        lines += ["", f"Backtest: {bt['n_windows']} non-overlapping 30-day windows, "
                      f"{bt['window_dates'][0]} to {bt['window_dates'][1]} (D34; reference = {bt['reference_config']}, "
                      "evidence only, never served).", "",
                  "| Strategy | Mean / window [95% CI] | Cumulative | Max drawdown | Sharpe | Trades |",
                  "|---|---|---|---|---|---|"]
        for name, r in bt["rows"].items():
            ci = r["mean_window_return_ci95"]
            lines.append(f"| {name} | {_f(r['mean_window_return'], True)} [{_f(ci['low'], True)}, "
                         f"{_f(ci['high'], True)}] | {_f(r['cumulative_return'], True)} | "
                         f"{_f(r['max_drawdown'], True)} | {_f(r['sharpe_annualised'])} | "
                         f"{'n/a' if r['trades'] is None else r['trades']} |")
        lines += ["", f"Power: {x['power_note']}", ""]
    return "\n".join(lines)


def main() -> None:
    require_snapshot()                                  # D40: evaluation snapshot only
    card = build()
    OUT_JSON.write_text(json.dumps(card, indent=2), encoding="utf-8")
    OUT_MD.write_text(markdown(card), encoding="utf-8")
    print(f"wrote {OUT_JSON}\nwrote {OUT_MD}")


if __name__ == "__main__":
    main()
