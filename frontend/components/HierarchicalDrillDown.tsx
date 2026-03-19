'use client';

/**
 * Hierarchical Drill-Down Dashboard Component
 * Level 1: Top Clusters (Industries)
 * Level 2: Sub-Topics within cluster
 * Level 3: Detailed posts for sub-topic
 *
 * Features:
 * - Smooth Framer Motion transitions between levels
 * - Breadcrumb navigation
 * - Real-time updates with performance optimization
 * - Icons for visual differentiation
 */

import React, { useState, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronRight, Home, TrendingUp, ArrowUp, ArrowDown } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { StatBadge } from '@/components/ui/stat-badge';
import {
  getScopedTrends,
  getSubTopicDetail,
  getTopClusters,
  buildHierarchy,
  scoreFromMomentum,
  BreadcrumbItem,
  createBreadcrumbs,
  ScopedTrendsResult,
  SubTopicDetailResult,
} from '@/lib/hierarchical-trends';
import { TrendingSignal } from '@/lib/websocket-service';
import { cn } from '@/lib/utils';

interface HierarchicalDrillDownProps {
  signals: TrendingSignal[];
  isLoading?: boolean;
}

type DrillLevel = 'clusters' | 'subtopics' | 'posts';

export const HierarchicalDrillDown: React.FC<HierarchicalDrillDownProps> = ({
  signals,
  isLoading = false,
}) => {
  // Navigation state
  const [drillLevel, setDrillLevel] = useState<DrillLevel>('clusters');
  const [selectedCluster, setSelectedCluster] = useState<string | null>(null);
  const [selectedSubTopic, setSelectedSubTopic] = useState<string | null>(null);

  // Memoized computed values
  const topClusters = useMemo(() => getTopClusters(signals, 10), [signals]);

  const scopedTrends = useMemo(() => {
    if (!selectedCluster) return null;
    return getScopedTrends(selectedCluster, signals);
  }, [selectedCluster, signals]);

  const subTopicDetail = useMemo(() => {
    if (!selectedCluster || !selectedSubTopic) return null;
    return getSubTopicDetail(selectedCluster, selectedSubTopic, signals);
  }, [selectedCluster, selectedSubTopic, signals]);

  // Navigation handlers
  const handleClusterClick = useCallback((cluster: string) => {
    setSelectedCluster(cluster);
    setSelectedSubTopic(null);
    setDrillLevel('subtopics');
  }, []);

  const handleSubTopicClick = useCallback((subTopic: string) => {
    setSelectedSubTopic(subTopic);
    setDrillLevel('posts');
  }, []);

  const handleBack = useCallback(() => {
    if (drillLevel === 'posts') {
      setSelectedSubTopic(null);
      setDrillLevel('subtopics');
    } else if (drillLevel === 'subtopics') {
      setSelectedCluster(null);
      setDrillLevel('clusters');
    }
  }, [drillLevel]);

  const handleHome = useCallback(() => {
    setSelectedCluster(null);
    setSelectedSubTopic(null);
    setDrillLevel('clusters');
  }, []);

  return (
    <div className="w-full space-y-6">
      {/* Breadcrumb Navigation */}
      <Breadcrumb
        level={drillLevel}
        cluster={selectedCluster}
        subTopic={selectedSubTopic}
        onHome={handleHome}
        onBack={handleBack}
      />

      {/* Animated Content Container */}
      <AnimatePresence mode="wait">
        {drillLevel === 'clusters' && (
          <ClustersView
            key="clusters"
            clusters={topClusters}
            onSelectCluster={handleClusterClick}
            isLoading={isLoading}
          />
        )}

        {drillLevel === 'subtopics' && scopedTrends && (
          <SubTopicsView
            key="subtopics"
            scopedTrends={scopedTrends}
            onSelectSubTopic={handleSubTopicClick}
          />
        )}

        {drillLevel === 'posts' && subTopicDetail && (
          <PostsDetailView key="posts" subTopicDetail={subTopicDetail} />
        )}
      </AnimatePresence>
    </div>
  );
};

/**
 * Breadcrumb Navigation Component
 */
interface BreadcrumbProps {
  level: DrillLevel;
  cluster: string | null;
  subTopic: string | null;
  onHome: () => void;
  onBack: () => void;
}

