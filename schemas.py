from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# =========================
# PRODUCT INFO
# =========================

class ProductInfo(BaseModel):
    asin: str
    name: str
    image: Optional[str] = None
    rating: Optional[float] = None
    number_of_ratings: Optional[int] = None


# =========================
# REGRET / RISK
# =========================

class RegretScore(BaseModel):
    score: float
    risk_level: str   # "Low" | "Medium" | "High"
    color: str        # "green" | "orange" | "red"


# =========================
# DECISION INTELLIGENCE
# =========================

class DecisionIntelligence(BaseModel):
    purchase_confidence: float


# =========================
# ADVANCED INSIGHTS
# =========================

class Distribution(BaseModel):
    low: float
    medium: float
    high: float


class AdvancedInsights(BaseModel):
    distribution: Distribution
    variance: float


# =========================
# EVIDENCE (REVIEWS)
# =========================

class Evidence(BaseModel):
    top_negative: List[str]
    top_positive: List[str]


# =========================
# FULL ANALYZE RESPONSE
# =========================

class AnalyzeResponse(BaseModel):
    product: ProductInfo
    regret: RegretScore
    decision_intelligence: DecisionIntelligence
    advanced_insights: AdvancedInsights
    recommendation: str
    evidence: Evidence


# =========================
# PENDING RESPONSE
# (product not in dataset yet)
# =========================

class PendingResponse(BaseModel):
    status: str
    asin: str
    message: str


# =========================
# HISTORY RECORD
# =========================

class HistoryRecord(BaseModel):
    asin: str
    product_name: str
    product_image: Optional[str] = None
    regret_percentage: float
    recommendation: str
    analyzed_at: datetime

    class Config:
        from_attributes = True
