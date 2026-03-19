'use client';

/**
 * Trending Industries Dashboard
 * Real-time hierarchical view: Industries → Subtopics → Posts
 * Integrates with Kafka trending_signals via WebSocket
 */

import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { StatBadge } from '@/components/ui/stat-badge';
import { Spotlight } from '@/components/ui/spotlight';
import { getWebSocketService, AnalyticsState, TrendingSignal } from '@/lib/websocket-service';
import { cn } from '@/lib/utils';

interface IndustryView {
  name: string;
  score: number;
  count: number;
  topSubtopic?: string;
  momentum: string;
}

export const TrendingDashboard: React.FC = () => {
  const [state, setState] = useState<AnalyticsState | null>(null);
  const [industries, setIndustries] = useState<IndustryView[]>([]);
  const [selectedIndustry, setSelectedIndustry] = useState<string | null>(null);
  const [selectedSubtopic, setSelectedSubtopic] = useState<TrendingSignal | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<'connected' | 'connecting' | 'disconnected' | 'error'>('disconnected');
  const [isLoading, setIsLoading] = useState(true);

  // Initialize WebSocket connection
  useEffect(() => {
    const wsService = getWebSocketService();

    // Listen for state updates
    const unsubscribeState = wsService.onStateChange((newState) => {
      setState(newState);

      // Derive industries from state
      const industryMap = new Map<string, IndustryView>();
      newState.topIndustries.forEach((signals, industry) => {
        const topSignal = signals[0];
        industryMap.set(industry, {
          name: industry,
          score: topSignal.trending_score,
          count: signals.length,
          topSubtopic: topSignal.subtopic,
          momentum: topSignal.momentum || 'stable',
        });
      });

      const industryArray = Array.from(industryMap.values())
        .sort((a: IndustryView, b: IndustryView) => b.score - a.score)
        .slice(0, 10); // Top 10 industries

      setIndustries(industryArray);
      setIsLoading(false);

      // Auto-select first industry if none selected
      if (!selectedIndustry && industryArray.length > 0) {
        setSelectedIndustry(industryArray[0].name);
      }
    });

    // Listen for connection status
    const unsubscribeStatus = wsService.onStatusChange(setConnectionStatus);

    // Connect to backend
    wsService.connect().catch((err) => {
      console.error('Failed to connect to analytics stream:', err);
    });

    return () => {
      unsubscribeState();
      unsubscribeStatus();
    };
  }, []);

  const selectedIndustrySignals = selectedIndustry && state ? state.topIndustries.get(selectedIndustry) || [] : [];

  const subtopics = selectedIndustrySignals.reduce(
    (acc, signal) => {
      const existing = acc.find((s) => s.subtopic === signal.subtopic);
      if (existing) {
        existing.count += 1;
        existing.maxScore = Math.max(existing.maxScore, signal.trending_score);
      } else {
        acc.push({
          subtopic: signal.subtopic,
          count: 1,
          maxScore: signal.trending_score,
          signals: [signal],
        });
      }
      return acc;
    },
    [] as Array<{ subtopic: string; count: number; maxScore: number; signals: TrendingSignal[] }>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="relative rounded-lg backdrop-blur-xl bg-gradient-to-r from-white/5 to-white/5 border border-white/20 p-8 overflow-hidden">
        <Spotlight size={300} fill="rgba(0, 212, 255, 0.2)" className="top-0 left-0" />

        <div className="relative z-10">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-4xl font-bold bg-gradient-to-r from-cyan-400 via-blue-400 to-purple-400 bg-clip-text text-transparent">
              Trending Analytics
            </h1>
            <div className="flex items-center gap-3">
              <div className={cn('w-3 h-3 rounded-full animate-pulse', connectionStatus === 'connected' ? 'bg-green-400' : 'bg-red-400')} />
              <span className="text-sm text-gray-400 font-mono">
                {connectionStatus === 'connected' ? '● LIVE' : connectionStatus.toUpperCase()}
              </span>
            </div>
          </div>
          <p className="text-gray-300">Real-time hierarchical view: Industries → Subtopics → Trending Posts</p>

          {state?.lastUpdate && (
            <p className="text-xs text-gray-500 mt-2">Last update: {state.lastUpdate.toLocaleTimeString()}</p>
          )}
        </div>
      </div>

      {isLoading ? (
        <Card className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-cyan-400 border-r-2 border-purple-400" />
            <p className="mt-4 text-gray-400">Connecting to real-time stream...</p>
          </div>
        </Card>
      ) : (
        <>
          {/* Industries Grid */}
          <div>
            <h2 className="text-lg font-semibold text-gray-200 mb-4">Major Industry Clusters</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
              {industries.map((industry) => (
                <button
                  key={industry.name}
                  onClick={() => setSelectedIndustry(industry.name)}
                  className={cn(
                    'relative rounded-lg backdrop-blur-xl transition-all duration-300 cursor-pointer overflow-hidden group',
                    'border border-white/10 p-4',
                    selectedIndustry === industry.name
                      ? 'bg-gradient-to-br from-cyan-500/20 to-purple-500/20 border-cyan-400/50 shadow-lg shadow-cyan-500/20'
                      : 'bg-white/5 hover:bg-white/10 hover:border-white/20'
                  )}
                >
                  <div className="absolute inset-0 bg-gradient-to-br from-cyan-400/0 to-purple-400/0 group-hover:from-cyan-400/10 group-hover:to-purple-400/10 transition-all" />
                  <div className="relative z-10">
                    <p className="text-xs uppercase tracking-widest text-gray-400 mb-2">Industry</p>
                    <h3 className="text-lg font-bold text-white truncate">{industry.name}</h3>
                    <div className="mt-3 space-y-1">
                      <div className="flex items-baseline justify-between">
                        <span className="text-2xl font-bold text-cyan-400">{(industry.score * 100).toFixed(0)}</span>
                        <span className="text-xs text-gray-500">score</span>
                      </div>
                      <p className="text-xs text-gray-400">{industry.count} trending items</p>
                      <p className="text-xs text-gray-500 truncate">{industry.topSubtopic}</p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Subtopics Drill-down */}
          {selectedIndustry && subtopics.length > 0 && (
            <div>
              <h2 className="text-lg font-semibold text-gray-200 mb-4">Sub-topics: {selectedIndustry}</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {subtopics.map((item) => (
                  <button
                    key={item.subtopic}
                    onClick={() => setSelectedSubtopic(item.signals[0])}
                    className={cn(
                      'relative rounded-lg backdrop-blur-xl transition-all duration-300 cursor-pointer overflow-hidden group',
                      'border border-white/10 p-4',
                      selectedSubtopic?.subtopic === item.subtopic
                        ? 'bg-gradient-to-br from-purple-500/20 to-pink-500/20 border-purple-400/50 shadow-lg shadow-purple-500/20'
                        : 'bg-white/5 hover:bg-white/10 hover:border-white/20'
                    )}
                  >
                    <div className="absolute inset-0 bg-gradient-to-br from-purple-400/0 to-pink-400/0 group-hover:from-purple-400/10 group-hover:to-pink-400/10 transition-all" />
                    <div className="relative z-10">
                      <p className="text-xs uppercase tracking-widest text-gray-400 mb-2">Sub-topic</p>
                      <h3 className="text-base font-bold text-white capitalize truncate mb-3">{item.subtopic.replace(/_/g, ' ')}</h3>
                      <div className="space-y-1">
                        <div className="flex items-baseline justify-between">
                          <span className="text-xl font-bold text-purple-400">{(item.maxScore * 100).toFixed(0)}</span>
                          <span className="text-xs text-gray-500">score</span>
                        </div>
                        <p className="text-xs text-gray-400">{item.count} posts trending</p>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Top 5 Trending Posts */}
          {selectedSubtopic && (
            <Card>
              <CardHeader>
                <CardTitle>Top Trending Posts: {selectedSubtopic.subtopic}</CardTitle>
                <CardDescription>
                  Industry: {selectedSubtopic.industry} • Score: {(selectedSubtopic.trending_score * 100).toFixed(1)}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {selectedSubtopic.posts?.slice(0, 5).map((post, idx) => (
                    <div key={idx} className="rounded-lg bg-white/5 border border-white/10 p-4 hover:bg-white/10 transition-colors">
                      <div className="flex items-start justify-between mb-2">
                        <h4 className="font-semibold text-white flex-1 line-clamp-2">{post.title || post.subject || 'Untitled'}</h4>
                        <span className="text-xs bg-cyan-500/20 text-cyan-300 px-2 py-1 rounded ml-2">#{idx + 1}</span>
                      </div>
                      <p className="text-sm text-gray-400 line-clamp-2 mb-3">{post.content || post.body || 'No preview available'}</p>
                      <div className="flex flex-wrap gap-3 text-xs">
                        <span className="text-gray-500">
                          💬 {post.engagement_total || post.likes || 0} engagement
                        </span>
                        <span className="text-gray-500">📈 {(post.velocity || 0).toFixed(1)}/hr velocity</span>
                        <span className="text-gray-500">⏱ {post.timestamp || post.created_at}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Sentiment Spikes */}
          {state?.sentimentSpikes && state.sentimentSpikes.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Sentiment Spikes & Momentum Alerts</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {state.sentimentSpikes.slice(0, 6).map((spike, idx) => (
                    <div key={idx} className="rounded-lg bg-white/5 border border-white/10 p-4">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="font-semibold text-white">{spike.subtopic.replace(/_/g, ' ')}</h4>
                        <span className={cn('text-xs px-2 py-1 rounded', spike.momentum === 'accelerating' ? 'bg-red-500/20 text-red-300' : 'bg-yellow-500/20 text-yellow-300')}>
                          {spike.momentum || 'stable'}
                        </span>
                      </div>
                      <p className="text-sm text-gray-400">{spike.industry}</p>
                      <div className="mt-2 text-xs text-gray-500">
                        Score: <span className="text-cyan-400">+{(spike.trending_score * 100).toFixed(0)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
};
