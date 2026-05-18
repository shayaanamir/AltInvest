// --------------------------------
// USERS
// --------------------------------

export const users = [
  {
    id: 1,
    name: "Shaunak Karve",
    email: "shaunak@example.com",
    password_hash: "$2b$12$8shdkfhsdkjfhsd",
    profile_image:
      "https://cdn.altinvest.com/profiles/user1.png",
    risk_profile: "balanced",
    investment_goal: "market_discovery",
    layout_preference: "analyst",
    created_at: "2026-05-18T10:30:00Z",
  },
  {
    id: 2,
    name: "Aarav Mehta",
    email: "aarav@example.com",
    password_hash: "$2b$12$jfhsd8f7sdf",
    profile_image:
      "https://cdn.altinvest.com/profiles/user2.png",
    risk_profile: "aggressive",
    investment_goal: "active_trading",
    layout_preference: "trader",
    created_at: "2026-05-18T11:10:00Z",
  },
];

// --------------------------------
// ASSETS
// --------------------------------

export const assets = [
  {
    id: 101,
    symbol: "BTC",
    name: "Bitcoin",
    asset_type: "crypto",
    description: "Decentralized digital currency",
    logo_url: "https://cdn.altinvest.com/assets/btc.png",
    market_cap: 1240000000000,
    circulating_supply: 19600000,
    all_time_high: 73750,
    website: "https://bitcoin.org",
    created_at: "2026-05-18T10:30:00Z",
  },
  {
    id: 102,
    symbol: "ETH",
    name: "Ethereum",
    asset_type: "crypto",
    description: "Smart contract blockchain",
    logo_url: "https://cdn.altinvest.com/assets/eth.png",
    market_cap: 410000000000,
    circulating_supply: 120000000,
    all_time_high: 4860,
    website: "https://ethereum.org",
    created_at: "2026-05-18T10:30:00Z",
  },
  {
    id: 103,
    symbol: "SOL",
    name: "Solana",
    asset_type: "crypto",
    description: "High-speed blockchain ecosystem",
    logo_url: "https://cdn.altinvest.com/assets/sol.png",
    market_cap: 68000000000,
    circulating_supply: 460000000,
    all_time_high: 260,
    website: "https://solana.com",
    created_at: "2026-05-18T10:30:00Z",
  },
  {
    id: 104,
    symbol: "BAYC",
    name: "Bored Ape YC",
    asset_type: "nft",
    description: "Popular NFT collection",
    logo_url: "https://cdn.altinvest.com/assets/bayc.png",
    market_cap: 420000000,
    circulating_supply: 10000,
    all_time_high: 153000,
    website: "https://boredapeyachtclub.com",
    created_at: "2026-05-18T10:30:00Z",
  },
];

// --------------------------------
// ASSET MARKET DATA
// --------------------------------

export const assetMarketData = [
  {
    id: 5001,
    asset_id: 101,
    price: 64230,
    market_cap: 1240000000000,
    volume_24h: 32500000000,
    circulating_supply: 19600000,
    ath: 73750,
    market_rank: 1,
    volatility: 68,
    liquidity_score: 94,
    sentiment_score: 88,
    timestamp: "2026-05-18T12:00:00Z",
  },
  {
    id: 5002,
    asset_id: 102,
    price: 3450,
    market_cap: 410000000000,
    volume_24h: 18200000000,
    circulating_supply: 120000000,
    ath: 4860,
    market_rank: 2,
    volatility: 59,
    liquidity_score: 91,
    sentiment_score: 82,
    timestamp: "2026-05-18T12:00:00Z",
  },
  {
    id: 5003,
    asset_id: 103,
    price: 145.8,
    market_cap: 68000000000,
    volume_24h: 5600000000,
    circulating_supply: 460000000,
    ath: 260,
    market_rank: 5,
    volatility: 74,
    liquidity_score: 86,
    sentiment_score: 91,
    timestamp: "2026-05-18T12:00:00Z",
  },
];

// --------------------------------
// ASSET PRICE HISTORY
// --------------------------------

