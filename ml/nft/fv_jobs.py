"""Jobs that run after each NFT refresh in the ml-nft-refresh sidecar (Phase 10 step 10.9).

- refit (D83): on the first refresh of a calendar month without a refit (normally the 1st), ml.nft.fv_refit.refit;
  whether one is due is read from the refit log on the data volume only (config.NFT_FV_REFIT_DIR, 10.9b);
- record (D85): log today's served item estimates (ml.nft.live_accuracy.record);
- summarize (D85): write the monthly summary of every settled month that has none yet.
Each job runs on its own: a failure is reported in fv_jobs_status.json (ML_NFT_DIR) and never stops the refresh or
serving. Monitoring only: no job changes config.NFT_FV_SERVE or switches a method.
"""

import json
from datetime import datetime, timezone

from ml import config
from ml.nft import fv_refit, live_accuracy

STATUS_FILE = "fv_jobs_status.json"


def refit_if_due(now: datetime) -> dict:
    if not fv_refit.due(now):
        return {"due": False}
    meta = fv_refit.refit(now.strftime("%Y-%m-%d"), trigger="monthly")
    return {k: meta[k] for k in ("model_version", "train_cutoff_exclusive", "train_rows", "model_sha256")}


def after_refresh(now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    jobs = {}

    def job(name, fn):
        try:
            jobs[name] = {"status": "ok", "result": fn()}
        except Exception as exc:                                  # reported, never raised
            jobs[name] = {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}
        print(f"[fv-jobs] {name}: {jobs[name]['status']}", flush=True)

    job("refit", lambda: refit_if_due(now))
    job("record", lambda: live_accuracy.record(now))
    for m in live_accuracy.due_months(now):
        job(f"summarize {m}", lambda m=m: live_accuracy.summarize(m, now)["pooled"])
    status = {"ran_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "jobs": jobs}
    (config.ML_NFT_DIR / STATUS_FILE).write_text(json.dumps(status, indent=1, default=str), encoding="utf-8")
    return status
