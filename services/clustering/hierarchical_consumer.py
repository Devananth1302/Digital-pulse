"""Hierarchical Kafka consumer: Cluster -> Sub-topic -> Posts.

Consumes from 'processed_results' and produces structured hierarchical payloads
to 'trending_signals_hierarchical' for real-time dashboard consumption.
"""

import logging
import json
from typing import Dict, List, Optional
from confluent_kafka import Consumer, Producer
from confluent_kafka.admin import AdminClient, NewTopic

from config.settings import settings
from services.clustering.hierarchical_clustering import HierarchicalClusterManager

logger = logging.getLogger(__name__)


class HierarchicalKafkaConsumer:
    """Consumes processed results and produces hierarchical clustered data."""

    def __init__(self):
        self.consumer_config = {
            "bootstrap.servers": settings.KAFKA_BROKER,
            "group.id": "hierarchical-consumer-group",
            "auto.offset.reset": "latest",
            "enable.auto.commit": True,
            "max.poll.interval.ms": 300000,
        }

        self.producer_config = {
            "bootstrap.servers": settings.KAFKA_BROKER,
            "acks": "all",
        }

        self.cluster_manager = HierarchicalClusterManager()
        self.consumer = None
        self.producer = None
        self.running_buffer: Dict[str, Dict] = {}

    def setup_topics(self):
        """Ensure required Kafka topics exist."""
        admin = AdminClient({"bootstrap.servers": settings.KAFKA_BROKER})

        topics_to_create = [
            NewTopic(
                "trending_signals_hierarchical",
                num_partitions=3,
                replication_factor=1,
                config={
                    "retention.ms": "86400000",  # 24 hours
                    "compression.type": "snappy",
                },
            ),
            NewTopic(
                "cluster_updates",
                num_partitions=2,
                replication_factor=1,
                config={"retention.ms": "3600000"},  # 1 hour
            ),
        ]

        for topic in topics_to_create:
            try:
                admin.create_topics([topic], validate_only=False)
                logger.info(f"Created topic: {topic.name}")
            except Exception as e:
                logger.debug(f"Topic {topic.name} may already exist: {e}")

    def start(self):
        """Start consuming and processing messages."""
        self.setup_topics()
        self.consumer = Consumer(self.consumer_config)
        self.producer = Producer(self.producer_config)

        self.consumer.subscribe(["processed_results"])
        logger.info("✓ Hierarchical consumer started, listening to 'processed_results'")

        try:
            while True:
                msg = self.consumer.poll(timeout=1.0)

                if msg is None:
                    continue

                if msg.error():
                    logger.error(f"Consumer error: {msg.error()}")
                    continue

                self._process_message(msg)

        except KeyboardInterrupt:
            logger.info("Consumer interrupted")
        finally:
            self.consumer.close()
            self.producer.flush()

    def _process_message(self, msg):
        """Process a single message and produce hierarchical output."""
        try:
            data = json.loads(msg.value().decode("utf-8"))

            # Categorize post into cluster/sub-topic
            meta_cluster, sub_topic, influence_score = self.cluster_manager.categorize_post(
                title=data.get("title", ""),
                content=data.get("content", ""),
                keywords=data.get("keywords", []),
                engagement_metrics={
                    "engagement_total": data.get("engagement_total", 0),
                    "velocity": data.get("velocity", 0),
                    "timestamp": data.get("timestamp", ""),
                },
            )

            # Add hierarchical metadata
            enriched_data = {
                **data,
                "meta_cluster": meta_cluster,
                "sub_topic": sub_topic,
                "weighted_influence": influence_score,
                "signal_type": "hierarchical_update",
            }

            # Store in running buffer for windowed aggregation
            self._update_buffer(enriched_data)

            # Produce enriched message
            self.producer.produce(
                "trending_signals_hierarchical",
                key=f"{meta_cluster}#{sub_topic}".encode("utf-8"),
                value=json.dumps(enriched_data).encode("utf-8"),
            )

            # Periodically produce aggregated cluster updates
            if len(self.running_buffer) % 25 == 0:
                self._produce_cluster_summary()

            self.producer.flush()

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def _update_buffer(self, post: Dict):
        """Update running buffer with post data."""
        key = f"{post['meta_cluster']}#{post['sub_topic']}"

        if key not in self.running_buffer:
            self.running_buffer[key] = {
                "meta_cluster": post["meta_cluster"],
                "sub_topic": post["sub_topic"],
                "posts": [],
                "stats": {
                    "total_engagement": 0,
                    "post_count": 0,
                    "avg_influence": 0,
                },
            }

        buffer_entry = self.running_buffer[key]
        buffer_entry["posts"].append(
            {
                "post_id": post.get("post_id"),
                "title": post.get("title"),
                "engagement_total": post.get("engagement_total", 0),
                "velocity": post.get("velocity", 0),
                "weighted_influence": post.get("weighted_influence", 0),
            }
        )

        # Keep only top 20 posts per sub-topic
        if len(buffer_entry["posts"]) > 20:
            buffer_entry["posts"].sort(
                key=lambda p: p["weighted_influence"], reverse=True
            )
            buffer_entry["posts"] = buffer_entry["posts"][:20]

        # Update stats
        buffer_entry["stats"]["post_count"] = len(buffer_entry["posts"])
        buffer_entry["stats"]["total_engagement"] += post.get("engagement_total", 0)
        buffer_entry["stats"]["avg_influence"] = (
            sum(p["weighted_influence"] for p in buffer_entry["posts"])
            / len(buffer_entry["posts"])
            if buffer_entry["posts"]
            else 0
        )

    def _produce_cluster_summary(self):
        """Produce aggregated cluster summaries."""
        try:
            # Group by meta-cluster
            clusters = {}
            for key, topic_data in self.running_buffer.items():
                meta_cluster = topic_data["meta_cluster"]
                if meta_cluster not in clusters:
                    clusters[meta_cluster] = {
                        "meta_cluster": meta_cluster,
                        "sub_topics": {},
                        "total_posts": 0,
                        "avg_influence": 0,
                    }

                clusters[meta_cluster]["sub_topics"][topic_data["sub_topic"]] = {
                    "post_count": topic_data["stats"]["post_count"],
                    "avg_influence": topic_data["stats"]["avg_influence"],
                }
                clusters[meta_cluster]["total_posts"] += topic_data["stats"]["post_count"]

            # Calculate cluster-level influence
            for cluster_data in clusters.values():
                influences = [
                    st["avg_influence"]
                    for st in cluster_data["sub_topics"].values()
                ]
                cluster_data["avg_influence"] = (
                    sum(influences) / len(influences) if influences else 0
                )

            # Produce cluster update
            self.producer.produce(
                "cluster_updates",
                key=b"summary",
                value=json.dumps({
                    "signal_type": "cluster_summary",
                    "clusters": clusters,
                    "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
                }).encode("utf-8"),
            )

            logger.debug(f"Produced cluster summary with {len(clusters)} clusters")

        except Exception as e:
            logger.error(f"Error producing cluster summary: {e}")

    def get_scoped_trends_stream(self, meta_cluster: str):
        """
        Get real-time stream of trends for a specific cluster.
        Useful for drilling down into a specific category.
        """
        logger.info(f"Starting scoped trend stream for cluster: {meta_cluster}")

        self.consumer = Consumer(self.consumer_config)
        self.consumer.subscribe(["trending_signals_hierarchical"])

        try:
            while True:
                msg = self.consumer.poll(timeout=1.0)

                if msg is None:
                    continue

                if msg.error():
                    continue

                data = json.loads(msg.value().decode("utf-8"))

                # Filter for requested cluster only
                if data.get("meta_cluster") == meta_cluster:
                    yield data

        finally:
            self.consumer.close()


def start_hierarchical_consumer():
    """Entry point for hierarchical consumer."""
    consumer = HierarchicalKafkaConsumer()
    consumer.start()


if __name__ == "__main__":
    start_hierarchical_consumer()