const Breadcrumb: React.FC<BreadcrumbProps> = ({
  level,
  cluster,
  subTopic,
  onHome,
  onBack,
}) => {
  let breadcrumbs: BreadcrumbItem[] = [];

  if (level === 'clusters') {
    breadcrumbs = [{ label: 'Trending Clusters', level: 'cluster' }];
  } else if (level === 'subtopics' && cluster) {
    breadcrumbs = createBreadcrumbs('cluster', cluster);
  } else if (level === 'posts' && cluster && subTopic) {
    breadcrumbs = createBreadcrumbs('subtopic', cluster, subTopic);
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-center gap-2 text-sm text-gray-400"
    >
      <button
        onClick={onHome}
        className="flex items-center gap-1 hover:text-cyan-400 transition-colors"
        aria-label="Go to home"
      >
        <Home size={16} />
        <span>Dashboard</span>
      </button>

      {breadcrumbs.map((item, idx) => (
        <React.Fragment key={idx}>
          <ChevronRight size={16} className="text-gray-600" />
          <span className="text-gray-300">{item.label}</span>
        </React.Fragment>
      ))}

      {level !== 'clusters' && (
        <button
          onClick={onBack}
          className="ml-auto text-xs px-3 py-1 rounded border border-gray-600 hover:border-cyan-400 hover:text-cyan-400 transition-colors"
        >
          ← Back
        </button>
      )}
    </motion.div>
  );
};

/**
 * Level 1: Clusters View
 */
interface ClustersViewProps {
  clusters: ReturnType<typeof getTopClusters>;
  onSelectCluster: (cluster: string) => void;
  isLoading: boolean;
}

const ClustersView: React.FC<ClustersViewProps> = ({
  clusters,
  onSelectCluster,
  isLoading,
}) => {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4"
    >
      {clusters.map((item, idx) => (
        <motion.div
          key={item.cluster}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: idx * 0.05 }}
          onClick={() => onSelectCluster(item.cluster)}
          className="cursor-pointer"
        >
          <Card className="h-full hover:border-cyan-400/50 hover:bg-cyan-400/5 transition-all transform hover:scale-105">
            <CardContent className="p-6 flex flex-col items-center text-center space-y-4">
              <div className="text-3xl font-bold text-cyan-400">
                {item.postCount}
              </div>
              <div className="space-y-1">
                <h3 className="font-semibold text-white">{item.cluster}</h3>
                <p className="text-xs text-gray-400">posts</p>
              </div>
              <StatBadge
                label="Influence"
                value={(item.influence * 100).toFixed(0)}
                unit="%"
                variant="cyan"
                trend={item.influence > 0.7 ? 'up' : item.influence < 0.3 ? 'down' : 'stable'}
              />
              <ChevronRight size={16} className="text-gray-500 group-hover:text-cyan-400 transition-colors" />
            </CardContent>
          </Card>
        </motion.div>
      ))}
    </motion.div>
  );
};

/**
 * Level 2: Sub-Topics View
 */
interface SubTopicsViewProps {
  scopedTrends: ScopedTrendsResult;
  onSelectSubTopic: (subTopic: string) => void;
}