export const assetPricePredictions = [
  { id: 8501, asset_id: 101, timestamp: "2026-05-18T00:00:00Z", price: 64230 },
  { id: 8502, asset_id: 101, timestamp: "2026-05-19T00:00:00Z", price: 65100 },
  { id: 8503, asset_id: 101, timestamp: "2026-05-20T00:00:00Z", price: 65800 },
  { id: 8504, asset_id: 101, timestamp: "2026-05-21T00:00:00Z", price: 67200 },
  { id: 8505, asset_id: 101, timestamp: "2026-05-22T00:00:00Z", price: 66900 },
  { id: 8506, asset_id: 101, timestamp: "2026-05-23T00:00:00Z", price: 68500 },
  { id: 8507, asset_id: 101, timestamp: "2026-05-24T00:00:00Z", price: 71000 }
];

// --------------------------------
// AAI SCORES
// --------------------------------

export const aaiScores = [
  { id: 8601, asset_id: 101, score: -0.85, confidence: 92.4, updated_at: "2026-05-18T12:00:00Z" },
  { id: 8602, asset_id: 102, score: 0.35, confidence: 85.1, updated_at: "2026-05-18T12:00:00Z" },
  { id: 8603, asset_id: 103, score: 0.91, confidence: 94.2, updated_at: "2026-05-18T12:00:00Z" },
  { id: 8604, asset_id: 104, score: -0.45, confidence: 78.5, updated_at: "2026-05-18T12:00:00Z" },
];

// --------------------------------
// ASSET PRICE HISTORY
// --------------------------------

export const assetPriceHistory = [
  {
    id: 8001,
    asset_id: 101,
    price: 64230,
    open: 63000,
    high: 64800,
    low: 62500,
    close: 64230,
    volume: 32000000000,
    timestamp: "2026-05-18T00:00:00Z",
  },
  {
    id: 8002,
    asset_id: 101,
    price: 63100,
    open: 62000,
    high: 63500,
    low: 61800,
    close: 63100,
    volume: 29000000000,
    timestamp: "2026-05-17T00:00:00Z",
  },
  {
    id: 8003,
    asset_id: 102,
    price: 3450,
    open: 3380,
    high: 3480,
    low: 3340,
    close: 3450,
    volume: 17000000000,
    timestamp: "2026-05-18T00:00:00Z",
  },
];

// --------------------------------
// ASSET SENTIMENT
// --------------------------------

// =====================================
// SENTIMENT ENGINE RESPONSE
// =====================================

