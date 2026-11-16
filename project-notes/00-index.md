# AltInvest: Study Notes (Index)

## Summary

AltInvest (called "AAIP: Alternative Asset Intelligence Platform" inside the backend) is a web app for
tracking and analysing **alternative assets**: cryptocurrencies (18 in the catalog) and blue-chip NFT
collections (7). It combines three signals into one 0-100 score, the **AAI score**. The three signals
are an ML price forecast, news sentiment (from NLP models and an LLM) and a volatility-based risk score.
Users can sign up, build a portfolio, keep watchlists, compare assets, set alerts and read a sentiment
hub. The stack is a React + Vite frontend and a FastAPI (Python) backend on MongoDB. A separate FastAPI ML
service serves forecasts, risk and NFT fair values. A sentiment engine runs VADER + FinBERT on crypto news.
Everything runs as containers with Docker Compose.

## Reading order

| # | File | Read it for |
|---|------|-------------|
| 1 | [01-overview.md](01-overview.md) | What it is, features, your 60-second pitch |
| 2 | [02-tech-stack.md](02-tech-stack.md) | Every technology, why it was chosen, alternatives |
| 3 | [03-system-design.md](03-system-design.md) | Architecture diagram, components, request flow, folders, deployment |
| 4 | [04-data-and-features.md](04-data-and-features.md) | Database, API endpoints, the 3 key features end to end, auth, errors |
| 5 | [05-challenges-and-interview-prep.md](05-challenges-and-interview-prep.md) | Hard parts, trade-offs, scaling, security, interview Q&A |

**Tip:** Before an interview, read 01 and 05 again. Read 03 and 04 when you want to explain how the code works.

## Where the "source of truth" docs live in the repo

- `DOCKER.md`: how to run the stack.
- `AUDIT_2026-11.md`: a production-readiness audit from 2026-11-02. Some items in it have been fixed since
  (for example, live market data now exists).
- `ml/README.md`, `ml/docs/STATUS.md`, `ml/docs/DECISIONS.md`: the ML service and every ML decision (D-numbers).
- `sentiment_engine/README.md`: the sentiment pipeline.
