# Phase 7: Backend integration

## 1. Goal
Connect the website to the ML service. Until now the backend showed numbers that were typed in by hand ("seed" rows) for BTC, ETH and SOL. From now on it copies the ML service's real answers once a day and shows ML's own explanation (the `note`) on the asset page.

## 2. What we did
1. The backend now **pulls** `/predict` and `/risk` for BTC, ETH and SOL from the ML service once at startup and every day at 00:15 UTC, ten minutes after ML refreshes its data. It stores the answers in MongoDB.
2. The backend's `/prediction` and `/risk` answers now include the `note`, and they never use made-up numbers for these three assets.
3. A **stale note** is added when the newest stored row is more than 36 hours old.
4. The seed script no longer writes invented predictions for BTC, ETH and SOL.
5. The asset page shows ML's note. While ML says `UNCERTAIN`, the Buy/Hold/Sell badge is labelled "AAI rating", so nobody reads it as the model's call.
6. We wrote 20 backend tests and ran the whole stack in Docker.

## 3. Files
- `backend/controllers/ml_pull_controller.py`: the daily pull.
- `backend/utils/ml_rows.py`: the 36 h stale note.
- `backend/tests/`: the 20 tests.
- `frontend/src/components/assetDetail/MlNoteCard.jsx`: shows the note.
- The other changed files are listed in docs/STATUS.md ("files changed outside ml/").

## 4. How it works
- **Retries.** Each call waits at most 10 s and is tried up to 4 times (waits of 2, 4 and 8 s in between). A 404 means "asset not covered" and is not retried. A 503 or no answer means nothing is written, so yesterday's good row stays the newest.
- **One row per asset per day.** A second pull on the same day replaces that day's row and does not add a new one.
- **Dates, not text.** The time is stored as a real date. MongoDB sorts dates above text, so a row with a text time would never count as the newest.
- **Stale note.** Example: if ML is down from Monday 00:15 to Tuesday 13:15, the stored row is 37 h old, so the backend adds "data stale ...". ML has its own separate 48 h rule, based on the date of its last price bar.
- **AAI.** ML's forecast is "0 % change" (the no-change baseline). The AAI counts that as a neutral 50 and says so in its note (decision C5, 2026-11-02).

## 5. Results
From the live run on 2026-11-02 (backend log and API answers, recorded in docs/STATUS.md):

| Check | Result | Meaning |
|---|---|---|
| First pull | 6 of 6 stored | BTC, ETH, SOL × predict, risk |
| Newest BTC row | `baseline-last-value`, `UNCERTAIN`, note set | The real ML answer replaced the seed |
| risk_score BTC / ETH / SOL | 97.795108 / 91.567549 / 87.09044 | Same as ML; higher = safer |
| Pull with ML stopped | 6 failures, row unchanged | Last good row kept |
| Seed re-run | BTC row unchanged | The seed no longer overwrites ML |
| Tests | backend 20 passed, ML 225 passed | |

## 6. Decisions
- Pull at 00:15 UTC, 10 s timeout, 3 retries, stale after 36 h: integration blank 2, chosen on 2026-10-20 (docs/STATUS.md).
- Pass `note` and `signal` through, and rename the badge while ML says UNCERTAIN: blank 6, D33.
- AAI keeps the neutral 50 from the baseline (D35), with a note: decision C5, made by the user on 2026-11-02.

## 7. Limits
- If one asset fails ML's data checks, all three return 503 (pooled risk, D36), so no asset is updated that day.
- The backend's `.env` points to the shared cloud database (Atlas), so a local run writes real rows there.
- The 36 h note reads the time of the last successful pull, not the age of the market data.
- The rendered page still has to be checked by hand in a browser (verify step 5).

## 8. Verify and next
- Verify: see "How to verify Phase 7 yourself" in docs/STATUS.md.
- Next: the ML fixes A0-A7 (A1 matters most: after a restart, the API can be down for minutes), then the hand-over note (B1), then the Phase 8 NFT plan.
