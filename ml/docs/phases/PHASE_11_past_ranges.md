# Phase 11: past ranges on the crypto price chart

## 1. Goal
The crypto price chart showed a range only for the next 30 days (the [volatility cone](../GLOSSARY.md), D52). Phase 11 also shades the past: for each day, the range the cone would have shown 30 days earlier. A user can then see how often the price actually stayed inside it. Nothing new is modelled: same cone formula, same served volatility (persistence `vol_30d`, D82).

## 2. What we did
1. ML: for each day d, rebuilt the cone as it would have looked on d-30 ([as of](../GLOSSARY.md) d-30), using only bars up to d-30 (D87).
2. Tested for [leakage](../GLOSSARY.md): every value equals the result computed from data cut at d-30.
3. Served it on a new ML endpoint `/past-ranges/{asset}`. The backend pulls it daily and adds `past_ranges` to the asset detail.
4. Frontend: light bands behind the price line, a "Show past ranges" toggle (on by default), a caption, and a [calibration line](../GLOSSARY.md) (D88).
5. Added a guard: no past ranges unless the chart's prices are the closes the ranges were built from (D89).
6. Reported full-history coverage, for monitoring only.

## 3. Files
- `ml/serving/past_ranges.py`: the series and the coverage count; schema in `ml/docs/CONTRACT_PAST_RANGES.md`.
- `ml/evaluation/past_range_coverage.py`: writes `ml/reports/past_range_coverage.json`.
- `ml/tests/test_past_ranges.py`, `backend/tests/test_past_ranges.py`, `frontend/src/utils/pastRanges.test.js`: tests.
- `frontend/src/utils/pastRanges.js`: the window, calibration and wording.

## 4. How it works
Example (made-up numbers): on 1 Oct the close was 100 and the served annual volatility was 0.73. The 80% range for 31 Oct is 100 x exp(±1.2816 x 0.73/√365 x √30) = 76.5 to 130.8. If the 31 Oct close was 120, that day counts as "inside the 80% range". The calibration line is the share of visible days counted as inside. It is shown only when 60 or more days are visible.

## 5. Results
Share of days inside each band over the whole history. Live data runs to 2026-11-14 (`ml/docs/phase11/past_range_coverage_live.json`); the snapshot to 2026-10-17 (`ml/reports/past_range_coverage.json`) gives the same to about 0.01.

| Asset | Days (live) | Inside 50% band | Inside 80% band |
|---|---|---|---|
| BTC | 3,317 | 0.490 | 0.724 |
| ETH | 3,317 | 0.480 | 0.718 |
| SOL | 2,227 | 0.483 | 0.727 |

Meaning: the 50% band behaves about as labelled. The 80% band holds the price less often than 80%, because crypto has [heavy tails](../GLOSSARY.md). This is shown to users as is; the method was not changed because of it.

## 6. Decisions
- D87: the method (centre = the ML close of d-30), a new endpoint and contract file, and backend storage.
- D88: the calibration line: wording, 60-day minimum, and the ML close as "the price".
- D89: the price-series guard.
- Items marked (A) were chosen by the agent and need review.

## 7. Limits
- The shared Atlas database has demo seed prices, so the guard hides past ranges there (checkpoint_11.md section 5).
- The live cone starts at the backend's last price; past ranges are centred on the ML close. They match only when the database has real closes.
- The 80% band is too narrow over the full history. A calibrated range would be its own phase.

## 8. Verify and next
See "How to verify Phase 11 yourself" in docs/STATUS.md. Next: the owner reviews D87-D89 and merges. Putting real prices in the shared database is a backlog item.
