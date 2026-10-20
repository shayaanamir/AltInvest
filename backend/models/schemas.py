from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
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
    # Only the title is guaranteed: feeds omit links and timestamps, and a pipeline
    # that found nothing returns no headlines at all.
    title: str
    score: Optional[float] = None                   # blended VADER + FinBERT score
    contribution: Optional[float] = None            # this headline's share of the news score
    vader_score: Optional[float] = None
    finbert_score: Optional[float] = None
    source: Optional[str] = None
    age_hours: Optional[float] = None
    link: Optional[str] = None


class SentimentDistribution(BaseModel):
    positive: int
    negative: int
    neutral: int


class MarketSignals(BaseModel):
    # Every field is optional: the market-data source can be down or rate-limited, in which
    # case the engine returns none of them (and a neutral result has none to give).
    price_change_24h: Optional[float] = None
    volume_change_24h: Optional[float] = None
    is_trending: Optional[bool] = None
    btc_dominance: Optional[float] = None


class DataQuality(BaseModel):
    # Which inputs fell back to placeholders. Older stored records carry only
    # degraded / cmc_fallback, so everything is optional.
    degraded: Optional[bool] = None
    cmc_fallback: Optional[bool] = None
    quote_fallback: Optional[bool] = None
    global_fallback: Optional[bool] = None
    trending_fallback: Optional[bool] = None
    cmc_key_missing: Optional[bool] = None
    finbert_unavailable: Optional[bool] = None
    reason: Optional[str] = None


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
    data_quality: Optional[DataQuality] = None
    error: Optional[str] = None
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
    aai_score: Optional[float] = None       # [0, 100]; null when the prediction or risk score is missing
    pred_score: Optional[float] = None
    expected_return_30d: Optional[float] = None
    sentiment_score: float
    sentiment_confidence: Optional[float] = None
    sentiment_available: Optional[bool] = None      # False: no recent sentiment, neutral 50 was used
    sentiment_note: Optional[str] = None
    risk_score: Optional[float] = None
    missing_inputs: List[str] = []
    note: Optional[str] = None
    model_version: Optional[str] = None
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
    url: Optional[str] = None            # link to the original article, when the insight has one
    related_asset_symbol: Optional[str] = None
    related_nft_slug: Optional[str] = None
    published_at: str


class DashboardStats(BaseModel):
    portfolio_value_usd: float
    volume_24h_usd: float
    global_sentiment: float
    global_sentiment_label: str
    holdings_count: int = 0
    assets_count: int = 0
    collections_count: int = 0
    crypto_score_count: int = 0
    nft_score_count: int = 0
    market_mood_confidence: Optional[float] = None   # avg sentiment confidence, 0-100
    unpriced_holding_count: int = 0                  # holdings left out of portfolio_value_usd (no price)
    sentiment_asset_count: int = 0                   # assets behind global_sentiment


class PortfolioHoldingIn(BaseModel):
    asset_type: str
    symbol: Optional[str] = None
    nft_collection_slug: Optional[str] = None
    nft_token_id: Optional[str] = None
    # Numbers only, finite, and sensible: a holding is valued as price * quantity.
    quantity: float = Field(gt=0, allow_inf_nan=False)
    avg_buy_price_usd: Optional[float] = Field(None, ge=0, allow_inf_nan=False)
    avg_buy_price_eth: Optional[float] = Field(None, ge=0, allow_inf_nan=False)
    avg_buy_eth_usd_rate: Optional[float] = Field(None, ge=0, allow_inf_nan=False)
    cost_basis_usd: Optional[float] = Field(None, ge=0, allow_inf_nan=False)


class PortfolioHoldingPatch(BaseModel):
    """The fields PATCH /portfolio/holdings/{id} can change. Omitted or null fields are left alone."""
    quantity: Optional[float] = Field(None, gt=0, allow_inf_nan=False)
    avg_buy_price_usd: Optional[float] = Field(None, ge=0, allow_inf_nan=False)
    avg_buy_price_eth: Optional[float] = Field(None, ge=0, allow_inf_nan=False)
    avg_buy_eth_usd_rate: Optional[float] = Field(None, ge=0, allow_inf_nan=False)
    cost_basis_usd: Optional[float] = Field(None, ge=0, allow_inf_nan=False)


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
    quantity: Optional[float] = None                # None only for a stored row with an unreadable quantity
    avg_buy_price_usd: Optional[float] = None
    avg_buy_price_eth: Optional[float] = None
    avg_buy_eth_usd_rate: Optional[float] = None
    cost_basis_usd: Optional[float] = None
    current_price: Optional[float] = None
    current_value_usd: Optional[float] = None       # None when it can't be valued; never a made-up 0
    unrealised_pnl_usd: Optional[float] = None
    unrealised_pnl_pct: Optional[float] = None
    valuation_status: Optional[str] = None          # "ok" | "no_price" | "invalid_quantity" | "unsupported_type"
    date_added: Optional[str] = None
    updated_at: Optional[str] = None


