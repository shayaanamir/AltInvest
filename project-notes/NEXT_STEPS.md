# Next steps (handoff, 2026-11-17)

For a new session continuing this work. Read `AUDIT_2026-11-16.md` (sections 3, 7 and 9) and
`ml/docs/DECISIONS.md` (D94 to D96) first.

## Rules that still apply

- **Atlas:**
  - Never run `seed_all` or any old seed script against Atlas. The only allowed writes are idempotent upserts of real data, such as the bootstrap `coins` and `profiles` steps with `--allow-remote`.
  - Deletes follow this order: dry run with counts, then a backup to `C:\Shail\Somaiya\LY-Project\AltInvest\backups\`, then the owner's explicit approval, then the delete, then a re-count.
- **Secrets:** never print `.env`, secrets or connection strings.
- **Git:**
  - The main folder stays on `main`. Do code work in separate worktrees (`git worktree add ..\AltInvest-<name> -b <branch> origin/main`).
  - Commit one root cause per commit, with the test output in the commit message or PR.
  - Before every merge, fetch and rebase onto the latest `origin/main`. Teammates' changes win in a conflict unless they break a test.
  - Merge your own PRs with `gh pr merge <n> --merge`, but only once the branch is rebased with no conflicts and the tests and build pass. `gh` is at `C:\Program Files\GitHub CLI\gh.exe` (not on Git Bash's PATH by default).
- **Known test-environment failures** (not regressions): `test_seed_guard::test_local_targets_pass[None]` and `test_compose_no_longer_sets_a_second_database`.
- **Running the tests:**
  - **Backend:** in a container built from `main` (`docker build -f backend/Dockerfile -t altinvest-backend-test .`), with the worktree mounted at `/app`, `-w /app/backend`, `APP_ENV=test` and `MONGO_TEST_URI` pointing at a throwaway MongoDB (e.g. the local `mongodb` container on network `altinvest_altinvest`). The host Python lacks the backend's dependencies.
  - **ML:** `..\AltInvest\.venv-train\Scripts\python.exe -m pytest ml`, from the repo root or from `ml/`.
  - **Sentiment engine:** from `sentiment_engine/`, inside the backend image.
  - **Frontend:** `eslint .`, `npm test` and `vite build`. A worktree needs a junction to the main folder's `frontend/node_modules`.
- **Decision numbers:** the next free one is **D97**.

## Done on 2026-11-17 (merged to `main`)

| PR | Merge commit | What |
|---|---|---|
| #12 | `2d684c4` | ML Stage 1 (D94: 16 coins served, DAI/BASE not covered, no seeded ML rows) and audit Step 3 (G-07, G-12, G-36, G-37, G-38, G-39, N-04, most of N-05), plus D95. The branch first merged main's Steps 5 and 6; G-37 was applied to the new onboarding card. |
| #13 | `376f176` | G-20: no AAI from a prediction or risk row older than 3 days; "inputs stale"; `inputs_as_of` and `as_of` on every row. |
| #14 | `c2a0331` | D96: measured risk breakdown (volatility, liquidity, 90-day drawdown; higher = safer), plus G-28 (Discover "Min safety score"). **Scheduled writes are off until `RISK_BREAKDOWN_WRITES=1`.** |
| #15 | `d31975a` | G-45 A2: a corrupt prediction-log line is skipped and reported. |
| #16 | `da56ebd` | N-10: `ml/signal` renamed to `ml/signals`; pytest works from inside `ml/`. |
| #17 | `57d6925` | `tools/cleanup_fictional_assets.py`. |
| #18 | `a3a9027` | ARB added to the sentiment engine's assets, so it can get an AAI score. |
| #19 | `94c5f1b` | Audit and `ml/docs/STATUS.md` updated for all of the above. |

Data work on Atlas, done with the owner's approval:

- The 4 fictional NFT collections and BASE were deleted (42 rows). The backup is `backups\fictional-assets-20261117T070442Z.json`, the re-count is 0, and Discover shows 7 collections.
- `assets` has all 18 identity rows: 17 real coins, plus BASE before it was deleted.

Deploy:

- `docker compose up -d --build` was run in the main folder at `2d684c4` (PR #12) only.
- Checks: `/health` ok on Atlas; BTC and LINK serve real risk (84.84 and 56.31) and the no-change forecast (UNCERTAIN); DAI is "not covered".
- **The running stack does not yet include PRs #13 to #19.** Run `git pull` in the main folder, then `docker compose up -d --build`.

## What's left

1. **Deploy the latest `main`:** `git pull` in the main folder, then `docker compose up -d --build`. Then check `/health` and an asset page with an AAI score, and confirm ARB gets a sentiment reading within about 15 minutes and an AAI row within about 30.
2. **D96 liquidity change (owner request):** measure liquidity as **24h USD volume** (ranked), not volume / market cap. Volume / market cap is turnover, so BTC ranks near the bottom (6.7 in the dry run). Do it as a new decision (D97, amending D96) in `backend/controllers/risk_breakdown_controller.py` (`METRICS["liquidity"]` and `gather_inputs`), with tests.
3. **Stage 2 Atlas run (needs the owner's go-ahead):**
   - First a dry run: `docker exec -w /app/backend altinvest-backend python -m controllers.risk_breakdown_controller`.
   - Then one real run with `--write`, or set `RISK_BREAKDOWN_WRITES=1` for the backend. Compose doesn't pass it yet; add `RISK_BREAKDOWN_WRITES: ${RISK_BREAKDOWN_WRITES:-0}` to the backend's environment.
   - Do item 2 first so the first stored rows use the new liquidity.
4. **AAI coverage:** after items 1 and 3, check that `aai_scores` has rows for all 16 coins. Before this work, ARB, ATOM and LTC were missing. ARB is fixed by PR #18. ATOM and LTC lack a usable sentiment reading at times (no articles); the AAI refresh needs a recent one.
5. **Bug sweep (Task 6, not started):**
   - Use a throwaway account. A new account must verify its email first, and SMTP is configured, so either use a plus-address the owner can click, or get approval to mark it verified in Atlas.
   - Don't store its credentials in a file.
   - Test in the UI: every Discover filter, the create and delete flows (watchlist, holding, alert), Compare, all 17 asset pages plus BASE (now gone, so it should show "not found"), phone width, and the other currencies.
   - Re-try the "blank DOGE page" and "blank NFT pages from Discover" reports. Neither reproduced on 2026-11-16 at desktop width in USD.
   - Then delete the account through Settings, and confirm its holdings, watchlists and alerts are gone. The old "test" account was already deleted on 2026-11-16.
   - Label each bug's cause as Atlas data, code already on main, or new code.
6. **Audit Step 2 (Task 8):**
   - N-01: reconcile `real-prices` with `main`'s market-data job; merge or retire `phase-11-cone` and `nft-aai`; prune stale branches.
   - The rest of N-02: one Python lock file for the backend image (pins and `npm audit` were done in Step 6).
7. **Sign-offs the owner still has to give** (items marked "(A)" were decided autonomously):
   - **D94:** (3) pool failures (a failing non-evaluated coin is left out of the pool and returns 503 itself); (6) removal of the `/assets/{symbol}/detail` forecast object and the "AI Prediction" performance mode.
   - **D96:** (3) the input age limits (ML row 3 days, CoinGecko snapshot 1 day, prices 3 days with at least 60 of 90 closes); (5) Discover's `volatility` = 100 minus the volatility safety score; (7) G-28's `min_safety` parameter.
   - **D95** has no "(A)" items.
8. **Other open audit items:** the rest of N-05 (as_of in watchlists, trending, search and NFT floors); G-45 A1 and A3-A6; the ❌ and ❔ rows in section 3 of the audit.

## Branch and worktree states (2026-11-17, after PR #19)

- `origin/main` is at `94c5f1b`. The main folder `AltInvest` is on `main` but checked out at `2d684c4`, so it needs `git pull` (see item 1).
- These feature branches are all merged into `main`, and their worktrees can be removed (`git worktree remove ..\AltInvest-<name>`, then `git branch -d <branch>`):

  | Branch | Worktree |
  |---|---|
  | `real-forecasts` | none; the merge was prepared as `sync/real-forecasts-main` in `AltInvest-sync` |
  | `fix/g20-aai-input-age` | `AltInvest-g20` |
  | `stage2-risk-breakdown` | `AltInvest-stage2` |
  | `fix/g45-read-log` | `AltInvest-g45` |
  | `fix/n10-signal-shadow` | `AltInvest-n10` |
  | `chore/cleanup-fictional-assets` | `AltInvest-cleanup` |
  | `fix/sentiment-arb` | `AltInvest-arb` |
  | `docs/audit-step3` | `AltInvest-docs` |
  | `docs/next-steps` (this file) | `AltInvest-next` |

  - The worktrees have directory junctions at `frontend/node_modules` pointing at the main folder's `node_modules`. `git worktree remove` deletes only the junction, not the target.
- Untouched, older branches (audit Step 2 decides their fate): `real-prices`, `phase-11-cone`, `nft-aai`, `phase-10-nft`, `phase-9-*`, `ml-v2`, `ml-phase-7`, `dev-shail`, `price-seed-issue`, `fix/binance-mirror`. There are also two local-only branches: `phase-7-integration` and `switch`.
- **Atlas:**
  - `risk_breakdown` is empty: D96 has not been written.
  - `aai_scores` crypto rows covered 13 coins before PR #18.
  - No fictional rows are left.
  - Backups are in `C:\Shail\Somaiya\LY-Project\AltInvest\backups\`.
