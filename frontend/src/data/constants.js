export const NAV_ITEMS = [
  { icon: "⊞", label: "Dashboard", active: true },
  { icon: "✦", label: "AI Copilot", badge: "NEW" },
  { icon: "↗", label: "Asset Detail" },
  { icon: "◉", label: "Sentiment" },
  { icon: "⬡", label: "AI Prediction" },
  { icon: "⊕", label: "Market Map" },
  { icon: "◈", label: "Portfolio" },
];

export const BOTTOM_NAV = [
  { icon: "⚙", label: "Settings" },
  { icon: "→", label: "Logout" },
];

export const STATS = [
  { label: "Total Portfolio Value", value: "$124,600", change: "▲ 2.65%", positive: true },
  { label: "24h Volume (Alt)",      value: "$42.50B",  change: "▼ 5.2%",  positive: false },
  { label: "Global AAI Sentiment",  value: "78.00/100",change: "▲ 2.1%",  positive: true },
];

export const INSIGHTS = [
  { source: "AltInvest AI", time: "2h ago", headline: "AI models predict strong Q3 for layer-1 protocols", impact: "positive" },
  { source: "CryptoBrief",  time: "4h ago", headline: "Regulatory concerns impact NFT liquidity",           impact: "negative" },
  { source: "Block Daily",  time: "5h ago", headline: "Institutional inflows to tokenized real estate hit ATH", impact: "positive" },
  { source: "MarketWatch",  time: "7h ago", headline: "Bitcoin volatility drops to 6-month low",            impact: "neutral" },
];

export const TRENDING_ASSETS = [
  { sym: "BTC",    name: "Bitcoin",      cat: "Crypto", price: "$64,230", chg: "+2.45%", pos: true,  score: 88, sig: "Up",   data: [42,44,41,46,48,45,50,52,49,54,55,53,57,58,56,60,61,59,63,62,64] },
  { sym: "ETH",    name: "Ethereum",     cat: "Crypto", price: "$3,450",  chg: "-1.2%",  pos: false, score: 82, sig: "Hold", data: [52,54,56,53,55,58,56,54,52,50,51,49,50,52,50,48,49,47,48,46,47] },
  { sym: "SOL",    name: "Solana",       cat: "Crypto", price: "$145.8",  chg: "+5.67%", pos: true,  score: 91, sig: "Up",   data: [38,40,39,42,44,43,46,48,47,50,52,51,54,56,55,58,60,59,62,64,66] },
  { sym: "BAY YC", name: "Bored Ape YC", cat: "NFT",    price: "$42,500", chg: "-4.5%",  pos: false, score: 45, sig: "Down", data: [70,68,66,65,67,64,62,60,58,56,55,53,51,50,48,46,45,44,42,41,40] },
];

export const PERFORMANCE_DATA = [42,38,55,48,60,52,68,58,72,65,80,74,88,78,95,82,105,88,115,98,124.6];

export const TIME_FILTERS = ["1D", "1W", "1M", "3M", "1Y", "ALL"];
