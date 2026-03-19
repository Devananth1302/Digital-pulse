"""Hierarchical clustering system for two-stage classification: Cluster -> Sub-topic.

Produces dynamic hierarchical structure with weighted influence scoring.
"""

import logging
from collections import defaultdict
from datetime import datetime, timezone
import numpy as np
from typing import Dict, List, Optional, Tuple

from backend.core.database import get_supabase

logger = logging.getLogger(__name__)

# Meta-clusters: Top-level categories dynamically determined
META_CLUSTERS = {
    "technology": ["ai", "ml", "software", "hardware", "startup", "cybersecurity", "cloud", "blockchain"],
    "finance": ["crypto", "stock", "market", "trading", "investment", "banking", "economy", "finance"],
    "sports": ["athletic", "football", "basketball", "soccer", "esports", "gaming", "sports"],
    "health": ["medical", "health", "disease", "vaccine", "covid", "wellness", "pharma", "mental"],
    "science": ["space", "nasa", "astronomy", "physics", "chemistry", "research", "quantum", "discovery"],
    "politics": ["election", "political", "government", "congress", "senate", "policy", "vote", "campaign"],
    "entertainment": ["movie", "film", "actor", "music", "celebrity", "award", "show", "entertainment"],
    "business": ["company", "corporate", "startup", "merger", "acquisition", "ipo", "business"],
}


