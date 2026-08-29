from pydantic import BaseModel
from typing import Optional, Dict, List


class AssetItem(BaseModel):
    asset: str
    name: str


class PredictionResponse(BaseModel):
    asset: str
    predicted_price: Optional[float]
    prediction_30d: Optional[float]
    confidence: Optional[float]
    model_version: Optional[str]
    timestamp: str
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    risk_score: Optional[float] = None
    trend: Optional[str] = None
    agreement: Optional[bool] = None
    signal: Optional[str] = None
    boosted_confidence: Optional[float] = None
    ensemble_price: Optional[float] = None
    note: Optional[str] = None

class HeadlineItem(BaseModel):
    title: str
    score: float
    source: str
    age_hours: float
    link: str


class SentimentDistribution(BaseModel):
    positive: int
    negative: int
    neutral: int


class MarketSignals(BaseModel):
    price_change_24h: float
    volume_change_24h: float
    is_trending: bool
    btc_dominance: float


class SentimentResponse(BaseModel):
    asset: str
    sentiment_score: float                          # maps to their sentiment_score
    source: str
    post_count: int                                 # maps to their article_count
    timestamp: str
    # --- extended fields from Person D's engine ---
    confidence: Optional[float] = None
    confidence_label: Optional[str] = None
    signal_strength: Optional[str] = None
    trend: Optional[str] = None
    source_count: Optional[int] = None
    source_breakdown: Optional[Dict[str, float]] = None
    sentiment_distribution: Optional[SentimentDistribution] = None
    top_headlines: Optional[List[HeadlineItem]] = None
    market_signals: Optional[MarketSignals] = None
    articles_by_source: Optional[Dict[str, int]] = None
    note: Optional[str] = None

class RiskResponse(BaseModel):
    asset: str
    risk_score: float               # always in [0, 100]
    volatility: Optional[float]
    sharpe_ratio: Optional[float]
    timestamp: str
    note: Optional[str] = None


class AAIResponse(BaseModel):
    asset: str
    aai_score: float                # always clamped to [0, 100]
    pred_score: float
    sentiment_score: float
    sentiment_confidence: Optional[float] = None
    risk_score: float
    model_version: str
    timestamp: str


class HealthResponse(BaseModel):
    status: str
    version: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthUser(BaseModel):
    id: str
    name: str
    email: str


class AuthResponse(BaseModel):
    user: AuthUser
    token: str


class AssetHeader(BaseModel):
    asset_id: str
    symbol: str
    name: str
    category: str
    subcategory: Optional[str] = None
    logo_color: Optional[str] = None
    logo_url: Optional[str] = None
    price: Optional[float] = None
    change_24h: Optional[float] = None
    market_cap: Optional[float] = None
    market_rank: Optional[int] = None


class MarketInsightItem(BaseModel):
    source: str
    title: str
    summary: str
    impact: str
    related_asset_symbol: Optional[str] = None
    related_nft_slug: Optional[str] = None
    published_at: str


class DashboardStats(BaseModel):
    portfolio_value_usd: float
    volume_24h_usd: float
    global_sentiment: float
    global_sentiment_label: str


class PortfolioHoldingIn(BaseModel):
    asset_type: str
    symbol: Optional[str] = None
    nft_collection_slug: Optional[str] = None
    nft_token_id: Optional[str] = None
    quantity: float
    avg_buy_price_usd: Optional[float] = None
    avg_buy_price_eth: Optional[float] = None
    avg_buy_eth_usd_rate: Optional[float] = None
    cost_basis_usd: Optional[float] = None


class WatchlistCreate(BaseModel):
    name: str


class WatchlistItemIn(BaseModel):
    type: str
    symbol_or_slug: str


class AlertCreate(BaseModel):
    target_type: str
    target_symbol: Optional[str] = None
    target_slug: Optional[str] = None
    target_name: str
    metric_type: str
    condition: str
    threshold_value: Optional[float] = None
    delivery_channel: str = "in-app"


class AlertUpdate(BaseModel):
    status: Optional[str] = None
    threshold_value: Optional[float] = None
    condition: Optional[str] = None
    delivery_channel: Optional[str] = None


class SignupRequest(BaseModel):
    email: str
    password: str
    name: str


class PortfolioHoldingOut(BaseModel):
    id: str
    user_id: str
    asset_type: str
    symbol: Optional[str] = None
    name: Optional[str] = None
    nft_collection_slug: Optional[str] = None
    nft_token_id: Optional[str] = None
    quantity: float
    avg_buy_price_usd: Optional[float] = None
    avg_buy_price_eth: Optional[float] = None
    avg_buy_eth_usd_rate: Optional[float] = None
    cost_basis_usd: Optional[float] = None
    current_price: Optional[float] = None
    current_value_usd: Optional[float] = None
    unrealised_pnl_usd: Optional[float] = None
    unrealised_pnl_pct: Optional[float] = None
    date_added: Optional[str] = None
    updated_at: Optional[str] = None


