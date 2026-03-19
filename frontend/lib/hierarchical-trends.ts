/**
 * Hierarchical Trends - TypeScript utilities for drill-down analytics
 * Handles dynamically filtering and deriving hierarchical trends data
 */

import { TrendingSignal } from './websocket-service';

/**
 * Hierarchical data structure from Kafka
 */
export interface HierarchicalCluster {
  meta_cluster: string;
  sub_topics: Record<string, SubTopicData>;
  total_posts: number;
  avg_influence: number;
}

export interface SubTopicData {
  score: number;
  posts: TrendingSignal[];
  engagement_stats: {
    total_engagement: number;
    avg_velocity: number;
    post_count: number;
  };
  influence_rank: number;
}

export interface ScopedTrendsResult {
  meta_cluster: string;
  sub_topics: Record<string, SubTopicDetail>;
  breadcrumb: string[];
}

export interface SubTopicDetail {
  score: number;
  influence_rank: number;
  posts: TrendingSignal[];
  engagement_stats: {
    total_engagement: number;
    avg_velocity: number;
    post_count: number;
  };
  stats?: {
    post_count: number;
    avg_engagement: number;
    total_engagement: number;
    avg_velocity: number;
    top_influence: number;
  };
}

export interface SubTopicDetailResult {
  meta_cluster: string;
  sub_topic: string;
  breadcrumb: string[];
  posts: TrendingSignal[];
  stats: {
    post_count: number;
    avg_engagement: number;
    avg_influence: number;
  };
}

export interface BreadcrumbItem {
  label: string;
  level: 'cluster' | 'subtopic' | 'post';
  value?: string;
}

/**
 * Get all available meta-clusters from trending signals
 */
export function getClusters(signals: TrendingSignal[]): string[] {
  const clusters: string[] = [];
  const seen = new Set<string>();
  
  signals.forEach(signal => {
    if (signal.industry && !seen.has(signal.industry)) {
      clusters.push(signal.industry);
      seen.add(signal.industry);
    }
  });

  return clusters.sort();
}

/**
 * Main drill-down function: Filter scoped trends for a specific cluster
 * Returns sub-topics with filtered posts and statistics
 */
export function getScopedTrends(
  clusterName: string,
  signals: TrendingSignal[]
): ScopedTrendsResult {
  // Filter signals for this cluster
  const clusterSignals = signals.filter(
    (signal) => signal.industry?.toLowerCase() === clusterName.toLowerCase()
  );

  // Group by sub-topic
  const subTopicsMap: Record<string, SubTopicDetail> = {};

  clusterSignals.forEach((signal) => {
    const subTopic = signal.subtopic || 'Other';

    if (!subTopicsMap[subTopic]) {
      subTopicsMap[subTopic] = {
        score: 0,
        influence_rank: 0,
        posts: [],
        engagement_stats: {
          total_engagement: 0,
          avg_velocity: 0,
          post_count: 0,
        },
        stats: {
          post_count: 0,
          avg_engagement: 0,
          total_engagement: 0,
          avg_velocity: 0,
          top_influence: 0,
        },
      };
    }

    subTopicsMap[subTopic].posts.push(signal);
  });

  // Calculate statistics for each sub-topic
  let index = 0;
  Object.values(subTopicsMap).forEach((subTopic) => {
    const posts = subTopic.posts;

    if (posts.length > 0) {
      const engagements = posts.map((p) => p.engagement_total || 0);
      const velocities = posts.map((p) => p.velocity || 0);
      const influences = posts.map((p) => (p.momentum ? scoreFromMomentum(p.momentum) : 0.5));

      const accEngagement = engagements.reduce((a, b) => a + b, 0);
      const accVelocity = velocities.reduce((a, b) => a + b, 0);
      const maxInfluence = Math.max(...influences, 0);

      subTopic.engagement_stats = {
        total_engagement: accEngagement,
        avg_velocity: accVelocity / posts.length,
        post_count: posts.length,
      };

      subTopic.stats = {
        post_count: posts.length,
        avg_engagement: accEngagement / posts.length,
        total_engagement: accEngagement,
        avg_velocity: accVelocity / posts.length,
        top_influence: maxInfluence,
      };

      subTopic.score = maxInfluence;
      subTopic.influence_rank = ++index;

      // Sort posts by engagement
      subTopic.posts.sort(
        (a, b) => (b.engagement_total || 0) - (a.engagement_total || 0)
      );
    }
  });

  // Sort sub-topics by influence/engagement
  const sortedSubTopics = Object.entries(subTopicsMap)
    .sort(
      ([, a], [, b]) =>
        b.score - a.score ||
        b.engagement_stats.total_engagement - a.engagement_stats.total_engagement
    )
    .reduce((acc, [key, val]) => ({ ...acc, [key]: val }), {});

  return {
    meta_cluster: clusterName,
    sub_topics: sortedSubTopics,
    breadcrumb: ['Dashboard', clusterName],
  };
}

