/**
 * Performance-optimized React hooks for hierarchical drill-down
 * Includes memoization, performance monitoring, and efficient updates
 */

import { useEffect, useState, useCallback, useMemo, useRef } from 'react';
import { TrendingSignal } from './websocket-service';
import {
  getScopedTrends,
  getSubTopicDetail,
  getTopClusters,
  buildHierarchy,
  shouldRebuildHierarchy,
  ScopedTrendsResult,
  SubTopicDetailResult,
} from './hierarchical-trends';

/**
 * Main hook: Manage hierarchical drill-down state and derived data
 * Optimized with memoization to prevent unnecessary recalculations
 */
export function useHierarchicalDrillDown(signals: TrendingSignal[]) {
  const [drillLevel, setDrillLevel] = useState<'clusters' | 'subtopics' | 'posts'>('clusters');
  const [selectedCluster, setSelectedCluster] = useState<string | null>(null);
  const [selectedSubTopic, setSelectedSubTopic] = useState<string | null>(null);

  // Track previous signals for change detection
  const prevSignalsRef = useRef<TrendingSignal[]>([]);

  // Memoized top clusters (recalculates only when signals change significantly)
  const topClusters = useMemo(() => {
    const needsRebuild = shouldRebuildHierarchy(prevSignalsRef.current, signals);
    if (needsRebuild) {
      prevSignalsRef.current = signals;
      return getTopClusters(signals, 10);
    }
    return getTopClusters(signals, 10);
  }, [signals]);

  // Memoized scoped trends for selected cluster
  const scopedTrends = useMemo(() => {
    if (!selectedCluster) return null;
    return getScopedTrends(selectedCluster, signals);
  }, [selectedCluster, signals]);

  // Memoized sub-topic detail
  const subTopicDetail = useMemo(() => {
    if (!selectedCluster || !selectedSubTopic) return null;
    return getSubTopicDetail(selectedCluster, selectedSubTopic, signals);
  }, [selectedCluster, selectedSubTopic, signals]);

  // Navigation callbacks
  const selectCluster = useCallback((cluster: string) => {
    setSelectedCluster(cluster);
    setSelectedSubTopic(null);
    setDrillLevel('subtopics');
  }, []);

  const selectSubTopic = useCallback((subTopic: string) => {
    setSelectedSubTopic(subTopic);
    setDrillLevel('posts');
  }, []);

  const goBack = useCallback(() => {
    if (drillLevel === 'posts') {
      setSelectedSubTopic(null);
      setDrillLevel('subtopics');
    } else if (drillLevel === 'subtopics') {
      setSelectedCluster(null);
      setDrillLevel('clusters');
    }
  }, [drillLevel]);

  const goHome = useCallback(() => {
    setSelectedCluster(null);
    setSelectedSubTopic(null);
    setDrillLevel('clusters');
  }, []);

  return {
    drillLevel,
    selectedCluster,
    selectedSubTopic,
    topClusters,
    scopedTrends,
    subTopicDetail,
    selectCluster,
    selectSubTopic,
    goBack,
    goHome,
  };
}

/**
 * Hook: Get real-time hierarchical hierarchy structure
 * Returns memoized hierarchy that only updates when necessary
 */
export function useHierarchy(signals: TrendingSignal[]) {
  const [hierarchy, setHierarchy] = useState<Record<string, Record<string, any>>>({});
  const prevSignalsLengthRef = useRef(0);

  useEffect(() => {
    // Only rebuild if signal count changed significantly
    if (Math.abs(signals.length - prevSignalsLengthRef.current) > 5) {
      const newHierarchy = buildHierarchy(signals);
      setHierarchy(newHierarchy);
      prevSignalsLengthRef.current = signals.length;
    }
  }, [signals]);

  return hierarchy;
}

/**
 * Hook: Performance monitoring for drill-down operations
 */
interface PerformanceMetrics {
  clusterFetchTime: number;
  subTopicFetchTime: number;
  postsFetchTime: number;
  totalRenderTime: number;
}

export function useHierarchicalPerformance() {
  const [metrics, setMetrics] = useState<PerformanceMetrics>({
    clusterFetchTime: 0,
    subTopicFetchTime: 0,
    postsFetchTime: 0,
    totalRenderTime: 0,
  });

  const measureOperation = useCallback(
    (operation: keyof PerformanceMetrics, fn: () => void) => {
      const start = performance.now();
      fn();
      const duration = performance.now() - start;

      setMetrics((prev) => ({
        ...prev,
        [operation]: duration,
      }));

      // Log if slow
      if (duration > 100) {
        console.warn(`Slow hierarchical operation: ${operation} took ${duration.toFixed(2)}ms`);
      }

      return duration;
    },
    []
  );

  return { metrics, measureOperation };
}

/**
 * Hook: Manage breadcrumb state for navigation
 */
export interface BreadcrumbState {
  level: 'clusters' | 'subtopics' | 'posts';
  cluster?: string;
  subTopic?: string;
}