class HierarchicalClusterManager:
    """Manages hierarchical clustering with dynamic sub-topics and weighted influence."""

    def __init__(self, db_client=None):
        self.db = db_client or get_supabase()
        self.meta_cluster_cache: Dict[str, List[str]] = {}
        self.influence_weights = {
            "engagement_score": 0.4,
            "velocity_score": 0.3,
            "recency_score": 0.15,
            "semantic_relevance": 0.15,
        }

    def categorize_post(
        self,
        title: str,
        content: str,
        keywords: List[str],
        engagement_metrics: Dict,
    ) -> Tuple[str, str, float]:
        """
        Two-stage classification: Determine meta-cluster and sub-topic.

        Args:
            title: Post title
            content: Post content
            keywords: Extracted keywords
            engagement_metrics: Dict with engagement scoring data

        Returns:
            (meta_cluster_name, sub_topic_name, weighted_influence_score)
        """
        text = f"{title} {content}".lower()
        keywords_lower = [k.lower() for k in keywords]

        # Stage 1: Identify meta-cluster
        meta_cluster = self._determine_meta_cluster(text, keywords_lower)

        # Stage 2: Identify sub-topic within cluster
        sub_topic = self._determine_sub_topic(text, keywords_lower, meta_cluster)

        # Stage 3: Calculate weighted influence
        influence_score = self._calculate_weighted_influence(engagement_metrics, sub_topic)

        return meta_cluster, sub_topic, influence_score

    def _determine_meta_cluster(self, text: str, keywords: List[str]) -> str:
        """Determine which meta-cluster a post belongs to."""
        score_map = defaultdict(float)

        # Match keywords against meta-cluster definitions
        for meta_cluster, keywords_list in META_CLUSTERS.items():
            for keyword in keywords_list:
                if keyword in text:
                    score_map[meta_cluster] += 2.0  # Strong match
                for kw in keywords:
                    if keyword in kw or kw in keyword:
                        score_map[meta_cluster] += 1.0  # Weak match

        # Return highest-scoring cluster, default to "general"
        if score_map:
            return max(score_map, key=score_map.get)
        return "general"

    def _determine_sub_topic(self, text: str, keywords: List[str], meta_cluster: str) -> str:
        """Determine sub-topic within a meta-cluster."""
        # Use most frequent keywords as sub-topic
        if keywords:
            # Prefer keywords that are more specific (longer, more meaningful)
            sorted_keywords = sorted(keywords, key=lambda k: len(k), reverse=True)
            return sorted_keywords[0].title()
        # Fallback to meta-cluster name
        return meta_cluster.title()

    def _calculate_weighted_influence(self, engagement_metrics: Dict, sub_topic: str) -> float:
        """Calculate weighted influence score from multiple factors."""
        score = 0.0

        # Engagement component (0.4 weight)
        engagement_total = engagement_metrics.get("engagement_total", 0)
        engagement_normalized = min(engagement_total / 1000.0, 1.0)  # Normalize to 0-1
        score += engagement_normalized * self.influence_weights["engagement_score"]

        # Velocity component (0.3 weight)
        velocity = engagement_metrics.get("velocity", 0)
        velocity_normalized = min(velocity / 100.0, 1.0)
        score += velocity_normalized * self.influence_weights["velocity_score"]

        # Recency component (0.15 weight)
        timestamp_str = engagement_metrics.get("timestamp", "")
        recency = self._calculate_recency_score(timestamp_str)
        score += recency * self.influence_weights["recency_score"]

        # Semantic relevance (0.15 weight) - assume high by default
        semantic_score = 0.7
        score += semantic_score * self.influence_weights["semantic_relevance"]

        return min(score, 1.0)  # Clamp to 0-1

    def _calculate_recency_score(self, timestamp_str: str) -> float:
        """Calculate recency score from timestamp (0-1)."""
        try:
            if isinstance(timestamp_str, str):
                ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            else:
                ts = timestamp_str

            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)

            hours_old = (datetime.now(timezone.utc) - ts).total_seconds() / 3600.0
            recency = max(0.0, 1.0 - (hours_old / 72.0))  # Decay over 72 hours
            return recency
        except:
            return 0.5  # Default middle score on error

    def build_hierarchical_payload(
        self, posts_with_clusters: List[Dict]
    ) -> Dict[str, Dict]:
        """
        Build hierarchical structure: Meta-Cluster -> Sub-Topics -> Posts

        Args:
            posts_with_clusters: List of posts with cluster and sub_topic fields

        Returns:
            Hierarchical dict:
            {
                "Technology": {
                    "sub_topics": {
                        "AI": {
                            "score": 0.95,
                            "posts": [...],
                            "engagement_stats": {...}
                        },
                        "Cybersecurity": {...}
                    },
                    "total_posts": 150,
                    "avg_influence": 0.75
                },
                ...
            }
        """
        hierarchy = defaultdict(lambda: {"sub_topics": {}, "total_posts": 0, "avg_influence": 0})

        # Build hierarchy
        for post in posts_with_clusters:
            meta_cluster = post.get("meta_cluster", "General")
            sub_topic = post.get("sub_topic", "Other")
            influence_score = post.get("weighted_influence", 0.5)

            # Initialize sub-topic if needed
            if sub_topic not in hierarchy[meta_cluster]["sub_topics"]:
                hierarchy[meta_cluster]["sub_topics"][sub_topic] = {
                    "score": 0,
                    "posts": [],
                    "engagement_stats": {
                        "total_engagement": 0,
                        "avg_velocity": 0,
                        "post_count": 0,
                    },
                    "influence_rank": 0,
                }

            # Add post to sub-topic
            sub_topic_data = hierarchy[meta_cluster]["sub_topics"][sub_topic]
            sub_topic_data["posts"].append(
                {
                    "post_id": post.get("post_id"),
                    "title": post.get("title"),
                    "timestamp": post.get("timestamp"),
                    "engagement_total": post.get("engagement_total", 0),
                    "velocity": post.get("velocity", 0),
                    "influence_score": influence_score,
                }
            )

            # Update stats
            sub_topic_data["engagement_stats"]["total_engagement"] += post.get(
                "engagement_total", 0
            )
            sub_topic_data["engagement_stats"]["avg_velocity"] += post.get("velocity", 0)
            sub_topic_data["engagement_stats"]["post_count"] += 1
            sub_topic_data["score"] = max(
                sub_topic_data["score"], influence_score
            )  # Score = highest influence post

            hierarchy[meta_cluster]["total_posts"] += 1

        # Finalize structure
        result = {}
        for meta_cluster, cluster_data in hierarchy.items():
            # Calculate aggregate influence
            all_scores = []
            for sub_topic_data in cluster_data["sub_topics"].values():
                all_scores.extend([p["influence_score"] for p in sub_topic_data["posts"]])

            cluster_data["avg_influence"] = (
                np.mean(all_scores) if all_scores else 0
            )

            # Rank sub-topics by score
            ranked_subtopics = sorted(
                cluster_data["sub_topics"].items(),
                key=lambda x: x[1]["score"],
                reverse=True,
            )

            cluster_data["sub_topics"] = {
                name: data for name, data in ranked_subtopics
            }

            for rank, (_, sub_topic_data) in enumerate(
                cluster_data["sub_topics"].items(), 1
            ):
                sub_topic_data["influence_rank"] = rank
                if sub_topic_data["engagement_stats"]["post_count"] > 0:
                    sub_topic_data["engagement_stats"]["avg_velocity"] /= (
                        sub_topic_data["engagement_stats"]["post_count"]
                    )

            result[meta_cluster] = cluster_data

        return result

    def get_scoped_trends(
        self, meta_cluster: str, posts_with_clusters: List[Dict]
    ) -> Dict[str, List]:
        """
        Filter trends for a specific cluster.

        Returns:
        {
            "meta_cluster": "Sports",
            "sub_topics": {
                "Football": {
                    "posts": [...],
                    "stats": {...}
                },
                ...
            },
            "breadcrumb": ["General", "Sports"]
        }
        """
        filtered = {
            "meta_cluster": meta_cluster,
            "sub_topics": {},
            "breadcrumb": ["General", meta_cluster],
        }

        # Filter posts for this cluster
        cluster_posts = [
            p for p in posts_with_clusters
            if p.get("meta_cluster", "General").lower() == meta_cluster.lower()
        ]

        # Group by sub-topic
        for post in cluster_posts:
            sub_topic = post.get("sub_topic", "Other")
            if sub_topic not in filtered["sub_topics"]:
                filtered["sub_topics"][sub_topic] = {"posts": [], "stats": {}}

            filtered["sub_topics"][sub_topic]["posts"].append(post)

        # Calculate stats per sub-topic
        for sub_topic_data in filtered["sub_topics"].values():
            posts = sub_topic_data["posts"]
            if posts:
                engagements = [
                    p.get("engagement_total", 0) for p in posts
                ]
                velocities = [p.get("velocity", 0) for p in posts]

                sub_topic_data["stats"] = {
                    "post_count": len(posts),
                    "avg_engagement": np.mean(engagements),
                    "total_engagement": sum(engagements),
                    "avg_velocity": np.mean(velocities),
                    "top_influence": max([p.get("weighted_influence", 0) for p in posts]),
                }

        return filtered

    def get_sub_topic_detail(
        self, meta_cluster: str, sub_topic: str, posts_with_clusters: List[Dict]
    ) -> Dict:
        """Get detailed view of a specific sub-topic."""
        filtered_posts = [
            p
            for p in posts_with_clusters
            if (
                p.get("meta_cluster", "General").lower() == meta_cluster.lower()
                and p.get("sub_topic", "").lower() == sub_topic.lower()
            )
        ]

        # Sort by weighted influence
        filtered_posts.sort(
            key=lambda p: p.get("weighted_influence", 0), reverse=True
        )

        return {
            "meta_cluster": meta_cluster,
            "sub_topic": sub_topic,
            "breadcrumb": ["General", meta_cluster, sub_topic],
            "posts": filtered_posts[:50],  # Top 50 posts
            "stats": {
                "post_count": len(filtered_posts),
                "avg_engagement": (
                    np.mean([p.get("engagement_total", 0) for p in filtered_posts])
                    if filtered_posts
                    else 0
                ),
                "avg_influence": (
                    np.mean([p.get("weighted_influence", 0) for p in filtered_posts])
                    if filtered_posts
                    else 0
                ),
            },
        }