/**
 * Get detailed view of a specific sub-topic within a cluster
 */
export function getSubTopicDetail(
  clusterName: string,
  subTopic: string,
  signals: TrendingSignal[]
): SubTopicDetailResult {
  // Filter for specific cluster and sub-topic
  const filtered = signals.filter(
    (signal) =>
      signal.industry?.toLowerCase() === clusterName.toLowerCase() &&
      signal.subtopic?.toLowerCase() === subTopic.toLowerCase()
  );

  // Sort by engagement and influence
  filtered.sort(
    (a, b) =>
      (b.engagement_total || 0) - (a.engagement_total || 0) ||
      (b.velocity || 0) - (a.velocity || 0)
  );

  // Calculate statistics
  const postCount = filtered.length;
  const avgEngagement =
    filtered.length > 0
      ? filtered.reduce((sum, p) => sum + (p.engagement_total || 0), 0) /
        filtered.length
      : 0;
  const avgInfluence =
    filtered.length > 0
      ? filtered.reduce(
          (sum, p) =>
            sum + (p.momentum ? scoreFromMomentum(p.momentum) : 0.5),
          0
        ) / filtered.length
      : 0;

  return {
    meta_cluster: clusterName,
    sub_topic: subTopic,
    breadcrumb: ['Dashboard', clusterName, subTopic],
    posts: filtered.slice(0, 50), // Top 50 posts
    stats: {
      post_count: postCount,
      avg_engagement: avgEngagement,
      avg_influence: avgInfluence,
    },
  };
}

/**
 * Build complete hierarchical structure from signals
 */
export function buildHierarchy(
  signals: TrendingSignal[]
): Record<string, Record<string, SubTopicDetail>> {
  const hierarchy: Record<string, Record<string, SubTopicDetail>> = {};

  signals.forEach((signal) => {
    const cluster = signal.industry || 'General';
    const subTopic = signal.subtopic || 'Other';

    if (!hierarchy[cluster]) {
      hierarchy[cluster] = {};
    }

    if (!hierarchy[cluster][subTopic]) {
      hierarchy[cluster][subTopic] = {
        score: 0,
        influence_rank: 0,
        posts: [],
        engagement_stats: {
          total_engagement: 0,
          avg_velocity: 0,
          post_count: 0,
        },
        stats: {
          post_count: 0,
          avg_engagement: 0,
          total_engagement: 0,
          avg_velocity: 0,
          top_influence: 0,
        },
      };
    }

    hierarchy[cluster][subTopic].posts.push(signal);
  });

  // Calculate stats
  Object.values(hierarchy).forEach((clusterData) => {
    let index = 0;
    Object.values(clusterData).forEach((subTopicData) => {
      const posts = subTopicData.posts;
      if (posts.length > 0) {
        const engagements = posts.map((p) => p.engagement_total || 0);
        const velocities = posts.map((p) => p.velocity || 0);
        const influences = posts.map((p) =>
          p.momentum ? scoreFromMomentum(p.momentum) : 0.5
        );

        const totalEngage = engagements.reduce((a, b) => a + b, 0);
        const avgVel = velocities.reduce((a, b) => a + b, 0) / posts.length;
        const maxInfl = Math.max(...influences, 0);

        subTopicData.engagement_stats = {
          total_engagement: totalEngage,
          avg_velocity: avgVel,
          post_count: posts.length,
        };

        subTopicData.stats = {
          post_count: posts.length,
          avg_engagement: totalEngage / posts.length,
          total_engagement: totalEngage,
          avg_velocity: avgVel,
          top_influence: maxInfl,
        };

        subTopicData.score = maxInfl;
        subTopicData.influence_rank = ++index;

        // Sort posts
        subTopicData.posts.sort(
          (a, b) => (b.engagement_total || 0) - (a.engagement_total || 0)
        );
      }
    });
  });

  return hierarchy;
}