export const asset_sentiment = [
  {
    asset_id: "btc",

    sentiment_score: 0.5047,

    confidence: 1.0,

    confidence_label: "high",

    signal_strength: "conflicted",

    trend: "stable",

    last_updated: "2026-05-17T14:39:38.461619+00:00",

    article_count: 64,

    source_count: 9,

    source_breakdown: {
      news_nlp: 0.4858,
      market_signals: 0.5488,
    },

    sentiment_distribution: {
      positive: 22,
      negative: 30,
      neutral: 12,
    },

    top_headlines: [
      {
        title:
          "Bitcoin ETF flows reverse as US funds shed $1B amid inflation fears",
        score: -0.951,
        source: "CryptoSlate",
        age_hours: 30.15,
        link:
          "https://cryptoslate.com/bitcoin-etf-flows-reverse-1b-outflows-inflation-fears/",
      },

      {
        title:
          "Institutional accumulation increases as BTC stabilizes above $60K",
        score: 0.842,
        source: "CoinDesk",
        age_hours: 12.4,
        link:
          "https://coindesk.com/markets/institutional-accumulation-btc/",
      },

      {
        title:
          "Bitcoin volatility drops to yearly lows as traders await Fed decision",
        score: 0.102,
        source: "Decrypt",
        age_hours: 8.7,
        link:
          "https://decrypt.co/bitcoin-volatility-fed-decision",
      },
    ],

    market_signals: {
      price_change_24h: -0.1394,
      volume_change_24h: -42.1803,
      is_trending: false,
      btc_dominance: 60.1292,
    },

    articles_by_source: {
      NewsBTC: 10,
      CoinTelegraph: 11,
      AMBCrypto: 6,
      CoinDesk: 7,
      BeInCrypto: 4,
      CryptoSlate: 6,
      "The Block": 4,
      Decrypt: 8,
      "Bitcoin Magazine": 8,
    },
  },

  {
    asset_id: "eth",

    sentiment_score: 0.6721,

    confidence: 0.91,

    confidence_label: "high",

    signal_strength: "bullish",

    trend: "rising",

    last_updated: "2026-05-17T15:02:12.192000+00:00",

    article_count: 52,

    source_count: 8,

    source_breakdown: {
      news_nlp: 0.61,
      market_signals: 0.73,
    },

    sentiment_distribution: {
      positive: 35,
      negative: 9,
      neutral: 8,
    },

    top_headlines: [
      {
        title:
          "Ethereum ETF approval odds rise as institutional demand accelerates",
        score: 0.91,
        source: "CoinTelegraph",
        age_hours: 5.2,
        link:
          "https://cointelegraph.com/news/ethereum-etf-approval-odds",
      },

      {
        title:
          "Ethereum gas fees hit 6-month lows amid network optimization",
        score: 0.51,
        source: "Decrypt",
        age_hours: 9.8,
        link:
          "https://decrypt.co/ethereum-gas-fees-drop",
      },
    ],

    market_signals: {
      price_change_24h: 3.52,
      volume_change_24h: 14.2,
      is_trending: true,
      btc_dominance: null,
    },

    articles_by_source: {
      CoinTelegraph: 9,
      CoinDesk: 6,
      AMBCrypto: 5,
      NewsBTC: 8,
      BeInCrypto: 7,
      Decrypt: 9,
      CryptoSlate: 4,
      "Ethereum Foundation Blog": 4,
    },
  },

  {
    asset_id: "sol",

    sentiment_score: 0.742,

    confidence: 0.88,

    confidence_label: "high",

    signal_strength: "strongly_bullish",

    trend: "rising",

    last_updated: "2026-05-17T15:21:44.102000+00:00",

    article_count: 39,

    source_count: 7,

    source_breakdown: {
      news_nlp: 0.69,
      market_signals: 0.79,
    },

    sentiment_distribution: {
      positive: 28,
      negative: 4,
      neutral: 7,
    },

    top_headlines: [
      {
        title:
          "Solana meme coin ecosystem drives record transaction growth",
        score: 0.94,
        source: "CoinDesk",
        age_hours: 3.1,
        link:
          "https://coindesk.com/markets/solana-memecoin-growth",
      },

      {
        title:
          "Developers continue migrating to Solana amid Ethereum fee concerns",
        score: 0.71,
        source: "Decrypt",
        age_hours: 11.2,
        link:
          "https://decrypt.co/solana-developer-growth",
      },
    ],

    market_signals: {
      price_change_24h: 5.67,
      volume_change_24h: 22.8,
      is_trending: true,
      btc_dominance: null,
    },

    articles_by_source: {
      CoinTelegraph: 7,
      CoinDesk: 6,
      Decrypt: 5,
      NewsBTC: 5,
      CryptoSlate: 4,
      BeInCrypto: 6,
      AMBCrypto: 6,
    },
  },

  {
    asset_id: "bayc",

    sentiment_score: 0.312,

    confidence: 0.79,

    confidence_label: "medium",

    signal_strength: "bearish",

    trend: "falling",

    last_updated: "2026-05-17T15:44:19.551000+00:00",

    article_count: 21,

    source_count: 5,

    source_breakdown: {
      news_nlp: 0.28,
      market_signals: 0.35,
    },

    sentiment_distribution: {
      positive: 3,
      negative: 14,
      neutral: 4,
    },

    top_headlines: [
      {
        title:
          "NFT trading activity drops as liquidity exits blue-chip collections",
        score: -0.87,
        source: "Decrypt",
        age_hours: 6.4,
        link:
          "https://decrypt.co/nft-liquidity-decline",
      },

      {
        title:
          "BAYC floor price hits new yearly lows amid weak market demand",
        score: -0.91,
        source: "CoinTelegraph",
        age_hours: 9.7,
        link:
          "https://cointelegraph.com/news/bayc-floor-price-lows",
      },
    ],

    market_signals: {
      price_change_24h: -4.5,
      volume_change_24h: -31.7,
      is_trending: false,
      btc_dominance: null,
    },

    articles_by_source: {
      CoinTelegraph: 4,
      Decrypt: 5,
      NFTNow: 3,
      BeInCrypto: 4,
      CryptoSlate: 5,
    },
  },
];

// --------------------------------
// SENTIMENT POSTS
// --------------------------------

