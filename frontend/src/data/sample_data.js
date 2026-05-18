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
    volatility: 74,
    liquidity_score: 86,
    sentiment_score: 91,
    timestamp: "2026-05-18T12:00:00Z",
  },
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

export const assetSentiment = [
  {
    id: 9001,
    asset_id: 101,
    positive_score: 72,
    negative_score: 18,
    neutral_score: 10,
    overall_sentiment: "bullish",
    fear_greed_index: 78,
    source_count: 14250,
    timestamp: "2026-05-18T12:00:00Z",
  },
  {
    id: 9002,
    asset_id: 102,
    positive_score: 61,
    negative_score: 24,
    neutral_score: 15,
    overall_sentiment: "neutral",
    fear_greed_index: 63,
    source_count: 9250,
    timestamp: "2026-05-18T12:00:00Z",
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
    sentiment: "positive",
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
    sentiment: "negative",
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
    impact: "positive",
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
    impact: "negative",
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
    total_value: 124600,
    snapshot_date: "2026-05-18",
  },
  {
    id: 9502,
    portfolio_id: 2001,
    total_value: 121200,
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
    impact: "positive",
    event_date: "2026-05-18",
  },
  {
    id: 9802,
    title:
      "Major exchange introduces tokenized commodities",
    impact: "positive",
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