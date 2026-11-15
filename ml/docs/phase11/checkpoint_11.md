# Checkpoint 11: crypto past ranges (2026-11-16)

Branch `phase-11-cone`, from `main` at 180aa51. Not pushed, not merged; `main` was not touched. Backend edits are only in the commit prefixed `backend:`. Decisions: D87, D88, D89 in ml/docs/DECISIONS.md. Items marked "(A)" and all of D89 are AUTONOMOUS and need review.

## 1. Commits

| Commit | What |
|---|---|
| `bc6f966` | DECISIONS D87-D89 |
| `e29410d` | ML: `ml/serving/past_ranges.py`, `GET /past-ranges/{asset}`, `CONTRACT_PAST_RANGES.md`, config constants, tests (leakage included) |
| `d1a690d` | ML: full-history coverage report `ml.evaluation.past_range_coverage` (monitoring only) |
| `293c83c` | backend: pull into `ml_past_ranges`; `past_ranges` on `/assets/{symbol}/detail` with the price-series guard; tests |
| `aa35605` | frontend: past bands, "Show past ranges" toggle, caption, calibration line; tests |
| `9054d05` | frontend: legend swatch visible in dark theme |
| `02b839d` | coverage reports (snapshot and live) and logs |
| `0a5ef07` | screenshots |
| this commit | checkpoint, STATUS, PHASE_11 explainer, GLOSSARY, AGENTS list |