export function useBreadcrumbs() {
  const [breadcrumbs, setBreadcrumbs] = useState<BreadcrumbState[]>([
    { level: 'clusters' },
  ]);

  const push = useCallback(
    (level: 'clusters' | 'subtopics' | 'posts', cluster?: string, subTopic?: string) => {
      setBreadcrumbs((prev) => [...prev, { level, cluster, subTopic }]);
    },
    []
  );

  const pop = useCallback(() => {
    setBreadcrumbs((prev) => (prev.length > 1 ? prev.slice(0, -1) : prev));
  }, []);

  const goToLevel = useCallback((index: number) => {
    setBreadcrumbs((prev) => prev.slice(0, index + 1));
  }, []);

  const reset = useCallback(() => {
    setBreadcrumbs([{ level: 'clusters' }]);
  }, []);

  return {
    breadcrumbs,
    current: breadcrumbs[breadcrumbs.length - 1],
    push,
    pop,
    goToLevel,
    reset,
  };
}

/**
 * Hook: Debounced cluster updates
 * Prevents rapid re-renders from streaming updates
 */
export function useDebouncedClusterUpdate(
  signals: TrendingSignal[],
  delay: number = 500
) {
  const [debouncedSignals, setDebouncedSignals] = useState(signals);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    // Clear existing timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    // Set new timeout
    timeoutRef.current = setTimeout(() => {
      setDebouncedSignals(signals);
    }, delay);

    // Cleanup
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [signals, delay]);

  return debouncedSignals;
}

/**
 * Hook: Track which clusters have been viewed
 * Useful for analytics or caching
 */
export function useClusterViewTracking() {
  const [viewedClusters, setViewedClusters] = useState<string[]>([]);
  const [viewedSubTopics, setViewedSubTopics] = useState<Record<string, string[]>>({});

  const trackClusterView = useCallback((cluster: string) => {
    setViewedClusters((prev) => 
      prev.includes(cluster) ? prev : [...prev, cluster]
    );
  }, []);

  const trackSubTopicView = useCallback((cluster: string, subTopic: string) => {
    setViewedSubTopics((prev) => {
      const subTopics = prev[cluster] || [];
      return {
        ...prev,
        [cluster]: subTopics.includes(subTopic) ? subTopics : [...subTopics, subTopic]
      };
    });
  }, []);

  const isClusterViewed = useCallback(
    (cluster: string) => viewedClusters.includes(cluster),
    [viewedClusters]
  );

  const isSubTopicViewed = useCallback(
    (cluster: string, subTopic: string) => {
      const subTopics = viewedSubTopics[cluster];
      return subTopics ? subTopics.includes(subTopic) : false;
    },
    [viewedSubTopics]
  );

  return {
    viewedClusters,
    viewedSubTopics,
    trackClusterView,
    trackSubTopicView,
    isClusterViewed,
    isSubTopicViewed,
  };
}

/**
 * Hook: Manage drill-down animation state
 * Ensures smooth transitions between levels
 */
export function useDrillDownAnimation() {
  const [isAnimating, setIsAnimating] = useState(false);

  const animate = useCallback(async (duration: number = 300) => {
    setIsAnimating(true);
    await new Promise((resolve) => setTimeout(resolve, duration));
    setIsAnimating(false);
  }, []);

  return { isAnimating, animate };
}

/**
 * Hook: Cache scoped trends to avoid recalculation
 */
export function useScopedTrendsCache() {
  const cacheRef = useRef<Map<string, ScopedTrendsResult>>(new Map());

  const getScopedTrendsCached = useCallback(
    (cluster: string, signals: TrendingSignal[]): ScopedTrendsResult => {
      const key = `${cluster}:${signals.length}`;

      if (cacheRef.current.has(key)) {
        return cacheRef.current.get(key)!;
      }

      const result = getScopedTrends(cluster, signals);
      cacheRef.current.set(key, result);

      // Limit cache size to 20 entries
      if (cacheRef.current.size > 20) {
        const firstKey = cacheRef.current.keys().next().value;
        if (firstKey) {
          cacheRef.current.delete(firstKey);
        }
      }

      return result;
    },
    []
  );

  const clearCache = useCallback(() => {
    cacheRef.current.clear();
  }, []);

  return { getScopedTrendsCached, clearCache };
}

/**
 * Combined hook: Use all hierarchical features
 */
export function useHierarchicalDashboard(signals: TrendingSignal[]) {
  const drill = useHierarchicalDrillDown(signals);
  const hierarchy = useHierarchy(signals);
  const performance = useHierarchicalPerformance();
  const breadcrumbs = useBreadcrumbs();
  const viewTracking = useClusterViewTracking();
  const animation = useDrillDownAnimation();
  const trendsCache = useScopedTrendsCache();

  return {
    drill,
    hierarchy,
    performance,
    breadcrumbs,
    viewTracking,
    animation,
    trendsCache,
  };
}