/**
 * Get top N trending clusters ranked by influence
 */
export function getTopClusters(
  signals: TrendingSignal[],
  limit: number = 5
): { cluster: string; influence: number; postCount: number }[] {
  const clusterStats: Record<string, { influence: number; posts: number }> = {};

  signals.forEach((signal) => {
    const cluster = signal.industry || 'General';
    const influence = signal.trending_score || scoreFromMomentum(signal.momentum || 'stable');

    if (!clusterStats[cluster]) {
      clusterStats[cluster] = { influence: 0, posts: 0 };
    }

    const stats = clusterStats[cluster];
    stats.influence = Math.max(stats.influence, influence);
    stats.posts += 1;
  });

  return Object.entries(clusterStats)
    .map(([cluster, stats]) => ({
      cluster,
      influence: stats.influence,
      postCount: stats.posts,
    }))
    .sort((a, b) => b.influence - a.influence)
    .slice(0, limit);
}

/**
 * Helper: Convert momentum string to numeric score (0-1)
 */
export function scoreFromMomentum(momentum: string): number {
  const scores: Record<string, number> = {
    accelerating: 0.95,
    rising: 0.75,
    stable: 0.5,
    declining: 0.25,
    collapsing: 0.05,
  };
  return scores[momentum.toLowerCase()] || 0.5;
}

/**
 * Helper: Create breadcrumb navigation items
 */
export function createBreadcrumbs(
  level: 'cluster' | 'subtopic',
  cluster: string,
  subTopic?: string
): BreadcrumbItem[] {
  const items: BreadcrumbItem[] = [
    { label: 'Dashboard', level: 'cluster', value: 'home' },
    { label: cluster, level: 'cluster', value: cluster },
  ];

  if (level === 'subtopic' && subTopic) {
    items.push({ label: subTopic, level: 'subtopic', value: subTopic });
  }

  return items;
}

/**
 * Memoizable version of getScopedTrends for React performance
 * Used with useMemo to prevent unnecessary recalculations
 */
export function createMemoizedGetScopedTrends() {
  const cache = new Map<string, ScopedTrendsResult>();

  return (clusterName: string, signals: TrendingSignal[]): ScopedTrendsResult => {
    // Simple cache key
    const key = `${clusterName}:${signals.length}`;

    if (cache.has(key)) {
      return cache.get(key)!;
    }

    const result = getScopedTrends(clusterName, signals);
    cache.set(key, result);

    // Limit cache size
    if (cache.size > 20) {
      const firstKey = cache.keys().next().value;
      if (firstKey) {
        cache.delete(firstKey);
      }
    }

    return result;
  };
}

/**
 * Performance helper: Check if hierarchy needs rebuild
 */
export function shouldRebuildHierarchy(
  oldSignals: TrendingSignal[],
  newSignals: TrendingSignal[]
): boolean {
  // Rebuild if signal count changed significantly or new clusters detected
  if (Math.abs(oldSignals.length - newSignals.length) > 10) {
    return true;
  }

  const oldClusters = new Set(oldSignals.map((s) => s.industry));
  const newClusters = new Set(newSignals.map((s) => s.industry));

  // Check if any new clusters detected
  for (const cluster of newClusters) {
    if (!oldClusters.has(cluster)) {
      return true;
    }
  }

  return false;
}
