# Phase 6b: Daily data refresh and Docker

## 1. Goal
Make the ML service run from a fresh clone, in Docker, with data that updates every day. It must never touch the frozen data every report was computed on. This is the last step before the ml-v2 branch is merged into main.

## 2. What we did
1. Re-ran the backtest and the D36 check on a clean commit: the numbers were identical.
2. Wrote down D38 (staleness), D39 (the CONTRACT `note` wording, agreed with Person B) and D40 (refresh and serving gate).
3. Split the data into an **evaluation snapshot** and **serving data**, chosen by two environment variables.
4. Added a stricter serving gate, the daily refresh, a small v2 Docker image and two compose services.
5. Wrote 23 tests (hand-made data, no network). `python -m pytest ml` gives 183 passed.

## 3. Files
- `ml/data/serving_gate.py`: decides whether an asset's data may be served.
- `ml/data/refresh.py`: fetch, validate, and replace the served files only if everything passed.
- `ml/Dockerfile`, `docker-compose.yml` (`ml` and `ml-refresh`), `.dockerignore`: the container setup.
- `ml/README.md`: a one-page guide for the team.

## 4. How it works
- **Two copies of the data.** The evaluation snapshot (ml/data/raw) must not grow. If it did, the split boundaries, which come from the row count, would move. The service in Docker reads its own folders in the `ml-data` volume instead.
- **Serving gate.** An asset is served only if its validation report passed AND the report matches the CSV (same row count, same last day). Anything else is a 503.
  Example: the CSV has 3352 rows but the report says 3351. The data changed after it was checked, so 503.
- **Refresh.** Back up the three files (CSV, fetch info, report), then download and validate in a staging folder. Only a set that passed replaces the old files, with an **atomic replace**. On any failure the backup comes back, so yesterday's data keeps being served with a "data stale" note.

## 5. Results
From the container run on 2026-10-20 at 20:15 UTC (`/data/validation/refresh_status.json`, and `/risk` from the host):

| | BTC | ETH | SOL |
|---|---|---|---|
| Refresh status / servable | ok / yes | ok / yes | ok / yes |
| Rows served in Docker (snapshot rows) | 3351 (3349) | 3351 (3349) | 2261 (2259) |
| Last bar served (snapshot) | 2026-10-19 (2026-10-17) | 2026-10-19 (2026-10-17) | 2026-10-19 (2026-10-17) |
| risk_score in Docker | 95.70 | 92.44 | 81.60 |

- Docker serves two more days than the snapshot, so no "data stale" note appears. risk_score differs from Phase 6a because 30-day volatility fell over those two days.
- The snapshot files on the host were byte-identical before and after (SHA-256).
- In the container, `python -m pytest ml` gives 183 passed, and the contract test ran (not skipped).

## 6. Decisions
- D38: "data stale" when the latest bar closed more than 48 h ago.
- D39: the CONTRACT `note` description; text only, the schema is unchanged.
- D40: daily refresh at 00:05 UTC, restore on failure, the stricter serving gate, and the snapshot is never overwritten without `--force`.

## 7. Limits
- Each refresh downloads the full history again (about 4 pages per asset).
- A gap in new data passes validation, but serving refuses gapped bars with a 500, not a 503 (Recommendations in ml/docs/STATUS.md).
- Re-running evaluation on newer data needs a new D-number that fixes the split dates (D40).

## 8. Verify and next
- Verify: see "How to verify Phase 6b yourself" in ml/docs/STATUS.md.
- Next: the PR from ml-v2 into main, then Phase 7: the backend calls this service at http://ml:8001.