class PortfolioSummary(BaseModel):
    # Value, cost basis and P&L cover only the holdings that could be valued, so they stay
    # comparable. unpriced_holding_count says how many were left out; holding_count is all of them.
    total_value_usd: float
    total_cost_basis_usd: float
    total_unrealised_pnl_usd: float
    total_unrealised_pnl_pct: Optional[float] = None
    holding_count: int
    unpriced_holding_count: int = 0


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
    subcategory: Optional[str] = None
    logo_color: Optional[str] = None
    price: Optional[float] = None   # crypto price or nft floor_usd
    floor_eth: Optional[float] = None        # nft only
    change_24h: Optional[float] = None
    change_7d: Optional[float] = None
    market_cap: Optional[float] = None
    volume_24h: Optional[float] = None
    aai_score: Optional[float] = None
    signal: Optional[str] = None             # BUY | HOLD | SELL, derived from aai_score
    risk_score: Optional[float] = None
    volatility: Optional[float] = None       # crypto: volatility_index, nft: illiquidity risk
    expected_return: Optional[float] = None  # predicted 30d %, crypto only
    sentiment_score: Optional[float] = None
    sentiment_confidence: Optional[float] = None
    sentiment_confidence_label: Optional[str] = None
    sentiment_trend: Optional[str] = None
    verified: Optional[bool] = None          # nft only
    held: bool = False
    watching: bool = False
    sparkline: List[float] = []


class CompareItem(DiscoverItem):
    pass


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
    investment_goal: Optional[str] = None
    email_verified: Optional[bool] = None
    created_at: Optional[str] = None
    activity_summary: ActivitySummary


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    investment_goal: Optional[str] = None
    bio: Optional[str] = None
    avatar_initials: Optional[str] = None
    avatar_color: Optional[str] = None
    risk_profile: Optional[str] = None
    layout_preference: Optional[str] = None
    display_currency: Optional[str] = None


class FxRatesOut(BaseModel):
    base: str
    rates: Dict[str, float]
    as_of: str
    source: Optional[str] = None
    supported: List[str]


# ── Settings PATCH bodies, one per section ───────────────────────────────────
# Unknown keys are rejected (extra="forbid"), so a typo or a stray key can't be written into a
# user's settings document. Fields left out or null are not changed.

class _SettingsPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PreferencesPatch(_SettingsPatch):
    display_currency: Optional[str] = Field(None, max_length=8)   # checked against the supported list in the route
    date_format: Optional[Literal["MM/DD/YYYY", "DD/MM/YYYY", "YYYY-MM-DD"]] = None
    default_landing_page: Optional[Literal["Dashboard", "Portfolio", "Sentiment"]] = None
    default_dashboard_layout: Optional[Literal["minimal", "analyst", "trader", "ai-first"]] = None


class AppearancePatch(_SettingsPatch):
    theme: Optional[Literal["dark", "light"]] = None
    density: Optional[Literal["comfortable", "compact"]] = None


class NotificationChannelsPatch(_SettingsPatch):
    inApp: Optional[bool] = None
    push: Optional[bool] = None
    email: Optional[bool] = None


class NotificationAlertTypesPatch(_SettingsPatch):
    aaiThresholdOnly: Optional[bool] = None
    priceAlerts: Optional[bool] = None
    sentimentShifts: Optional[bool] = None
    minorPriceWiggles: Optional[bool] = None
    marketNews: Optional[bool] = None
    systemMessages: Optional[bool] = None


class QuietHoursPatch(_SettingsPatch):
    enabled: Optional[bool] = None
    start: Optional[str] = Field(None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    end: Optional[str] = Field(None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    timezone: Optional[str] = Field(None, max_length=64)


class NotificationsPatch(_SettingsPatch):
    channels: Optional[NotificationChannelsPatch] = None
    alert_types: Optional[NotificationAlertTypesPatch] = None
    quiet_hours: Optional[QuietHoursPatch] = None


class SecurityPatch(_SettingsPatch):
    two_factor_enabled: Optional[bool] = None


class ConnectedAccountsPatch(_SettingsPatch):
    google: Optional[bool] = None
    github: Optional[bool] = None
    wallet: Optional[bool] = None


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


class VerifyEmailRequest(BaseModel):
    token: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str