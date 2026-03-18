from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class PostBase(BaseModel):
    post_id: str
    title: str
    content: str
    timestamp: datetime
    source: str
    likes: int = 0
    shares: int = 0
    comments: int = 0
    region: Optional[str] = None


class PostCreate(PostBase):
    pass


class PostInDB(PostBase):
    id: int
    engagement_total: float = 0.0
    engagement_velocity: float = 0.0
    time_decay: float = 1.0
    virality_score: float = 0.0
    cluster_id: Optional[int] = None
    embedding: Optional[List[float]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NarrativeCluster(BaseModel):
    cluster_id: int
    topic_label: str
    keywords: List[str] = []
    post_count: int = 0
    influence_score: float = 0.0
    avg_virality: float = 0.0
    created_at: datetime
    representative_posts: List[PostInDB] = []


class EmergingSignal(BaseModel):
    id: int
    cluster_id: Optional[int] = None
    topic: str
    growth_rate: float
    current_engagement: float
    previous_engagement: float
    detected_at: datetime
    severity: str = "medium"  # low, medium, high


class PulseScore(BaseModel):
    score: float = Field(ge=0, le=100)
    breakdown: dict
    top_narratives: List[str] = []
    trend_direction: str = "stable"  # rising, falling, stable
    timestamp: datetime


class ForecastResult(BaseModel):
    topic: str
    trend_prediction: str  # rising, falling, stable
    confidence_score: float = Field(ge=0, le=1)
    predicted_engagement: float
    forecast_hours: int = 48
    data_points: List[dict] = []


class ViralityBreakdown(BaseModel):
    post_id: str
    shares_component: float
    comments_component: float
    likes_component: float
    velocity_component: float
    total_score: float
    explanation: str
