# 05: Challenges and Interview Prep

## Hard or interesting parts (and how they were solved)

- **FinBERT is slow to load (10 s to 2 min).** The model is loaded once in a background thread at
  startup (`main.py` `_warmup_sentiment_engine`). Engine imports are *lazy* (they happen inside
  functions), so the API still starts even if torch isn't installed.
- **Many background jobs, maybe many processes.** If you run 4 Uvicorn workers, every job would run 4
  times. `utils/scheduler_gate.py` `claim_run()` uses one atomic Mongo upsert as a lock: "run only if
  nobody ran this in the last N seconds". No leader election is needed, and it survives crashes.
- **Cache stampede on sentiment.** (A cache stampede is when many requests find the cache stale at the
  same time and all recompute it.) Solution: a per-asset `threading.Lock`, a re-check after getting the
  lock, a minimum retry gap, and a request time budget. On failure, serve the last good record.
- **External APIs rate-limit us.** CoinGecko: one batched call for all assets every 2 min.
  RSS: `feed_cache.py` downloads each feed at most once per 10 min for all assets, with conditional
  requests and a cool-down after HTTP 429.
- **Mongo goes down.** The sentiment storage has a **circuit breaker**: after one failure it skips Mongo
  for 30 s instead of paying a timeout on every call.
- **Honest ML.** Models (Prophet, LSTM, GARCH, LightGBM, logistic regression) were tested with
  *walk-forward* evaluation (train on the past, test on the next period, repeat). They were compared with
  simple baselines. A *sealed* test set was used only once. Price models didn't beat "no change", so the
  baseline is served and labelled. The NFT fair-value LightGBM model did pass: MdAPE (median absolute
  percentage error) 2.94% vs 3.53% for the best baseline, with a 95% confidence interval that excludes 0
  (decision D79). Leakage tests check that no feature uses future data.
- **LLM safety and cost.** News text is untrusted: it is wrapped in tags with angle brackets
  neutralised, and the prompt tells the model never to follow it. A strict JSON schema means the output
  always parses. Results are cached until the article list changes, so a quiet collection costs no calls.
- **Data safety.** Seed scripts delete and rewrite demo rows. `db/seed_guard.py` refuses any non-local
  DB without `--allow-remote` (this came after a near-miss where Docker picked up the shared Atlas URI).

## Trade-offs

| Choice | Gained | Gave up |
|---|---|---|
| Jobs as threads inside the API process | Simple; no Redis/Celery to run | API and jobs scale together; torch makes the API image huge |
| Backend imports the sentiment engine directly | No extra network hop; one deployable | Several-GB backend image; tight coupling |
| ML as a separate service, pulled daily into Mongo | ML can fail without breaking the site; pages read fast from Mongo | Predictions are up to a day old |
| MongoDB | Store API payloads as-is; flexible schema | No joins or foreign keys; multi-document writes are not in transactions |
| JWT in `localStorage` + session row | Easy to send; tokens can be revoked | Readable by any injected script (XSS risk) |
| Serving baselines when models don't win | Trustworthy numbers | Less "impressive" demo |
| Sync `def` routes + PyMongo | Simple code | Concurrency is limited by the thread pool |

## Weaknesses / what I'd improve

- CORS allows every origin (`allow_origins=["*"]` in `main.py`, with a "tighten" TODO comment).
- `/health` is static. It doesn't check Mongo or the ML service.
- The `POST /sentiment/refresh` routes need no login, so anyone can trigger expensive work.
- `backend/requirements.txt` has no version pins. The Nov-2 audit found known CVEs in the installed packages.
- If `JWT_SECRET` is unset, a public development secret is used (it does log a warning).
- No CI pipeline (none found). There are tests: backend, ML (400+), sentiment and frontend utils.
- Dead code: `ensureDevSession()` in `frontend/src/hooks/useAuth.js` is never called.
- Two Mongo databases (`aaip_db` + `altinvest`) and two connection helpers.
- I'd move the jobs + FinBERT into a `worker` container. Use httpOnly cookies + rotating refresh tokens.
  Add one validated settings object. Add an email outbox with retries (all listed in `AUDIT_2026-11.md` §6.5).

## Scaling

**10x users (thousands):**
- Run the API with several Uvicorn workers behind a load balancer. `scheduler_gate` already stops jobs from running twice.
- Move the jobs into one worker container, so the API image drops torch and starts fast.
- Add a 30-60 s cache (in-memory or Redis) for universe endpoints (`/discover`, `/compare`, trending).
  Each request runs about 8 aggregations today.
- Check that every hot query uses an index (`db/indexes.py` already covers `(key, timestamp DESC)`). Add a TTL to `sentiment_history`.