class PortfolioSummary(BaseModel):
    total_value_usd: float
    total_cost_basis_usd: float
    total_unrealised_pnl_usd: float
    total_unrealised_pnl_pct: Optional[float] = None
    holding_count: int


class AllocationSlice(BaseModel):
    label: str
    value_usd: float
    pct_of_portfolio: float


class WatchlistItemOut(BaseModel):
    type: str
    symbol_or_slug: str
    added_at: Optional[str] = None
    # enriched at read time
    name: Optional[str] = None
    price: Optional[float] = None
    change_24h: Optional[float] = None
    aai_score: Optional[float] = None


class WatchlistOut(BaseModel):
    id: str
    user_id: str
    name: str
    created_at: Optional[str] = None
    items: List[WatchlistItemOut] = []


class AlertOut(BaseModel):
    id: str
    user_id: str
    target_type: str
    target_symbol: Optional[str] = None
    target_slug: Optional[str] = None
    target_name: str
    metric_type: str
    condition: str
    threshold_value: Optional[float] = None
    status: str
    delivery_channel: str
    created_at: Optional[str] = None
    last_triggered_at: Optional[str] = None
    last_observed_value: Optional[float] = None


class NotificationOut(BaseModel):
    id: str
    user_id: str
    type: str
    title: str
    message: str
    read: bool
    timestamp: Optional[str] = None
    deep_link: Optional[Dict] = None

class NFTCollectionListItem(BaseModel):
    slug: str
    name: str
    symbol: str
    subcategory: Optional[str] = None
    banner_color: Optional[str] = None
    verified: bool
    supply: int
    floor_eth: Optional[float] = None
    floor_usd: Optional[float] = None
    change_24h: Optional[float] = None
    change_7d: Optional[float] = None
    volume_24h_eth: Optional[float] = None
    holders_count: Optional[int] = None


class NFTTraitDistributionItem(BaseModel):
    trait: str
    value: str
    rarity_pct: float


class NFTCollectionDetail(BaseModel):
    slug: str
    name: str
    symbol: str
    subcategory: Optional[str] = None
    description: Optional[str] = None
    banner_color: Optional[str] = None
    verified: bool
    supply: int
    market: Optional[Dict] = None
    holder_stats: Optional[Dict] = None
    liquidity: Optional[Dict] = None
    risk_breakdown: Optional[Dict] = None
    trait_categories: List[str] = []
    recent_sales: List[Dict] = []
    aai_score: Optional[float] = None


class NFTTokenTrait(BaseModel):
    category: str
    value: str
    rarity_pct: float


class NFTTokenDetail(BaseModel):
    slug: str
    token_id: str
    rarity_rank: Optional[int] = None
    rarity_score: Optional[float] = None
    listed_price_eth: Optional[float] = None
    image_description: Optional[str] = None
    image_url: Optional[str] = None
    owner_address: Optional[str] = None
    traits: List[NFTTokenTrait] = []
    sale_history: List[Dict] = []
    ownership_history: List[Dict] = []

class DiscoverItem(BaseModel):
    category: str                   # "crypto" | "nft"
    id: str                         # asset_id or slug
    symbol: Optional[str] = None
    name: str
    logo_color: Optional[str] = None
    price: Optional[float] = None   # crypto price or nft floor_usd
    change_24h: Optional[float] = None
    change_7d: Optional[float] = None
    market_cap: Optional[float] = None       # crypto only
    volume_24h: Optional[float] = None
    aai_score: Optional[float] = None
    verified: Optional[bool] = None          # nft only


class CompareItem(BaseModel):
    category: str
    id: str
    name: str
    price: Optional[float] = None
    change_24h: Optional[float] = None
    change_7d: Optional[float] = None
    aai_score: Optional[float] = None
    risk_score: Optional[float] = None
    sentiment_score: Optional[float] = None


class CompareResponse(BaseModel):
    items: List[CompareItem]
    verdict: str


class SearchResults(BaseModel):
    assets: List[Dict]
    nft_collections: List[Dict]
    insights: List[Dict]

class ActivitySummary(BaseModel):
    holdings_count: int
    watchlists_count: int
    alerts_count: int
    active_alerts_count: int


class ProfileOut(BaseModel):
    id: str
    email: str
    name: str
    avatar_initials: Optional[str] = None
    avatar_color: Optional[str] = None
    bio: Optional[str] = None
    risk_profile: Optional[str] = None
    layout_preference: Optional[str] = None
    display_currency: Optional[str] = None
    email_verified: Optional[bool] = None
    created_at: Optional[str] = None
    activity_summary: ActivitySummary


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    bio: Optional[str] = None
    avatar_initials: Optional[str] = None
    avatar_color: Optional[str] = None
    risk_profile: Optional[str] = None
    layout_preference: Optional[str] = None
    display_currency: Optional[str] = None


class UserSettingsOut(BaseModel):
    user_id: str
    preferences: Optional[Dict] = None
    appearance: Optional[Dict] = None
    notifications: Optional[Dict] = None
    security: Optional[Dict] = None
    connected_accounts: Optional[Dict] = None


class SettingsSectionUpdate(BaseModel):
    section: str
    payload: Dict


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str