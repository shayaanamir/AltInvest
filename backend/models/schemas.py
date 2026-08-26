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