**100x users:**
- Make the API stateless (no threads). Run the jobs with Celery/RQ + Redis or a managed scheduler.
- Use a MongoDB Atlas replica set and send reads to secondaries. Use time-series collections for
  `prices` / `asset_market_data`. Shard by `user_id` for user data if needed.
- Put a CDN in front of the frontend (it is already static nginx).
- Note: market data, sentiment and ML work are the same for every user, so their cost doesn't grow with
  users. Only per-user reads grow, and those are cheap with caching.
- Send alerts through a queue. Use one evaluation pass per metric, then fan out to matching rules. Send email via an outbox.
- Add monitoring: real health checks, metrics and alerts on job failures.

## Security considerations

- ✅ bcrypt passwords; rate limits on login, signup, reset and Google; generic "invalid email or password".
- ✅ Revocable sessions; purpose-scoped reset/verify tokens; Google ID token fully verified.
- ✅ Ownership check on every user-scoped query; Pydantic input validation; search regex escaped (no NoSQL injection).
- ✅ Secrets come from env vars and are redacted in logs; no stack traces sent to clients; repo mounted read-only in Docker.
- ✅ The LLM prompt treats news text as untrusted data.
- ⚠️ CORS `*`; token in `localStorage`; default dev JWT secret; unpinned dependencies; open refresh endpoints.

## Likely interview questions

1. **What is the AAI score?** One 0-100 score: 40% ML forecast, 30% sentiment, 30% risk (higher = safer).
   Each part is normalised to 0-100 first. If the forecast or risk is missing, the score is null, not guessed.
2. **Why combine three signals?** Each alone is weak and noisy. Blending them gives a more stable view.
   Users also see the breakdown, so the score can be explained.
3. **Why FastAPI?** The ML and NLP code is Python, so one language everywhere. It gives automatic docs
   and Pydantic validation. (Add your own reason. See questions below.)
4. **Why MongoDB over PostgreSQL?** Payloads from CoinGecko, OpenSea and the ML service vary, and
   documents store them easily. The cost is no joins or foreign keys, so ownership is enforced in queries.
5. **How does login work?** bcrypt check → a session row in `user_sessions` → a JWT with `sid`. Every
   request checks the JWT *and* that the row exists. Deleting the row logs that device out at once.
6. **JWTs are stateless. Why check the DB?** So we can revoke them: logout, "sign out other devices",
   password change. It costs one indexed lookup per request.
7. **How do you stop brute-force login?** `auth_attempts` counts failures per account+IP (5/15 min) and
   per IP (30/15 min) and returns 429 with `Retry-After`. Rows expire through a TTL index.
8. **How does sentiment work?** RSS + Google News → clean → VADER (35%) + FinBERT (65%) per article,
   weighted by source trust and recency → 70% news + 30% market signals → trend vs 24 h ago.
9. **Why both VADER and FinBERT?** VADER is fast and handles short text well. FinBERT understands
   finance language. If FinBERT fails, VADER alone still gives a score.
10. **Why use an LLM for NFT news?** NFT stories get reposted under new headlines. The LLM spots "same
    story" and filters out irrelevant articles, which plain NLP can't do. It returns strict JSON and falls back to VADER + FinBERT.
11. **Your price model didn't beat the baseline. Isn't that a failure?** No. Measuring it honestly is the
    result. We served the baseline and labelled it in the UI. The NFT fair-value model did beat its baseline on a sealed test.
12. **What is walk-forward validation and why use it?** Train on data up to time T, test on the next
    period, move T forward, repeat. A random split would leak future prices into training.
13. **How do background jobs avoid running twice with many workers?** `claim_run()` does an atomic
    Mongo upsert keyed by job name. Only the process that wins the claim runs that tick.
14. **What if the ML service is down?** The pull retries 3 times and then writes nothing. Pages keep the
    last good prediction. The ML service itself returns 503 for bad data instead of serving wrong numbers.
15. **What if Mongo is down?** Every `PyMongoError` becomes a clean 503. The sentiment engine's circuit
    breaker stops retrying for 30 s. The frontend shows a connection banner.
16. **How do alerts avoid spamming?** They fire only when a value *crosses* the threshold. Then they
    pause until the user re-arms them.
17. **How would you scale to 100x users?** A stateless API behind a load balancer. Jobs move to a worker
    with a queue, plus a Redis cache for universe endpoints. Use an Atlas replica set, and a CDN for the frontend.
18. **Biggest security gap today?** CORS `*` and the token in `localStorage`. I'd fix them with an origin
    allow-list and httpOnly SameSite cookies with rotating refresh tokens.
19. **How is a portfolio's P&L computed?** The average cost method. A buy updates the weighted average
    price. A sell's realised P&L is (sell price − average price) × quantity. The server always computes the cost basis.
20. **How do you measure diversification?** `(1 − Σ w²) × 100` from the Herfindahl index. One position
    scores 0 and four equal positions score 75. Any position over 40% is flagged as concentrated.
