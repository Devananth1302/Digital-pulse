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


# ===== Hierarchical Drill-Down Schemas =====

class HierarchicalPostSummary(BaseModel):
    """Simplified post data for hierarchical views."""
    post_id: str
    title: str
    timestamp: datetime
    engagement_total: float
    velocity: float = 0.0
    influence_score: float
    momentum: Optional[str] = "stable"


class EngagementStats(BaseModel):
    """Engagement statistics for hierarchical groupings."""
    total_engagement: float
    avg_velocity: float
    post_count: int


class SubTopicData(BaseModel):
    """Data for a sub-topic within a cluster."""
    score: float
    posts: List[HierarchicalPostSummary] = []
    engagement_stats: EngagementStats
    influence_rank: int


class HierarchicalCluster(BaseModel):
    """Top-level cluster with sub-topics."""
    meta_cluster: str
    sub_topics: dict[str, SubTopicData]
    total_posts: int
    avg_influence: float


class ScopedTrendsPayload(BaseModel):
    """Payload for scoped trends at cluster level."""
    meta_cluster: str
    sub_topics: dict[str, dict]
    breadcrumb: List[str]


class SubTopicDetailPayload(BaseModel):
    """Detailed payload for a specific sub-topic."""
    meta_cluster: str
    sub_topic: str
    breadcrumb: List[str]
    posts: List[HierarchicalPostSummary]
    stats: dict


class HierarchicalSignal(BaseModel):
    """Enriched signal with hierarchical metadata."""
    post_id: str
    title: str
    content: Optional[str] = None
    timestamp: datetime
    source: str
    engagement_total: float
    velocity: float
    momentum: Optional[str] = "stable"
    
    # Hierarchical fields
    meta_cluster: str
    sub_topic: str
    weighted_influence: float
    signal_type: str = "hierarchical_update"
    
    # Optional engagement breakdown
    likes: int = 0
    shares: int = 0
    comments: int = 0
    
    class Config:
        json_schema_extra = {
            "example": {
                "post_id": "post_123",
                "title": "Breaking: AI Breakthrough",
                "content": "...",
                "timestamp": "2026-03-19T10:30:00Z",
                "source": "news_api",
                "engagement_total": 1250,
                "velocity": 42.5,
                "momentum": "accelerating",
                "meta_cluster": "Technology",
                "sub_topic": "Artificial Intelligence",
                "weighted_influence": 0.89,
                "signal_type": "hierarchical_update",
                "likes": 850,
                "shares": 200,
                "comments": 200,
            }
        }


class ClusterSummary(BaseModel):
    """Summary statistics for a cluster."""
    meta_cluster: str
    post_count: int = 0
    avg_influence: float = 0.0
    top_sub_topics: List[str] = []
    total_engagement: float = 0.0


class HierarchicalDashboardState(BaseModel):
    """Complete state for hierarchical dashboard."""
    clusters: List[HierarchicalCluster]
    top_clusters: List[dict]  # Top 5-10 by influence
    total_posts: int
    timestamp: datetime
    signal_count: int
