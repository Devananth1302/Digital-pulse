"""Narrative clustering using Sentence Transformers + KMeans fallback.

Uses BERTopic if available, falls back to sklearn KMeans + TF-IDF keywords.
"""

import logging
from collections import Counter
from datetime import datetime, timezone

import numpy as np

from backend.core.database import get_supabase

logger = logging.getLogger(__name__)

# Lazy-loaded models
_embedder = None

# Check BERTopic availability
try:
    from bertopic import BERTopic
    HAS_BERTOPIC = True
except ImportError:
    HAS_BERTOPIC = False
    logger.info("BERTopic not installed, using KMeans fallback clustering")


def _get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder


def generate_embeddings(texts: list[str]) -> np.ndarray:
    """Generate embeddings for a list of texts."""
    model = _get_embedder()
    embeddings = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
    return embeddings


def _extract_keywords(texts: list[str], labels: np.ndarray, n_keywords: int = 5) -> dict[int, list[str]]:
    """Extract top keywords per cluster using word frequency."""
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "need", "dare", "ought",
        "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
        "into", "through", "during", "before", "after", "above", "below",
        "between", "out", "off", "over", "under", "again", "further", "then",
        "once", "and", "but", "or", "nor", "not", "so", "yet", "both",
        "each", "few", "more", "most", "other", "some", "such", "no",
        "only", "own", "same", "than", "too", "very", "just", "because",
        "it", "its", "this", "that", "these", "those", "he", "she", "they",
        "we", "you", "i", "me", "my", "your", "his", "her", "our", "their",
        "who", "what", "which", "when", "where", "how", "all", "any",
        "about", "up", "also", "new", "said", "says", "like", "get",
    }

    cluster_keywords = {}
    unique_labels = set(labels)

    for label in unique_labels:
        if label == -1:
            continue
        mask = labels == label
        cluster_texts = [texts[i] for i in range(len(texts)) if mask[i]]

        # Count words
        word_counts = Counter()
        for text in cluster_texts:
            words = text.lower().split()
            words = [w.strip(".,!?;:'\"()-") for w in words]
            words = [w for w in words if len(w) > 2 and w not in stop_words and w.isalpha()]
            word_counts.update(words)

        cluster_keywords[label] = [w for w, _ in word_counts.most_common(n_keywords)]

    return cluster_keywords


def _kmeans_clustering(embeddings: np.ndarray, n_clusters: int = None) -> np.ndarray:
    """Simple KMeans clustering on embeddings."""
    from sklearn.cluster import KMeans

    n_samples = len(embeddings)
    if n_clusters is None:
        # Heuristic: sqrt(n/2), clamped between 3 and 15
        n_clusters = max(3, min(15, int(np.sqrt(n_samples / 2))))

    n_clusters = min(n_clusters, n_samples)

    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(embeddings)
    return labels


async def run_clustering(posts: list[dict]):
    """Cluster posts into narrative groups.

    Uses BERTopic if available, otherwise falls back to KMeans + keyword extraction.
    """
    if len(posts) < 5:
        logger.info("Not enough posts for clustering (%d)", len(posts))
        return

    db = get_supabase()

    # Prepare texts
    texts = [f"{p.get('title', '')} {p.get('content', '')[:200]}" for p in posts]
    post_ids = [p["post_id"] for p in posts]

    # Generate embeddings
    logger.info("Generating embeddings for %d posts...", len(posts))
    embeddings = generate_embeddings(texts)

    if HAS_BERTOPIC:
        try:
            return await _run_bertopic_clustering(db, posts, texts, post_ids, embeddings)
        except Exception as e:
            logger.warning("BERTopic failed (%s), falling back to KMeans", e)

    # Fallback: KMeans clustering
    await _run_kmeans_clustering(db, posts, texts, post_ids, embeddings)


async def _run_bertopic_clustering(db, posts, texts, post_ids, embeddings):
    """Cluster using BERTopic."""
    topic_model = BERTopic(
        embedding_model=_get_embedder(),
        nr_topics="auto",
        min_topic_size=3,
        verbose=False,
    )
    topics, probs = topic_model.fit_transform(texts, embeddings)

    topic_info = topic_model.get_topic_info()
    cluster_map = {}

    for _, row in topic_info.iterrows():
        topic_id = row["Topic"]
        if topic_id == -1:
            continue

        topic_words = topic_model.get_topic(topic_id)
        keywords = [w for w, _ in topic_words[:10]] if topic_words else []
        label = ", ".join(keywords[:3]) if keywords else f"Topic {topic_id}"

        cluster_posts = [posts[i] for i, t in enumerate(topics) if t == topic_id]
        post_count = len(cluster_posts)
        avg_virality = (
            np.mean([p.get("virality_score", 0) for p in cluster_posts])
            if cluster_posts else 0
        )
        influence = avg_virality * post_count

        cluster_data = {
            "topic_label": label,
            "keywords": keywords,
            "post_count": post_count,
            "influence_score": round(float(influence), 4),
            "avg_virality": round(float(avg_virality), 4),
        }

        result = db.table("narrative_clusters").insert(cluster_data).execute()
        if result.data:
            cluster_map[topic_id] = result.data[0]["cluster_id"]

    for i, topic_id in enumerate(topics):
        if topic_id in cluster_map:
            db.table("posts").update(
                {"cluster_id": cluster_map[topic_id]}
            ).eq("post_id", post_ids[i]).execute()

    logger.info("BERTopic: created %d clusters from %d posts", len(cluster_map), len(posts))


async def _run_kmeans_clustering(db, posts, texts, post_ids, embeddings):
    """Fallback clustering using KMeans + keyword extraction."""
    logger.info("Running KMeans fallback clustering...")

    labels = _kmeans_clustering(embeddings)
    keywords_map = _extract_keywords(texts, labels)

    cluster_map = {}
    unique_labels = set(labels)

    for label in unique_labels:
        if label == -1:
            continue

        keywords = keywords_map.get(label, [])
        topic_label = ", ".join(keywords[:3]) if keywords else f"Topic {label}"

        cluster_posts = [posts[i] for i in range(len(posts)) if labels[i] == label]
        post_count = len(cluster_posts)
        avg_virality = (
            np.mean([p.get("virality_score", 0) for p in cluster_posts])
            if cluster_posts else 0
        )
        influence = avg_virality * post_count

        cluster_data = {
            "topic_label": topic_label,
            "keywords": keywords,
            "post_count": post_count,
            "influence_score": round(float(influence), 4),
            "avg_virality": round(float(avg_virality), 4),
        }

        try:
            result = db.table("narrative_clusters").insert(cluster_data).execute()
            if result.data:
                cluster_map[label] = result.data[0]["cluster_id"]
        except Exception as e:
            logger.error("Failed to insert cluster %d: %s", label, e)

    # Update posts with cluster IDs
    for i, label in enumerate(labels):
        if label in cluster_map:
            try:
                db.table("posts").update(
                    {"cluster_id": cluster_map[label]}
                ).eq("post_id", post_ids[i]).execute()
            except Exception as e:
                logger.error("Failed to update post cluster: %s", e)

    logger.info("KMeans: created %d clusters from %d posts", len(cluster_map), len(posts))
