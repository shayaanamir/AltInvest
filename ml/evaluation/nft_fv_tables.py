"""Markdown tables for checkpoint 10.6, generated from ml/reports/nft/walkforward_fair_value.json (no hand-typed numbers).

    python -m ml.evaluation.nft_fv_tables     (writes ml/docs/phase10/logs/10.6_tables.md)
"""

import json

from ml.data.validate import ML_ROOT
from ml.evaluation.run_nft_fair_value import REPORT

OUT = ML_ROOT / "docs" / "phase10" / "logs" / "10.6_tables.md"


def _f(x, d=4):
    return "" if x is None else f"{x:.{d}f}" if isinstance(x, float) else str(x)


def _ci(c):
    return "n/a" if not c else f"{c['estimate']:.4f} [{c['low']:.4f}, {c['high']:.4f}]"


def _table(head, rows):
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
                     + ["| " + " | ".join(map(str, r)) + " |" for r in rows])


def _by(block: dict, names: list) -> str:
    return _table(["group", "n"] + names, [[k, v["n"]] + [_f(v[n]) for n in names] for k, v in block.items()])


def render(r: dict) -> str:
    s = r["selection"]
    rank, conf, v, rg = s["ranking_first_60pct"], s["confirmation_last_40pct"], s["verdict"], s["range"]
    bases = r["baselines"]
    cands = rank["order"]
    names = bases + cands
    out = [f"Generated from {REPORT.name}: git {r['git_commit'][:7]} dirty {r['git_dirty']}, trial count "
           f"{r['trial_count']}, test rows {r['data']['test_rows_pooled']}, test dates {r['data']['test_date_range']}",
           "", "## Folds", _table(["fold", "part", "train cutoff", "test", "n_train", "n_test", "seconds"],
                                  [[f["fold"], f["part"], f["train_cutoff"], " to ".join(f["test"]), f["n_train"],
                                    f["n_test"], f["seconds"]] for f in r["folds"]]),
           "", f"## Ranking (first 60%: {rank['n_rows']} rows, {rank['n_dates']} dates) and confirmation "
               f"(last 40%: {conf['n_rows']} rows, {conf['n_dates']} dates; reported for all, tested only for the top)",
           _table(["name", "kind", "ranking MdAPE", "rank", "confirmation MdAPE"],
                  [[n, "baseline" if n in bases else "candidate", _f(rank["mdape"][n]),
                    cands.index(n) + 1 if n in cands else "", _f(conf["mdape"][n])] for n in names]),
           "", f"Better baseline on the ranking folds: {rank['best_baseline']}", "",
           "## Verdict (top candidate only)",
           _table(["top candidate", "baseline (best on confirmation)", "model MdAPE", "baseline MdAPE",
                   "paired diff baseline - model [95% CI]", "CI ok", "D32 ok", "approved"],
                  [[v["top_candidate"], v["baseline"], _f(v["model_mdape"]), _f(v["baseline_mdape"]),
                    _ci(v["paired_diff_baseline_minus_model"]), v["ci_excludes_0_positive"],
                    v["beats_better_baseline_on_ranking_folds_D32"], v["approved"]]]),
           "", "## Range on the confirmation folds",
           _table(["name", "coverage", "lower miss", "upper miss", "mean width", "interval score", "crossed",
                   "in band", "tails ok"],
                  [[n, _f(x["coverage"]), _f(x["lower_tail_miss"]), _f(x["upper_tail_miss"]), _f(x["mean_width"]),
                    _f(x["mean_interval_score"]), x["n_crossed"], x["coverage_in_bounds"], x["tails_within_max"]]
                   for n, x in rg["confirmation"].items()]),
           "", f"Baseline range to beat: {rg['baseline_range_to_beat']}; interval-score diff baseline - model: "
               f"{_ci(rg['paired_interval_score_diff_baseline_minus_model'])}; range approved {rg['approved']}; "
               f"fallback baseline range in band {rg['fallback_baseline_range_in_band']}; served range (pooled) "
               f"{rg['served_range_pooled']}", "",
           "## Per collection, confirmation folds",
           _table(["collection", "n", f"{v['top_candidate']} MdAPE"] + [f"{b} MdAPE" for b in bases]
                  + ["best baseline", "model <= best", "serve point", "serve range"]
                  + [f"{n} coverage" for n in [v["top_candidate"]] + bases],
                  [[k, x["n"], _f(x["mdape"][v["top_candidate"]])] + [_f(x["mdape"][b]) for b in bases]
                   + [x["best_baseline"], x["model_not_worse_than_best_baseline"], x.get("serve_point", "(not approved)"),
                      x.get("serve_range", "(not approved)")]
                   + [_f(x["coverage"][n]) for n in [v["top_candidate"]] + bases]
                   for k, x in s["per_collection"].items()])]
    d = r["descriptive"]
    for part in ("confirmation", "ranking", "all_folds"):
        for key in ("by_collection", "by_sale_type", "by_floor_age_bucket"):
            out += ["", f"## Descriptive MdAPE, {part}, {key} (not used for selection)", _by(d[part][key], names)]
    out += ["", "## Descriptive MdAPE by fold", _by(d["by_fold"], names)]
    top = v["top_candidate"]
    imp = r["feature_importance_gain_share_mean_over_folds"][top]
    out += ["", f"## Feature importance of {top} (gain share, mean over folds, top 25)",
            _table(["feature", "gain share"], [[k, _f(x)] for k, x in imp.items()])]
    return "\n".join(out) + "\n"


def main() -> None:
    r = json.loads(REPORT.read_text(encoding="utf-8"))
    OUT.write_text(render(r), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
