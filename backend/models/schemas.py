from pydantic import BaseModel
from typing import Optional


class AssetItem(BaseModel):
    asset: str
    name: str


class PredictionResponse(BaseModel):
    asset: str
    predicted_price: Optional[float]
    prediction_30d: Optional[float]
    confidence: Optional[float]
    model_version: str
    timestamp: str
    note: Optional[str] = None


class SentimentResponse(BaseModel):
    asset: str
    sentiment_score: float          # always in [-1.0, 1.0]
    source: str
    post_count: int
    timestamp: str
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
    risk_score: float
    model_version: str
    timestamp: str


class HealthResponse(BaseModel):
    status: str
    version: str
