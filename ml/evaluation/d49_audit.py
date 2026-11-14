"""D49 audit of the Phase 9 approvals under top-only selection (Phase 10 step 10.9, D81, D82). Nothing is re-run.

    python -m ml.evaluation.d49_audit        -> ml/reports/d49_audit_risk.json

D81 replaces D49's per-model-type confirmation with top-only selection (D25/D44). This reads the logged Phase 9
walk-forward results and applies top-only to them, per asset, part and horizon: every declared config of every
model type is ranked together by its pooled loss on the ranking folds (the first 60%); only the top-ranked config is
confirmed, with ITS logged confirmation verdict (paired moving-block bootstrap 95% CI of loss(baseline) - loss
(model) on the last 40%, D44): approved if the estimate is > 0 and the CI excludes 0. The model types were
evaluated on the same ranking rows (checked: same n_pooled, dates and baseline loss), so their logged ranking losses
are directly comparable and nothing needs re-running.

Parts with a logged approval are audited: risk (EWMA vs GARCH(1,1) Student-t, ml/reports/{asset}/
walkforward_risk_v2.json, h = 30 and 7) and direction (logistic regression vs LightGBM, walkforward_direction_v2.json,
h = 30). Price and range logged no approval, and top-only can only remove approvals, so they are listed as such.
The served approval being audited is D50/D51: EWMA risk for all assets, from the h = 30 walk-forward approvals.
"""

import json

from ml.data.validate import ML_ROOT

ASSETS = ("btc", "eth", "sol")
OUT = ML_ROOT / "reports" / "d49_audit_risk.json"
NO_APPROVAL_PARTS = {"price": "walkforward_price_v2", "range": "walkforward_range"}


def _load(asset: str, report: str) -> dict:
    return json.loads((ML_ROOT / "reports" / asset / f"{report}.json").read_text(encoding="utf-8"))


def top_only(models: dict, baseline: str, where: str) -> dict:
    """models: {model type: {ranking_first_60pct, confirmation_last_40pct, verdict}} as logged."""
    rank = {k: m["ranking_first_60pct"] for k, m in models.items()}
    first = next(iter(rank.values()))
    for k, r in rank.items():
        if (r["n_pooled"], r["date_range"], r["mean_loss"][baseline]) != \
                (first["n_pooled"], first["date_range"], first["mean_loss"][baseline]):
            raise ValueError(f"{where}: {k} was ranked on different rows; cannot audit from the logs")
    losses = {(k, c): loss for k, r in rank.items() for c, loss in r["mean_loss"].items() if c != baseline}
    top_type, top_cfg = min(losses, key=lambda k: losses[k])
    v = models[top_type]["verdict"]
    if v["top_config"] != top_cfg:
        raise ValueError(f"{where}: the logged confirmation is not of the top-ranked config")
    ci = v["paired_diff_baseline_minus_model"]
    approved = bool(ci["estimate"] > 0 and ci["low"] > 0)
    if approved != bool(v["approved"]):
        raise ValueError(f"{where}: logged verdict disagrees with the CI rule")
    return {"ranking_rows": first["n_pooled"], "ranking_dates": first["date_range"],
            "ranking_loss": {f"{k}:{c}": x for (k, c), x in losses.items()} | {baseline: first["mean_loss"][baseline]},
            "top_model": top_type, "top_config": top_cfg,
            "confirmation_dates": models[top_type]["confirmation_last_40pct"]["date_range"],
            "top_confirmation": {"model_loss": v["model_loss"], "baseline_loss": v["baseline_loss"], "paired_ci": ci},
            "approved_top_only": top_type if approved else None,
            "approved_d49_per_model_type": [k for k, m in models.items() if m["verdict"]["approved"]]}


def audit() -> dict:
    results, sources = {}, {}
    for a in ASSETS:
        risk, direc = _load(a, "walkforward_risk_v2"), _load(a, "walkforward_direction_v2")
        sources[a] = {"risk": f"ml/reports/{a}/walkforward_risk_v2.json",
                      "risk_git_commit": risk["horizons"]["h30"]["metadata"]["git_commit"],
                      "direction": f"ml/reports/{a}/walkforward_direction_v2.json",
                      "direction_git_commit": direc["metadata"].get("git_commit")}
        results[a] = {"risk": {h: top_only(risk["horizons"][h]["models"], "persistence_vol30", f"{a} risk {h}")
                               for h in ("h30", "h7")},
                      "direction": {"h30": top_only(direc["models"], "prior", f"{a} direction h30")}}
        for part, rep in NO_APPROVAL_PARTS.items():
            if any(v["approved"] for v in _load(a, rep)["verdict_table"]):
                raise ValueError(f"{a} {part}: a logged approval exists; extend the audit")
            results[a][part] = "no approval logged; top-only can only remove approvals"
    ewma_h30 = {a: results[a]["risk"]["h30"]["approved_top_only"] == "ewma" for a in ASSETS}
    matches = all(ewma_h30.values())
    return {"decision": "D82 (audit under D81)", "sources": sources,
            "rule": __doc__.strip().split("\n\n")[1].replace("\n", " "),
            "results": results, "ewma_approved_top_only_h30": ewma_h30, "matches_current_approval": matches,
            "outcome": ("EWMA approval stands (D50/D51 unchanged)" if matches else
                        "EWMA approval WITHDRAWN: no Phase 9 risk config is approved under top-only; crypto risk "
                        "serves persistence vol_30d and the cone uses it (D82)"),
            "direction_note": "Direction serving is unchanged either way (D33: signal UNCERTAIN; the ETH logistic "
                              "regression is closed, D50)."}


def main() -> None:
    out = audit()
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    for a, parts in out["results"].items():
        for part in ("risk", "direction"):
            for h, r in parts[part].items():
                ci = r["top_confirmation"]["paired_ci"]
                print(f"{a} {part} {h}: top {r['top_model']}:{r['top_config']} (ranking {r['ranking_loss']}); "
                      f"CI {ci['estimate']:.4f} [{ci['low']:.4f}, {ci['high']:.4f}] -> {r['approved_top_only']}; "
                      f"D49 approved {r['approved_d49_per_model_type']}")
    print(out["outcome"])


if __name__ == "__main__":
    main()
