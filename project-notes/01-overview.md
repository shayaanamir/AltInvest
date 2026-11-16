# 01: Overview

## What it is (explain it to a friend)

AltInvest is like a smart dashboard for crypto and NFTs. It pulls live prices, reads the news and runs
ML models. Then it gives each asset one simple score from 0 to 100. You can also track your own
portfolio, watch assets and get alerts when something changes.

## The problem it solves

- Alternative assets (crypto, NFTs) are noisy. Prices jump, news is everywhere and hype is hard to separate from signal.
- A normal investor has to check many sites: price trackers, news, NFT marketplaces and risk tools.
- AltInvest puts all of this in one place and sums it up in one explainable score (the **AAI score**).
  It also says openly when a number is weak or missing.

**Who uses it:** retail investors who hold or are curious about crypto and NFTs. TODO: confirm the target
user (students? a college demo audience? real retail users?).

## Main features (one line each)

- **Sign up / sign in**: email + password, or Google sign-in; email verification and password reset.
- **Onboarding**: a 5-step wizard (markets, risk style, goals, assets, layout) (`OnboardingPage.jsx`).
- **Dashboard**: portfolio value, performance chart, market insights, trending assets and NFT collections.
- **AAI score**: one 0-100 score per asset. 40% ML forecast + 30% sentiment + 30% risk.
- **Asset detail page**: price chart, market stats, risk, sentiment, AAI breakdown, similar assets.
- **NFT collection page**: floor price, risk, sentiment and an ML **fair-value estimate** for one NFT.
- **Discover**: filter and sort the whole asset universe (crypto + NFTs).
- **Compare**: put assets side by side (AAI, risk vs return, sentiment).
- **Sentiment hub**: the market "mood" gauge, mood trend, themes and the headlines that drove the score.
- **Portfolio**: add crypto/NFT holdings, buy/sell, profit and loss, allocation, "portfolio intelligence"
  (diversification, concentration, aggregate risk).
- **Watchlists**: named lists of assets to follow.
- **Alerts**: rules like "BTC price above 80,000". Checked every 5 minutes, sent in-app or by email.
- **Notifications, Profile, Settings**: theme, display currency (USD/EUR/GBP/INR/JPY), sessions, connected accounts.
- **Global search**: search assets, collections and news, with recent-search history.

## 60-second answer: "Tell me about your project"

> "AltInvest is an analytics platform for alternative assets: crypto and NFTs. The problem is that
> these markets are noisy, and investors jump between price sites, news and NFT marketplaces. We built
> one place that combines three signals into a single 0-to-100 score we call the AAI score. The three are
> a machine-learning forecast, news sentiment and a volatility-based risk score.
>
> The frontend is React with Vite. The main backend is FastAPI on MongoDB. Two Python services sit
> beside it. One is a sentiment engine that scores news with VADER and FinBERT, and uses an LLM on Groq
> for NFT news. The other is an ML service that serves forecasts, risk scores and an NFT fair-value
> model built with LightGBM. Background jobs pull live data from CoinGecko, Binance, OpenSea and news
> feeds. Everything runs in Docker Compose.
>
> One thing I'm proud of is that we were honest about the ML. We tested every model against simple
> baselines on a sealed test set. When a model didn't beat the baseline, we served the baseline and
> said so in the UI. The NFT fair-value model did pass: about 2.9% median error against 3.5% for the
> best baseline."

(Change the last part to match your own role. See below.)

## My Role

- TODO: My title/role on the team (e.g. "ML lead", "full-stack").
- TODO: Team size and who did what.
  - Hint from git history: `shail-712` (the git user on this machine) made about 152 of the ~155 commits
    in `ml/`. `shauncode24` made most frontend, backend and all sentiment-engine commits. Shayaan Amir
    worked on backend, db and frontend. Confirm this.
- TODO: The 2-3 things I personally built end to end.
- TODO: One hard bug or decision I owned, and what I learned.
- TODO: Project dates (git history runs from 2026-04-18 to 2026-11-16), and whether this is a
  final-year college project.