export const sentimentPosts = [
  {
    id: 12001,
    asset_id: 101,
    platform: "twitter",
    author: "@crypto_whale",
    content:
      "Institutional accumulation on BTC is increasing rapidly.",
    sentiment: "Positive",
    engagement_score: 9200,
    posted_at: "2026-05-18T11:45:00Z",
    url: "https://twitter.com/example/status/123456",
  },
  {
    id: 12002,
    asset_id: 104,
    platform: "reddit",
    author: "u/nft_collector",
    content:
      "NFT liquidity has slowed significantly over the last month.",
    sentiment: "Negative",
    engagement_score: 2400,
    posted_at: "2026-05-18T10:20:00Z",
    url: "https://reddit.com/r/nft/example",
  },
];

// --------------------------------
// MARKET INSIGHTS
// --------------------------------

export const marketInsights = [
  {
    id: 15001,
    title:
      "Institutional inflows push BTC sentiment higher",
    summary:
      "Large wallet activity and ETF demand continue driving bullish sentiment.",
    source: "CryptoBrief",
    impact: "Positive",
    asset_id: 101,
    published_at: "2026-05-18T09:30:00Z",
  },
  {
    id: 15002,
    title:
      "Regulatory concerns impact NFT liquidity",
    summary:
      "NFT trading volume declines as uncertainty around digital asset regulation rises.",
    source: "Block Daily",
    impact: "Negative",
    asset_id: 104,
    published_at: "2026-05-18T07:00:00Z",
  },
    {
    id: 15001,
    title:
      "Institutional inflows push BTC sentiment higher",
    summary:
      "Large wallet activity and ETF demand continue driving bullish sentiment.",
    source: "CryptoBrief",
    impact: "Positive",
    asset_id: 101,
    published_at: "2026-05-18T09:30:00Z",
  },
  {
    id: 15002,
    title:
      "Regulatory concerns impact NFT liquidity",
    summary:
      "NFT trading volume declines as uncertainty around digital asset regulation rises.",
    source: "Block Daily",
    impact: "Negative",
    asset_id: 104,
    published_at: "2026-05-18T07:00:00Z",
  },
    {
    id: 15001,
    title:
      "Institutional inflows push BTC sentiment higher",
    summary:
      "Large wallet activity and ETF demand continue driving bullish sentiment.",
    source: "CryptoBrief",
    impact: "Positive",
    asset_id: 101,
    published_at: "2026-05-18T09:30:00Z",
  },
  {
    id: 15002,
    title:
      "Regulatory concerns impact NFT liquidity",
    summary:
      "NFT trading volume declines as uncertainty around digital asset regulation rises.",
    source: "Block Daily",
    impact: "Negative",
    asset_id: 104,
    published_at: "2026-05-18T07:00:00Z",
  },
];

// --------------------------------
// PORTFOLIOS
// --------------------------------

export const portfolios = [
  {
    id: 2001,
    user_id: 1,
    name: "Main Portfolio",
    created_at: "2026-05-18T10:30:00Z",
  },
  {
    id: 2002,
    user_id: 2,
    name: "Growth Portfolio",
    created_at: "2026-05-18T11:00:00Z",
  },
];

// --------------------------------
// PORTFOLIO HOLDINGS
// --------------------------------

export const portfolioHoldings = [
  {
    id: 3001,
    portfolio_id: 2001,
    asset_id: 101,
    quantity: 0.1557,
    average_buy_price: 58000,
    current_value: 10000,
    allocation_percentage: 42,
    updated_at: "2026-05-18T12:00:00Z",
  },
  {
    id: 3002,
    portfolio_id: 2001,
    asset_id: 102,
    quantity: 2.89,
    average_buy_price: 3100,
    current_value: 10000,
    allocation_percentage: 28,
    updated_at: "2026-05-18T12:00:00Z",
  },
  {
    id: 3003,
    portfolio_id: 2001,
    asset_id: 103,
    quantity: 68.58,
    average_buy_price: 121,
    current_value: 10000,
    allocation_percentage: 18,
    updated_at: "2026-05-18T12:00:00Z",
  },
];

// --------------------------------
// WATCHLISTS
// --------------------------------

export const watchlists = [
  {
    id: 4001,
    user_id: 1,
    asset_id: 101,
    created_at: "2026-05-18T10:45:00Z",
  },
  {
    id: 4002,
    user_id: 1,
    asset_id: 103,
    created_at: "2026-05-18T10:50:00Z",
  },
];