const SubTopicsView: React.FC<SubTopicsViewProps> = ({ scopedTrends, onSelectSubTopic }) => {
  const subTopicsList = Object.entries(scopedTrends.sub_topics);

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      className="space-y-3"
    >
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-white">Sub-Topics: {scopedTrends.meta_cluster}</h2>
        <p className="text-sm text-gray-400 mt-1">
          {subTopicsList.length} sub-topics • Ranked by influence
        </p>
      </div>

      <div className="grid gap-3">
        {subTopicsList.map(([subTopic, data], idx) => (
          <motion.div
            key={subTopic}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: idx * 0.05 }}
            onClick={() => onSelectSubTopic(subTopic)}
            className="cursor-pointer group"
          >
            <Card className="hover:border-purple-400/50 hover:bg-purple-400/5 transition-all">
              <CardContent className="p-4 flex items-center justify-between">
                <div className="flex-1 space-y-2">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-white group-hover:text-purple-400 transition-colors">
                      {subTopic}
                    </h3>
                    <span className="text-xs px-2 py-1 rounded-full bg-purple-500/20 text-purple-300">
                      #{data.influence_rank}
                    </span>
                  </div>
                  <div className="flex gap-3 text-xs text-gray-400">
                    <span>📊 {data.engagement_stats.post_count} posts</span>
                    <span>⚡ {(data.engagement_stats.avg_velocity || 0).toFixed(1)} vel</span>
                  </div>
                </div>

                <div className="flex flex-col items-end gap-2">
                  <StatBadge
                    label="Score"
                    value={(data.score * 100).toFixed(0)}
                    unit="%"
                    variant="purple"
                  />
                  <ChevronRight size={18} className="text-gray-500 group-hover:text-purple-400 transition-colors" />
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
};

/**
 * Level 3: Posts Detail View
 */
interface PostsDetailViewProps {
  subTopicDetail: SubTopicDetailResult;
}

const PostsDetailView: React.FC<PostsDetailViewProps> = ({ subTopicDetail }) => {
  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      className="space-y-6"
    >
      {/* Header with stats */}
      <div className="space-y-4">
        <h2 className="text-2xl font-bold text-white">
          {subTopicDetail.sub_topic} • {subTopicDetail.meta_cluster}
        </h2>

        <div className="grid grid-cols-4 gap-4">
          <StatCard
            label="Posts"
            value={subTopicDetail.stats.post_count}
            icon="📄"
          />
          <StatCard
            label="Avg Engagement"
            value={(subTopicDetail.stats.avg_engagement || 0).toFixed(0)}
            icon="💬"
          />
          <StatCard
            label="Influence"
            value={((subTopicDetail.stats.avg_influence || 0) * 100).toFixed(0)}
            unit="%"
            icon="⭐"
          />
          <StatCard
            label="Trending"
            value={subTopicDetail.stats.avg_influence > 0.7 ? 'Rising' : 'Stable'}
            icon="📈"
          />
        </div>
      </div>

      {/* Posts list */}
      <div className="space-y-3">
        <h3 className="text-lg font-semibold text-white">Top Posts</h3>
        {subTopicDetail.posts.map((post, idx) => (
          <motion.div
            key={post.post_id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.03 }}
          >
            <Card className="hover:border-pink-400/30 transition-colors">
              <CardContent className="p-4">
                <div className="flex gap-4">
                  {/* Rank badge */}
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-pink-500 to-rose-500 flex items-center justify-center text-white font-bold text-sm">
                      {idx + 1}
                    </div>
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white truncate">{post.title}</p>
                    <p className="text-xs text-gray-400 mt-1 line-clamp-2">{post.posts?.[0] || 'No description'}</p>
                  </div>

                  {/* Metrics */}
                  <div className="flex-shrink-0 flex gap-3 text-right">
                    <div className="text-right">
                      <div className="text-sm font-semibold text-cyan-400">
                        {post.engagement_total || 0}
                      </div>
                      <div className="text-xs text-gray-500">engagement</div>
                    </div>

                    <div className={cn(
                      'text-right px-3 py-2 rounded-lg',
                      post.momentum === 'accelerating' && 'bg-green-500/20',
                      post.momentum === 'rising' && 'bg-cyan-500/20',
                      post.momentum === 'stable' && 'bg-gray-500/20',
                      post.momentum === 'declining' && 'bg-orange-500/20',
                      post.momentum === 'collapsing' && 'bg-red-500/20',
                    )}>
                      <div className="text-xs font-semibold">
                        {post.momentum === 'accelerating' && <ArrowUp size={14} className="inline text-green-400" />}
                        {post.momentum === 'declining' && <ArrowDown size={14} className="inline text-orange-400" />}
                        {post.momentum === 'rising' && <TrendingUp size={14} className="inline text-cyan-400" />}
                      </div>
                      <div className="text-xs capitalize">{post.momentum || 'stable'}</div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
};

/**
 * Helper: Stat Card Component
 */
interface StatCardProps {
  label: string;
  value: string | number;
  unit?: string;
  icon?: string;
}

const StatCard: React.FC<StatCardProps> = ({ label, value, unit, icon }) => (
  <Card>
    <CardContent className="p-4 text-center space-y-2">
      {icon && <div className="text-2xl">{icon}</div>}
      <div className="text-2xl font-bold text-cyan-400">
        {value}
        {unit}
      </div>
      <div className="text-xs text-gray-400">{label}</div>
    </CardContent>
  </Card>
);

export default HierarchicalDrillDown;
