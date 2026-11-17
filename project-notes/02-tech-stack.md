# 02: Tech Stack

"(likely)" = the reason is my best guess, not written in the code or docs.

## Frontend (`frontend/`)

| Technology | What it's used for | Why it was chosen | Alternative I could mention |
|---|---|---|---|
| React 19 | All UI pages and components | Most popular UI library; component model fits a dashboard with many cards (likely) | Vue, Svelte, Angular |
| Vite 8 | Dev server with hot reload, production build | Very fast startup and HMR (hot module replacement = page updates without a reload) (likely) | Create React App, Next.js, Webpack |
| react-router-dom 7 | Client-side routing (`src/routes.js`) | Standard router for single-page React apps | TanStack Router, Next.js routing |
| Plain CSS + CSS variables (`styles/tokens.css`) | Theming (light/dark), per-page styles | Simple, no extra build step; tokens make dark mode easy (likely) | Tailwind (is installed, but the audit says little of it is used), CSS Modules, styled-components |
| framer-motion / ogl / three | Landing-page animations and effects | Polished marketing page (likely) | CSS animations, GSAP |
| `fetch` + own `apiClient.js` | All HTTP calls, timeout, auth header, error mapping | No extra dependency; full control (likely) | Axios, React Query / TanStack Query |
| `node --test` | Unit tests for utils (`src/utils/*.test.js`) | Built into Node, zero setup | Vitest, Jest |

## Backend (`backend/`)

| Technology | What it's used for | Why it was chosen | Alternative I could mention |
|---|---|---|---|
| Python + FastAPI | REST API (19 routers, about 80 routes) | Same language as the ML/NLP code; auto docs at `/docs`; Pydantic validation (likely) | Django REST Framework, Flask, Node/Express |
| Uvicorn | ASGI server (ASGI = Python's standard interface for async web servers) | Default server for FastAPI | Gunicorn + Uvicorn workers, Hypercorn |
| Pydantic | Request/response schemas (`models/schemas.py`) | Built into FastAPI; type-checked input | Marshmallow |
| PyMongo | MongoDB driver (`db/queries.py`) | Official, synchronous driver; the routes are sync `def` | Motor (async), an ODM like Beanie/MongoEngine |
| bcrypt | Password hashing (`auth/security.py`) | Slow-by-design hash, industry standard | Argon2, scrypt |
| PyJWT | Login, reset and verify tokens (HS256) | Simple, stateless signed tokens | Server sessions with cookies, Paseto |
| httpx | Calls to ML service, CoinGecko, Binance, Google, Groq | Timeouts and a modern API | requests, aiohttp |
| Background threads | 10 periodic jobs started in `main.py` `on_startup` | Simple, no extra infrastructure (likely) | Celery + Redis, APScheduler, cron, a separate worker container |

## Database

| Technology | What it's used for | Why it was chosen | Alternative I could mention |
|---|---|---|---|
| MongoDB 7 (Docker) or MongoDB Atlas | All app data (~33 collections), sentiment data, caches | Flexible documents fit varied asset/NFT/ML payloads; easy to store JSON from APIs as-is (likely) | PostgreSQL (+ JSONB), TimescaleDB for time series |
| TTL indexes | Auto-delete expired sessions, login attempts, old search history | Built-in cleanup, no cron needed | A scheduled cleanup job |

## ML and NLP

| Technology | What it's used for | Why it was chosen | Alternative I could mention |
|---|---|---|---|
| Separate FastAPI ML service (`ml/`, port 8001) | `/predict`, `/risk`, NFT floor/risk/sales/item value | Keeps heavy ML apart from the web API; can be rebuilt on its own | Model served in the backend itself, BentoML, TorchServe |
| pandas, NumPy, scikit-learn | Features, labels, baselines, evaluation | Standard Python data stack | Polars |
| LightGBM | Served NFT fair-value model | Fast gradient boosting for tabular data; beat baselines in testing (`ml/docs/DECISIONS.md` D78) | XGBoost, CatBoost |
| Prophet, PyTorch (LSTM), arch (GARCH) | Training/evaluation only (`requirements-train.txt`) | Tried as forecasters; none beat the baseline, so not served (D35, D45) | ARIMA, Temporal Fusion Transformer |
| VADER | Fast rule-based sentiment on headlines | Cheap, no GPU, good on short text | TextBlob |
| FinBERT (HuggingFace transformers + torch) | Finance-tuned BERT sentiment | Understands financial language better than VADER | Generic BERT/RoBERTa, an LLM |
| Groq LLM (`openai/gpt-oss-120b`) | Scores NFT news: relevance, label, duplicate stories | Strict JSON output, very fast inference, handles reworded duplicate stories | OpenAI/Anthropic API, a local LLM |
| feedparser | Reads RSS news feeds | Simple, robust RSS parser | BeautifulSoup scraping |

## Auth

| Technology | What it's used for | Why it was chosen | Alternative |
|---|---|---|---|
| JWT + `user_sessions` collection | Login sessions that can be revoked | Stateless token, plus a DB row so logout/"sign out other devices" works | Opaque session IDs in httpOnly cookies |
| Google Identity Services (OAuth code flow) | "Sign in with Google" (`auth/google_oauth.py`) | Users don't need a new password | Auth0, Firebase Auth, Clerk |
| SMTP (`utils/mailer.py`) | Verification, reset and alert emails | Works with any mail provider | SendGrid, AWS SES |

## External APIs

| API | Used for | Key needed? |
|---|---|---|
| CoinGecko | Live market snapshot every 2 min, asset profiles | No |
| Binance | Hourly price history; daily data for the ML service | No |
| Google News RSS + 10 publisher RSS feeds | News for sentiment | No |
| OpenSea, Alchemy | NFT floor prices, sales, traits | Yes (`OPENSEA_API_KEY`, `ALCHEMY_API_KEY`) |
| Groq | LLM for NFT news and market themes | Yes (`GROQ_API_KEY`); falls back to VADER + FinBERT |
| Frankfurter (ECB rates) | Display-currency conversion | No |

## Hosting / deployment

| Technology | What it's used for | Why | Alternative |
|---|---|---|---|
| Docker + Docker Compose | Runs mongodb, backend, ml, ml-refresh, ml-nft-refresh, frontend | One command to start everything; same setup on every laptop | Kubernetes, separate VMs |
| nginx (`frontend/Dockerfile.prod`) | Serves the built frontend in production, with SPA fallback | Fast static server | Vercel, Netlify, S3 + CloudFront |
| Cloud host | TODO: confirm. No cloud deployment config (Kubernetes, Terraform, CI) was found in the repo | | Render, Railway, AWS ECS, Fly.io |
