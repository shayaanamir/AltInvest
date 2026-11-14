"""Performance scorecard (Phase 6d): one place that shows how every model did, read from the existing reports.

    python -m ml.evaluation.scorecard          (from the repo root)

Reads ONLY ml/reports/{asset}/walkforward_{risk,price,direction}.json, backtest.json, power_check.json and the
Phase 9 reports (walkforward_{price_v2,range,risk_v2,direction_v2}.json, test_final.json), the D82 audit
(ml/reports/d49_audit_risk.json) and the Phase 10 NFT reports (ml/reports/nft/walkforward_risk.json,
walkforward_fair_value.json, sealed_fair_value.json); trains nothing and reads
no data (AGENTS rules 5, 8). Writes ml/reports/scorecard.json and ml/reports/SCORECARD.md, both generated, never
hand-typed. Every number is copied from a source report; `gain` is the paired difference signed so that > 0 means
the model beat its baseline (D25, D28, D31, D44). Served comes from config and D33, D35, D36, D82.
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
    "risk": "not served: persistence vol_30d is served (D27, D82)",
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


PHASE9 = {  # part -> (report, metric label, model field, baseline field)
    "price": ("walkforward_price_v2", "MAE of h-day return", "model_mae", "baseline_mae"),
    "range": ("walkforward_range", "interval score", "model_interval_score", "baseline_interval_score"),
    "risk": ("walkforward_risk_v2", "QLIKE", "model_qlike", "baseline_qlike"),
    "direction": ("walkforward_direction_v2", "log loss", "model_log_loss", "baseline_log_loss"),
}


def phase9_served(part: str, model: str, horizon: int) -> bool:
    """D51: only EWMA risk at h = 30 was served; D82 withdrew it (top-only, D81), so today nothing in this table is
    served (RISK_MODEL_SERVED is False); range, price and direction keep their baselines."""
    return part == "risk" and model == "ewma" and horizon == config.HORIZON_DAYS and config.RISK_MODEL_SERVED


AUDIT = REPORTS / "d49_audit_risk.json"


def approved_top_only(asset: str, part: str, v: dict) -> bool:
    """D81/D82: a Phase 9 approval under top-only selection, from the D82 audit of the logged results (risk and
    direction); price and range logged no approval, and top-only can only remove approvals."""
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))["results"][asset][part]
    if isinstance(audit, str):
        return bool(v["approved"])
    return audit[f"h{v['horizon']}"]["approved_top_only"] == v["model"]


def phase9_rows(asset: str) -> list[dict]:
    rows = []
    for part, (report, metric, mfield, bfield) in PHASE9.items():
        for v in _load(asset, report)["verdict_table"]:
            served = phase9_served(part, v["model"], v["horizon"])
            rows.append({"part": part, "horizon": v["horizon"], "model": v["model"], "best_config": v["best_config"],
                         "metric": metric, "model_value": v[mfield], "baseline": v["baseline"],
                         "baseline_value": v[bfield], "gain_ci95": _ci(v["paired_ci"]), "approved": v["approved"],
                         "approved_top_only": approved_top_only(asset, part, v), "served": served, "source": f"ml/reports/{asset}/{report}.json"})
    return rows


def sealed_test(asset: str) -> dict:
    t = _load(asset, "test_final")
    return {"risk": {h: {k: r[k] for k in ("qlike_ewma", "qlike_persistence", "not_worse")}
                     | {"gain_ci95": _ci(r["paired_diff_persistence_minus_ewma"])} for h, r in t["risk"].items()},
            "range_h30": {k: t["range_h30"]["test"][k] for k in ("coverage", "lower_tail_miss", "upper_tail_miss")},
            "decision": t["decision"], "source": f"ml/reports/{asset}/test_final.json"}


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


def nft_section() -> dict:
    """Phase 10 NFT rows, copied from ml/reports/nft (D59, D65, D73, D77, D79, D80)."""
    nft = REPORTS / "nft"
    risk = json.loads((nft / "walkforward_risk.json").read_text(encoding="utf-8"))
    fv_wf = json.loads((nft / "walkforward_fair_value.json").read_text(encoding="utf-8"))["selection"]
    fv_s = json.loads((nft / "sealed_fair_value.json").read_text(encoding="utf-8"))
    rows = [{"part": "nft risk (pooled, h = 30)", "model": v["model"], "metric": "QLIKE", "model_value": v["model_qlike"],
             "baseline": v["baseline"], "baseline_value": v["baseline_qlike"], "gain_ci95": _ci(v["paired_ci"]),
             "approved": v["approved"], "served": False,
             "status": ("approved in 10.3, withdrawn by the D72 check (D73); under top-only GARCH ranks first and its "
                        "CI includes 0 (D65 i)") if v["approved"] else "not approved",
             "source": "ml/reports/nft/walkforward_risk.json"}
            for v in risk["verdict_table"] if v["scope"].startswith("pooled")]
    v = fv_wf["verdict"]
    rows.append({"part": "nft fair value (walk-forward)", "model": v["top_candidate"], "metric": "MdAPE on price",
                 "model_value": v["model_mdape"], "baseline": v["baseline"], "baseline_value": v["baseline_mdape"],
                 "gain_ci95": _ci(v["paired_diff_baseline_minus_model"]), "approved": v["approved"], "served": True,
                 "status": "approved (D77); served for 6 collections, B2 for lilpudgys (D78, D80); no range",
                 "source": "ml/reports/nft/walkforward_fair_value.json"})
    s = fv_s["verdict"]
    best = s["best_baseline"]
    rows.append({"part": "nft fair value (sealed test, once)", "model": "served setup", "metric": "MdAPE on price",
                 "model_value": s["mdape"]["served"], "baseline": best, "baseline_value": s["mdape"][best],
                 "gain_ci95": _ci(s["paired_diff_best_baseline_minus_served"]), "approved": s["pass"], "served": True,
                 "status": "PASS (D79): the serving rule stays", "source": "ml/reports/nft/sealed_fair_value.json"})
    return {"rows": rows, "served_risk": "persistence vol_30d (D73)",
            "served_fair_value": "monthly refit of fv_pooled_l1_nl15 (D83); B2 for lilpudgys (D80)"}


def build(assets=config.ASSETS) -> dict:
    out = {"assets": {}}
    for a in assets:
        models = {m: model_row(a, m) for m in MODELS}
        bt = backtest_rows(a)
        power = _load(a, "power_check")
        out["assets"][a] = {"verdict": verdict(a, models, bt), "models": models, "backtest": bt,
                            "power_note": power["note"], "phase9": phase9_rows(a), "sealed_test": sealed_test(a)}
    out["nft"] = nft_section()
    out["summary"] = {
        "models_approved": sum(r["approved"] for x in out["assets"].values() for r in x["models"].values()),
        "models_served": sum(r["served"] for x in out["assets"].values() for r in x["models"].values()),
        "models_total": len(assets) * len(MODELS),
        "phase9_approved": sum(r["approved"] for x in out["assets"].values() for r in x["phase9"]),
        "phase9_approved_top_only": sum(r["approved_top_only"] for x in out["assets"].values() for r in x["phase9"]),
        "phase9_served": sum(r["served"] for x in out["assets"].values() for r in x["phase9"]),
        "phase9_rows": sum(len(x["phase9"]) for x in out["assets"].values()),
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


def _approved(r: dict) -> str:
    if r["approved"] and not r["approved_top_only"]:
        return "withdrawn (D82)"
    return "yes" if r["approved"] else "no"


def markdown(card: dict) -> str:
    s = card["summary"]
    lines = ["# SCORECARD (generated by `python -m ml.evaluation.scorecard`; do not edit)", "",
             f"Generated {card['metadata']['generated_at']} at commit `{card['metadata']['git_commit']}`. "
             f"Models approved: {s['models_approved']} of {s['models_total']}; served: {s['models_served']}. "
             f"Phase 9 rows approved as logged (per model type, D49): {s['phase9_approved']} of {s['phase9_rows']}; "
             f"under top-only selection (D81): {s['phase9_approved_top_only']} (D82 audit, "
             f"ml/reports/d49_audit_risk.json); served: {s['phase9_served']}. Crypto risk serves persistence vol_30d "
             "(D82).", "",
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
        lines += ["", f"Power: {x['power_note']}", "", f"### {a.upper()} Phase 9 (walk-forward, last 40% of folds)", "",
                  "| Part | h | Model | Best config | Metric | Model | Baseline | Gain [95% CI] | Approved | Served |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
        for r in x["phase9"]:
            g = r["gain_ci95"]
            lines.append(f"| {r['part']} | {r['horizon']} | {r['model']} | {r['best_config']} | {r['metric']} | "
                         f"{_f(r['model_value'])} | {_f(r['baseline_value'])} ({r['baseline']}) | {_f(g['estimate'])} "
                         f"[{_f(g['low'])}, {_f(g['high'])}] | {_approved(r)} | "
                         f"{'yes' if r['served'] else 'no'} |")
        st = x["sealed_test"]
        lines += ["", "Sealed test (D50): " + "; ".join(
            f"risk {h}: QLIKE EWMA {_f(r['qlike_ewma'])} vs persistence {_f(r['qlike_persistence'])}, gain "
            f"{_f(r['gain_ci95']['estimate'])} [{_f(r['gain_ci95']['low'])}, {_f(r['gain_ci95']['high'])}]"
            for h, r in st["risk"].items()) + f"; vol_30d band coverage {_f(st['range_h30']['coverage'])}.", ""]
    n = card["nft"]
    lines += ["## NFT collections (Phase 10)", "",
              f"Served: risk = {n['served_risk']}; item value = {n['served_fair_value']}.", "",
              "| Part | Model | Metric | Model | Baseline | Gain [95% CI] | Approved | Served | Status |",
              "|---|---|---|---|---|---|---|---|---|"]
    for r in n["rows"]:
        g = r["gain_ci95"]
        lines.append(f"| {r['part']} | {r['model']} | {r['metric']} | {_f(r['model_value'])} | "
                     f"{_f(r['baseline_value'])} ({r['baseline']}) | {_f(g['estimate'])} [{_f(g['low'])}, "
                     f"{_f(g['high'])}] | {'yes' if r['approved'] else 'no'} | {'yes' if r['served'] else 'no'} | "
                     f"{r['status']} |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    require_snapshot()                                  # D40: evaluation snapshot only
    card = build()
    OUT_JSON.write_text(json.dumps(card, indent=2), encoding="utf-8")
    OUT_MD.write_text(markdown(card), encoding="utf-8")
    print(f"wrote {OUT_JSON}\nwrote {OUT_MD}")


if __name__ == "__main__":
    main()
