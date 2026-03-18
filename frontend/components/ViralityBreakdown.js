import { memo, useMemo } from 'react';

// Move helper functions outside component to prevent recreation
const MOMENTUM_COLORS = {
  accelerating: '#00ff88',
  growing: '#00d4ff',
  slowing: '#ff9f43',
  declining: '#ff3d8e',
};
const getMomentumColor = (label) => MOMENTUM_COLORS[label] || 'rgba(255,255,255,0.5)';

const MOMENTUM_ICONS = {
  accelerating: '🚀',
  growing: '📈',
  slowing: '📉',
  declining: '⬇️',
};
const getMomentumIcon = (label) => MOMENTUM_ICONS[label] || '➡️';

function ViralityBreakdown({ post }) {
  console.log('📈 [ViralityBreakdown] Received post:', {
    hasPost: !!post,
    hasBreakdown: !!post?.virality_breakdown,
    postTitle: post?.post?.title || post?.title,
    postData: post
  });

  // Memoize segments calculation
  const { vb, postData, segments, total } = useMemo(() => {
    if (!post || !post.virality_breakdown) {
      console.log('⚠️ [ViralityBreakdown] No breakdown data available');
      return { vb: null, postData: null, segments: [], total: 0 };
    }

    console.log('✅ [ViralityBreakdown] Processing breakdown:', post.virality_breakdown);

    const vb = post.virality_breakdown;
    const postData = post.post;

    // Safe defaults to prevent NaN/undefined
    const total = vb.total_score || 0;
    const sharesVal = vb.shares_component ?? 0;
    const commentsVal = vb.comments_component ?? 0;
    const likesVal = vb.likes_component ?? 0;
    const velocityVal = vb.velocity_component ?? 0;

    // Calculate percentages safely
    const calcPct = (val) => total > 0 ? ((val / total) * 100) : 25;

    const segments = [
      { key: 'shares', label: 'Shares', value: sharesVal, pct: vb.shares_pct ?? calcPct(sharesVal), color: '#00d4ff', weight: '0.4' },
      { key: 'comments', label: 'Comments', value: commentsVal, pct: vb.comments_pct ?? calcPct(commentsVal), color: '#7b61ff', weight: '0.3' },
      { key: 'likes', label: 'Likes', value: likesVal, pct: vb.likes_pct ?? calcPct(likesVal), color: '#ff3d8e', weight: '0.2' },
      { key: 'velocity', label: 'Velocity', value: velocityVal, pct: vb.velocity_pct ?? calcPct(velocityVal), color: '#00ff88', weight: '0.1' },
    ];

    return { vb, postData, segments, total };
  }, [post]);

  if (!vb) {
    return (
      <div className="glass-card" style={{ height: '100%' }}>
        <div className="section-header">
          <h2>Virality Breakdown</h2>
        </div>
        <div style={{
          height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: 'rgba(255,255,255,0.3)', fontSize: 13, textAlign: 'center', padding: 20,
        }}>
          Click a narrative to see its virality breakdown
        </div>
      </div>
    );
  }

  return (
    <div className="glass-card" style={{ height: '100%' }}>
      <div className="section-header">
        <h2>Virality Breakdown</h2>
        {vb.is_simulated && (
          <span style={{
            fontSize: 9, padding: '2px 6px', borderRadius: 4,
            background: 'rgba(255,159,67,0.2)', color: '#ff9f43',
          }}>
            ESTIMATED
          </span>
        )}
      </div>

      {/* Post title */}
      <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.6)', marginBottom: 16, lineHeight: 1.4 }}>
        {postData?.title?.substring(0, 80)}
        {postData?.title?.length > 80 ? '...' : ''}
      </div>

      {/* Total score + Momentum */}
      <div style={{ display: 'flex', justifyContent: 'space-around', marginBottom: 20 }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 36, fontWeight: 800, color: '#7b61ff' }}>
            {(total || 0).toFixed(1)}
          </div>
          <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: 1 }}>
            Virality Score
          </div>
        </div>
        {vb.momentum_label && (
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 24, fontWeight: 700, color: getMomentumColor(vb.momentum_label) }}>
              {getMomentumIcon(vb.momentum_label)} {((vb.momentum || 0) * 100).toFixed(0)}%
            </div>
            <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: 1 }}>
              {vb.momentum_label}
            </div>
          </div>
        )}
      </div>

      {/* Velocity indicator */}
      {vb.engagement_per_hour != null && (
        <div style={{
          display: 'flex', justifyContent: 'center', marginBottom: 16,
          fontSize: 12, color: 'rgba(255,255,255,0.5)',
        }}>
          <span style={{ color: '#00ff88', fontWeight: 600 }}>
            {(vb.engagement_per_hour || 0).toFixed(1)}
          </span>
          <span style={{ marginLeft: 4 }}>engagements/hour</span>
        </div>
      )}

      {/* Stacked bar */}
      <div className="virality-bar" style={{ marginBottom: 20 }}>
        {segments.map((seg) => (
          <div
            key={seg.key}
            className={`segment ${seg.key}`}
            style={{ width: `${Math.max(5, seg.pct)}%` }}
            title={`${seg.label}: ${seg.pct.toFixed(1)}%`}
          />
        ))}
      </div>

      {/* Component breakdown */}
      {segments.map((seg) => (
        <div key={seg.key} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10, fontSize: 13 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ width: 10, height: 10, borderRadius: 3, background: seg.color, flexShrink: 0 }} />
            <span style={{ color: 'rgba(255,255,255,0.7)' }}>{seg.label}</span>
            <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)' }}>(x{seg.weight})</span>
          </div>
          <div style={{ fontWeight: 600 }}>
            {(seg.value || 0).toFixed(1)}
            <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)', marginLeft: 4 }}>
              {seg.pct.toFixed(0)}%
            </span>
          </div>
        </div>
      ))}

      {/* Primary driver badge */}
      {vb.primary_driver && (
        <div style={{
          marginTop: 12, padding: '8px 12px', background: 'rgba(123,97,255,0.1)',
          borderRadius: 8, fontSize: 12, color: '#7b61ff', textAlign: 'center',
        }}>
          Primary Driver: <strong style={{ textTransform: 'capitalize' }}>{vb.primary_driver}</strong>
        </div>
      )}

      {/* Explanation */}
      <div style={{
        marginTop: 12, padding: 12, background: 'rgba(255,255,255,0.02)',
        borderRadius: 8, fontSize: 12, color: 'rgba(255,255,255,0.5)', lineHeight: 1.5,
      }}>
        {vb.explanation || 'Analyzing engagement patterns...'}
      </div>

      {/* Formula reference */}
      <div style={{
        marginTop: 12, fontSize: 10, color: 'rgba(255,255,255,0.25)', textAlign: 'center',
        fontFamily: 'monospace',
      }}>
        Score = Shares×0.4 + Comments×0.3 + Likes×0.2 + Velocity×0.1
      </div>
    </div>
  );
}

export default memo(ViralityBreakdown);
