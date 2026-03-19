"""Hierarchical Clustering Engine - Two-tier classification system.

Tier 1: Industry Classification (Zero-Shot)
- Maps content to major industries: Tech, Finance, Healthcare, Media, Sports, etc.
- Uses pre-trained Zero-Shot models (lightweight, no fine-tuning needed)

Tier 2: Sub-topic Detection (LDA-based)
- Identifies specific topics within each industry
- Captures domain-specific sub-categories
"""

import logging
from typing import Dict, Any, List, Tuple, Optional
import json

logger = logging.getLogger(__name__)

# Zero-Shot classification candidate labels (industries)
DEFAULT_INDUSTRIES = [
    "Technology",
    "Finance",
    "Healthcare",
    "Media",
    "Sports",
    "Entertainment",
    "Business",
    "Politics",
    "Education",
    "Science",
    "Real Estate",
    "E-commerce",
    "Travel",
    "Food & Beverage",
    "Fashion",
    "Automotive",
    "Manufacturing",
    "Energy",
    "Telecommunications",
    "Other"
]


class HierarchicalClusteringEngine:
    """Multi-tier clustering: Industry → Sub-topic."""
    
    def __init__(self):
        """Initialize clustering engine with zero-shot model."""
        self.industries = DEFAULT_INDUSTRIES
        self.industry_subtopics = self._initialize_subtopic_mappings()
        
        # Lazy-load zero-shot model
        self.zero_shot_model = None
        self.lda_models = {}
        
    def _initialize_subtopic_mappings(self) -> Dict[str, List[str]]:
        """Map industries to typical sub-topics."""
        return {
            "Technology": [
                "artificial_intelligence",
                "cloud_computing",
                "cybersecurity",
                "mobile_apps",
                "software_development",
                "hardware",
                "startups",
                "venture_capital",
                "data_science",
                "quantum_computing",
            ],
            "Finance": [
                "stock_market",
                "cryptocurrency",
                "banking",
                "insurance",
                "real_estate",
                "investments",
                "fx_trading",
                "commodities",
                "bond_market",
                "fintech",
            ],
            "Healthcare": [
                "pharmaceuticals",
                "medical_devices",
                "telemedicine",
                "clinical_trials",
                "mental_health",
                "nutrition",
                "fitness",
                "medical_technology",
                "public_health",
                "rare_diseases",
            ],
            "Media": [
                "journalism",
                "broadcasting",
                "streaming",
                "podcast",
                "content_creation",
                "social_media",
                "advertising",
                "publishing",
                "news_aggregation",
                "entertainment_news",
            ],
            "Sports": [
                "football",
                "basketball",
                "soccer",
                "baseball",
                "hockey",
                "tennis",
                "golf",
                "esports",
                "extreme_sports",
                "sports_analytics",
            ],
            "Other": [
                "general",
                "miscellaneous",
                "uncategorized",
            ]
        }
    
    def _get_zero_shot_model(self):
        """Lazy-load zero-shot classification model."""
        if self.zero_shot_model is None:
            try:
                from transformers import pipeline
                logger.info("Loading zero-shot classification model...")
                self.zero_shot_model = pipeline(
                    "zero-shot-classification",
                    model="facebook/bart-large-mnli",
                    device=-1  # CPU; use 0 for GPU
                )
            except ImportError:
                logger.error("transformers library not installed. Install with: pip install transformers")
                raise
        
        return self.zero_shot_model
    
    def classify_industry(self, text: str) -> Tuple[str, float]:
        """
        Classify content into industry using Zero-Shot.
        
        Args:
            text: Content text (title + content combined)
            
        Returns:
            (industry_name, confidence_score)
        """
        if not text or len(text.strip()) == 0:
            return "Other", 0.0
        
        try:
            model = self._get_zero_shot_model()
            
            result = model(text, self.industries, multi_class=False)
            
            industry = result['labels'][0]
            score = result['scores'][0]
            
            return industry, round(float(score), 4)
        
        except Exception as e:
            logger.warning(f"Zero-shot classification error: {e}")
            return "Other", 0.0
    
    def detect_subtopic(self, text: str, industry: str) -> Tuple[str, List[str]]:
        """
        Detect sub-topic within industry using keyword matching + heuristics.
        
        In production, this would use:
        - Fine-tuned LDA models per industry
        - Domain-specific keyword vocabularies
        - BERTopic for automatic topic extraction
        
        Args:
            text: Content text
            industry: Parent industry
            
        Returns:
            (primary_subtopic, all_detected_subtopics)
        """
        text_lower = text.lower()
        
        # Get valid subtopics for this industry
        subtopic_list = self.industry_subtopics.get(industry, ["general"])
        
        # Simple keyword-based detection (can be replaced with LDA)
        text_words = set(text_lower.split())
        
        detected = []
        for subtopic in subtopic_list:
            # Check if subtopic name appears (with underscore handling)
            subtopic_keywords = subtopic.replace("_", " ").split()
            
            # Count keyword matches
            matches = sum(1 for kw in subtopic_keywords if kw in text_words)
            
            if matches > 0 or any(kw in text_lower for kw in subtopic_keywords):
                detected.append(subtopic)
        
        # If no subtopic detected, use first one as default
        if not detected:
            detected = [subtopic_list[0]]
        
        primary_subtopic = detected[0]
        
        return primary_subtopic, detected
    
    def cluster_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Two-tier hierarchical clustering.
        
        Args:
            data: Record with title and content
            
        Returns:
            Record with cluster labels added
        """
        # Combine text for classification
        title = data.get('title', '')
        content = data.get('content', '')
        text = f"{title} {content}"
        
        # Tier 1: Industry classification
        industry, industry_score = self.classify_industry(text)
        
        # Tier 2: Sub-topic detection
        subtopic, subtopics_detected = self.detect_subtopic(text, industry)
        
        # Add clustering results
        result = {
            **data,
            
            # Tier 1: Industry
            'industry': industry,
            'industry_score': industry_score,
            
            # Tier 2: Sub-topic
            'subtopic': subtopic,
            'subtopics_detected': subtopics_detected,
            
            # For multi-assignment tracking
            'subtopic_count': len(subtopics_detected),
            
            # Clustering timestamp
            'clustered_at': datetime.now(timezone.utc).isoformat(),
        }
        
        logger.debug(f"Clustering: post_id={data.get('post_id')}, industry={industry}, subtopic={subtopic}")
        return result


# Singleton instance
_clustering_engine = None


def get_clustering_engine() -> HierarchicalClusteringEngine:
    """Get or create singleton clustering engine."""
    global _clustering_engine
    if _clustering_engine is None:
        _clustering_engine = HierarchicalClusteringEngine()
    return _clustering_engine


if __name__ == "__main__":
    from datetime import datetime, timezone
    
    # Test the clustering engine
    logging.basicConfig(level=logging.INFO)
    
    engine = get_clustering_engine()
    
    test_records = [
        {
            "post_id": "test_1",
            "title": "Apple releases new M3 chip",
            "content": "Apple announced the latest M3 processor with improved AI capabilities",
        },
        {
            "post_id": "test_2",
            "title": "FDA approves new cancer drug",
            "content": "The FDA has approved a groundbreaking immunotherapy for treating advanced melanoma",
        },
        {
            "post_id": "test_3",
            "title": "Bitcoin surges above $50k",
            "content": "Cryptocurrency market rallies following positive regulatory news",
        },
    ]
    
    for record in test_records:
        clustered = engine.cluster_record(record)
        print(f"Post: {clustered['title']}")
        print(f"  Industry: {clustered['industry']} (score: {clustered['industry_score']})")
        print(f"  Subtopic: {clustered['subtopic']}")
        print(f"  All subtopics: {clustered['subtopics_detected']}")
        print()