// --------------------------------
// TRENDING ASSETS
// --------------------------------

export const trendingAssets = [
  {
    id: 6001,
    asset_id: 101,
    trend_score: 88,
    movement_percentage: 2.45,
    activity_level: "high",
    updated_at: "2026-05-18T12:00:00Z",
  },
  {
    id: 6002,
    asset_id: 103,
    trend_score: 91,
    movement_percentage: 5.67,
    activity_level: "high",
    updated_at: "2026-05-18T12:00:00Z",
  },
  {
    id: 6003,
    asset_id: 104,
    trend_score: 45,
    movement_percentage: -4.5,
    activity_level: "medium",
    updated_at: "2026-05-18T12:00:00Z",
  },
];

// --------------------------------
// ASSET RISK METRICS
// --------------------------------

export const assetRiskMetrics = [
  {
    id: 7001,
    asset_id: 101,
    volatility_index: 68,
    liquidity_score: 94,
    regulatory_risk: 45,
    market_risk: 62,
    updated_at: "2026-05-18T12:00:00Z",
  },
  {
    id: 7002,
    asset_id: 103,
    volatility_index: 74,
    liquidity_score: 86,
    regulatory_risk: 52,
    market_risk: 70,
    updated_at: "2026-05-18T12:00:00Z",
  },
];

// --------------------------------
// ASSET CATEGORIES
// --------------------------------

export const assetCategories = [
  {
    id: 1,
    name: "Layer 1",
    description:
      "Base blockchain infrastructure assets",
  },
  {
    id: 2,
    name: "NFT",
    description:
      "Non-fungible token collections and ecosystems",
  },
  {
    id: 3,
    name: "RWA",
    description:
      "Real-world asset tokenization projects",
  },
];

// --------------------------------
// ASSET CATEGORY MAPPING
// --------------------------------

export const assetCategoryMapping = [
  {
    id: 1001,
    asset_id: 101,
    category_id: 1,
  },
  {
    id: 1002,
    asset_id: 102,
    category_id: 1,
  },
  {
    id: 1003,
    asset_id: 104,
    category_id: 2,
  },
];

// --------------------------------
// USER ALERTS
// --------------------------------

export const userAlerts = [
  {
    id: 90001,
    user_id: 1,
    asset_id: 101,
    alert_type: "price_above",
    target_value: 70000,
    is_active: true,
    created_at: "2026-05-18T12:00:00Z",
  },
  {
    id: 90002,
    user_id: 1,
    asset_id: 103,
    alert_type: "price_below",
    target_value: 120,
    is_active: true,
    created_at: "2026-05-18T12:00:00Z",
  },
];

// --------------------------------
// PORTFOLIO SNAPSHOTS
// --------------------------------

export const portfolioSnapshots = [
  {
    id: 9501,
    portfolio_id: 2001,
    total_value: 12,
    snapshot_date: "2026-05-18",
  },
  {
    id: 9502,
    portfolio_id: 2001,
    total_value: 10,
    snapshot_date: "2026-05-17",
  },
  {
    id: 9503,
    portfolio_id: 2001,
    total_value: 9,
    snapshot_date: "2026-05-16",
  },
  {
    id: 9504,
    portfolio_id: 2001,
    total_value: 8,
    snapshot_date: "2026-05-17",
  },
];

// --------------------------------
// MARKET EVENTS
// --------------------------------

export const marketEvents = [
  {
    id: 9801,
    title: "SEC approves BTC ETF",
    impact: "Positive",
    event_date: "2026-05-18",
  },
  {
    id: 9802,
    title:
      "Major exchange introduces tokenized commodities",
    impact: "Positive",
    event_date: "2026-05-15",
  },
];

// --------------------------------
// NEWS ARTICLES
// --------------------------------

export const newsArticles = [
  {
    id: 9901,
    title:
      "Solana ecosystem activity surges amid renewed interest",
    source: "CoinDesk",
    url: "https://coindesk.com/example",
    published_at: "2026-05-18T08:00:00Z",
  },
  {
    id: 9902,
    title:
      "Institutional demand for tokenized assets continues rising",
    source: "Bloomberg",
    url: "https://bloomberg.com/example",
    published_at: "2026-05-18T09:15:00Z",
  },
];