Not committed, and not touched: the working-tree changes that were already there before this phase (README.md, backend/controllers/aai_controller.py, backend/controllers/market_controller.py, db/__pycache__/*.pyc, backend/tests/test_nft_aai.py). They are not mine, so they stay uncommitted.

## 2. What was built (owner items 1-5)

1. **Past-range series (ML, D87).** For each bar d whose bar d-30 has a served volatility:
   - centre = close of bar d-30;
   - volatility = served `vol_30d` at d-30, annualised and rounded as /risk serves it;
   - 50% and 80% bands = the cone formula of `volCone.js` at 30 days;
   - plus the close of d.

   Method and served volatility are unchanged (`RISK_VOL_COLUMN` is still `vol_30d`). Served on the new endpoint `GET /past-ranges/{asset}?days=N`, validated against `ml/docs/CONTRACT_PAST_RANGES.md`. `CONTRACT.md` is not changed.
2. **Frontend.**
   - Past 50% and 80% bands drawn lightly behind the price line (opacity 0.11 / 0.07; the forward cone uses 0.22 / 0.14), running up to the existing cone.
   - "Show past ranges" toggle, on by default.
   - Legend item "Past 50% / 80% ranges", and the caption exactly as asked.
   - Hovering a day shows "Range shown 30 days earlier (80%): a–b".
3. **Calibration line (D88).** "Over these N days, the price stayed inside the 80% range on X% of days and inside the 50% range on Y%."
   - Computed from the as-of bands and each day's ML close.
   - Not shown below 60 days (1D/1W/1M) or while the toggle is off.
4. **"EWMA" wording.** None is user-facing:
   - no match in `frontend/src` outside one test fixture;
   - none in the non-test backend source;
   - none in the live responses of `/assets/{BTC,ETH,SOL}/detail`, `/risk/BTC`, `/prediction/BTC`, `/assets/BTC/intelligence`, `/nft/collections` and three collection pages;
   - none in the page text of any screenshot (`ewma_on_page: false` in `11_screenshot_facts.json`).

   The served notes lost "EWMA" in 4248b14 (Phase 10), so nothing needed removing.
5. **Tests, screenshots and coverage:** sections 3, 4 and 6.

## 3. Tests

| Suite | Command | Result |
|---|---|---|
| ML, full | `python -m pytest ml -q` | 467 passed (6 min 55 s), at e29410d's code |
| ML, Phase 11 | `python -m pytest ml/tests/test_past_ranges.py -q` | 15 passed |
| Backend | `docker exec -w /app/backend altinvest-backend python -m pytest tests -q -p no:cacheprovider` | 61 passed, 1 skipped, 1 failed |
| Frontend | `npm test` | 26 passed (5 new); `vite build` OK |

The backend failure is `test_seed_guard.py::test_local_targets_pass[None]`. It reads the container's `MONGO_URI`, which is now the Atlas cluster, so the guard refuses it. It does not depend on this phase (the test and the guard are from 68c1df7).

Leakage tests (`ml/tests/test_past_ranges.py`, real snapshot data):
- **Cut at d-30.** For every 7th day plus the first 40 and last 5 days of each asset, the point's centre, volatility and four band edges equal the values computed from bars cut at d-30.
- **Same as /risk.** For every 90th day and the last day, the volatility equals `responses.risk()` on all pooled assets cut at d-30.
- **Future bars.** Tripling every bar after d-30 changes only that point's close.

## 4. Screenshots (`ml/docs/phase11/screenshots/`, headless Edge, demo user)

Script and output: `ml/docs/phase11/logs/11_screenshots.mjs`, `11_screenshots_output.txt`. Facts: `11_screenshot_facts.json`.

- **3M window (91 days).** `11_{btc,eth,sol}_desktop_dark.png`, `11_{btc,eth,sol}_desktop_light.png` and `11_{btc,eth,sol}_phone_dark.png`. Phone page width is 390, with no horizontal scroll. The sidebar was collapsed by click, as in 10.9.
- **BTC extras.**
  - `11_btc_desktop_dark_1Y.png`: 366 days, calibration line shown.
  - `11_btc_desktop_dark_1M.png`: bands shown, no calibration line (31 days < 60).
  - `11_btc_desktop_dark_toggle_off.png`: no past bands, caption or calibration line.
- **Calibration lines on screen (3M, chart data to 8 Nov):**

  | Asset | 80% range | 50% range |
  |---|---|---|
  | BTC | 68% | 55% |
  | ETH | 60% | 44% |
  | SOL | 58% | 32% |

  BTC over 1Y: 70% and 55%.
- **How they were taken: an isolated stack, not your running one.**
  - Backend container `altinvest-backend-p11` on :8010, with the branch source, the **local** Mongo `aaip_db` and a throwaway JWT secret.
  - Vite on :5180, pointing at it.
  - The local ML pull filled `ml_past_ranges` in the local Mongo: "stored: 400 points" for BTC, ETH and SOL.
  - Both were stopped afterwards.
  - The ML container `altinvest-ml` was rebuilt from this branch so it serves `/past-ranges`. It is additive; the sidecars were left as they were.
- **Why isolated.** Your backend on :8000 reads the shared Atlas database (section 5). Restarting it with new code would have written a new collection there.

## 5. Finding: the shared database's chart prices are demo data (D89)

- The running backend (:8000) reads Atlas. There, BTC `price_history` runs from 2025-08-28 to 2026-08-28.
- On the same dates it is 35-82% of the real Binance close, for example 43,149.63 vs 112,566.90 on 2025-08-28.
- Past ranges centred on real closes would sit far from that line. So the backend sends `past_ranges` only when the median |chart price / ML close - 1| is at most 2%:

| Database | Window | Median price gap | `past_ranges` |
|---|---|---|---|
| Atlas (backend :8000) | 2025-08-28 to 2026-08-28 | 0.4174 | null |
| local Mongo (backend :8010) | 2025-11-08 to 2026-11-08 | 0.0 | sent |

Source: `ml/docs/phase11/logs/guard_check.txt`. The same seed data also feeds the existing forward cone's start point and the header price; the header price was already in the backlog. Until the shared database has real daily closes, the app on Atlas shows the cone only, as before Phase 11.

## 6. Coverage over the full history (monitoring only; no change to the method)

`ml/docs/phase11/past_range_coverage_live.json` (live serving data in the ml-data volume, last bar 2026-11-14) and `ml/reports/past_range_coverage.json` (evaluation snapshot, last bar 2026-10-17). Nominal 0.50 and 0.80.

| Asset | Days (live) | Inside 50% (live) | Inside 80% (live) | Inside 50% (snapshot) | Inside 80% (snapshot) |
|---|---|---|---|---|---|
| BTC | 3,317 | 0.490 | 0.724 | 0.489 | 0.722 |
| ETH | 3,317 | 0.480 | 0.718 | 0.483 | 0.719 |
| SOL | 2,227 | 0.483 | 0.727 | 0.486 | 0.729 |

- The 50% band is close to nominal. The 80% band holds the price on about 72% of days, below its label: crypto has heavy tails, and the cone's normal z values understate them. Per-year shares are in both reports. For example, over full calendar years BTC's 80% share ranges from 0.63 (2020) to 0.85 (2025) (snapshot).
- As asked, nothing was changed because of this. A calibrated range would need its own declared phase (compare the NFT range backlog item).
- The snapshot report was regenerated on a clean tree at 9aa89aa (`git_dirty: false`); the numbers are unchanged. The first run recorded `git_dirty: true` only because of the uncommitted files from before this phase (section 1), since committed on branch nft-aai.

## 7. For the owner

1. Review D87 (A), D88 (A) and D89. Main choices:
   - the centre is the ML close, not the backend's `prices`;
   - a new endpoint and a separate contract file;
   - the calibration counts the ML close, and both bands are shown;
   - the 2% price-series guard.
2. To see past ranges in your own stack, both are needed:
   - the backend's database has real daily closes (the local Mongo does; Atlas does not, section 5);
   - the backend is restarted to load the branch code (`docker compose restart backend`). Its startup pull writes `ml_past_ranges` into whatever database `MONGO_URI` points at. With the current `.env` that is Atlas.
3. Merge when satisfied. `git checkout main; git merge --no-ff phase-11-cone`. Afterwards rebuild ml: `docker compose build ml; docker compose up -d ml ml-refresh ml-nft-refresh`.
