# Phase 6d: Scorecard and live tracking

## 1. Goal
Show in one place how every model did against its baseline, and start recording what the API serves so it can be checked against what really happened. It comes now because the service runs daily (6b, 6c); from here on every served value can be scored 30 days later.

## 2. What we did
1. Wrote a **scorecard** generator that copies the numbers from the existing reports into one JSON file and one Markdown table. It trains nothing and reads no market data.
2. Added a **prediction log**: after each daily refresh, one line per asset with the values /predict and /risk served that day.
3. Added a **live scorecard** that scores a logged line once its 30-day horizon has passed, and counts it as pending until then.
4. Added two endpoints, `/debug/scorecard` and `/debug/live-scorecard`.
5. Wrote 26 tests (hand-made data, no network). `python -m pytest ml` gives 225 passed.
6. A review found that two refreshes could write the status file and the log at the same time. Both writes now run inside the refresh lock.

## 3. Files
- `ml/evaluation/scorecard.py`: builds `ml/reports/scorecard.json` and `ml/reports/SCORECARD.md`.
- `ml/serving/prediction_log.py`: appends the day's served values to `prediction_log.jsonl` in the serving data.
- `ml/evaluation/live_score.py`: scores the logged lines (`live_scorecard.json`).
- `ml/tests/test_scorecard.py`, `ml/tests/test_live_tracking.py`: the tests.

## 4. How it works
- **Approved is not served.** A model is approved only if the whole 95% CI of its gain over the baseline is above 0. Serving follows the decisions (D27, D33, D35, D36), so an approved model can still be unserved.
- **Prediction log.** It writes one line per (asset, last bar), so a second refresh on the same day adds nothing. It writes only to the serving data, never the snapshot (D40).
- **Live score.** A line logged for bar t is scored only when bar t+30 exists. It uses bars t+1 to t+30 only, through the same label functions as training.
  Example: a line logged for 2026-10-31 can be scored once the 2026-11-30 bar is in the data. Until then it is "pending" and no number is shown.

## 5. Results
From `ml/reports/SCORECARD.md` (generated at commit b243823):

| | BTC | ETH | SOL |
|---|---|---|---|
| Models approved (of risk, price, direction) | 0 | 1 (direction) | 0 |
| Models served | 0 | 0 | 0 |
| Served signal: trades / windows | 0 / 68 | 0 / 68 | 0 / 37 |
| Buy-and-hold mean per 30-day window | +6.23% | +7.55% | +8.88% |

- ETH direction's log-loss gain is 0.0359 [0.0035, 0.0604]. It is still not served: Phase 5a found no up/down skill (D33).
- The Docker run on 2026-11-01 logged 3 lines (last bar 2026-10-31). `/debug/live-scorecard`: 3 logged, 0 scored, 3 pending, first scorable 2026-11-30.

## 6. Decisions
- No new D-number. The scorecard only copies report numbers (AGENTS rule 5). The log and live score follow D40 (serving data only) and the 30-day horizon (D3).

## 7. Limits
- Nothing is scored live until 2026-11-30, and 30 days give only 1 independent observation per asset (n_effective).
- The served values are the baselines today, so the live score measures the baselines, not a model.
- If the refresh does not run on a day, that day has no log line; the log is never back-filled.
- On 2026-11-01 the Docker healthcheck timed out (5 s) because the host was overloaded: even `python -c "print('hi')"` took 11 s on the host. All routes still answered 200.

## 8. Verify and next
- Verify: see "How to verify Phase 6d yourself" in ml/docs/STATUS.md.
- Next: Phase 7, where the backend calls `/predict` and `/risk` at http://ml:8001 and shows the `note` and `signal` fields.
