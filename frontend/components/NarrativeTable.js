import { useState, useMemo, useCallback, memo } from 'react';
import { fetchNarrativeDetail } from '../lib/api';
import { safeNumber, safeFixed, safeLocaleString, formatRelativeTime, ensureArray, truncate } from '../lib/safeUtils';

// Generate simulated virality breakdown when API doesn't return it
function generateSimulatedBreakdown(post) {
  const likes = safeNumber(post?.likes, 0);
  const shares = safeNumber(post?.shares, 0);
  const comments = safeNumber(post?.comments, 0);
  const viralityScore = safeNumber(post?.virality_score, 0);
  const engagement = safeNumber(post?.engagement_total, likes + shares + comments);

  // Calculate components based on standard weights
  const sharesComponent = shares * 0.4;
  const commentsComponent = comments * 0.3;
  const likesComponent = likes * 0.2;
  const velocityComponent = safeNumber(post?.engagement_velocity, 0) * 0.1;

  const total = viralityScore || (sharesComponent + commentsComponent + likesComponent + velocityComponent);

  return {
    post: post,
    virality_breakdown: {
      total_score: total,
      shares_component: sharesComponent,
      comments_component: commentsComponent,
      likes_component: likesComponent,
      velocity_component: velocityComponent,
      shares_pct: total > 0 ? (sharesComponent / total) * 100 : 25,
      comments_pct: total > 0 ? (commentsComponent / total) * 100 : 25,
      likes_pct: total > 0 ? (likesComponent / total) * 100 : 25,
      velocity_pct: total > 0 ? (velocityComponent / total) * 100 : 25,
      engagement_per_hour: safeNumber(post?.engagement_velocity, 0),
      primary_driver: shares > comments && shares > likes ? 'shares' :
                      comments > likes ? 'comments' : 'likes',
      momentum: 1.0,
      momentum_label: 'growing',
      explanation: 'Simulated breakdown based on available engagement metrics.',
      is_simulated: true,
    }
  };
}

// Move static functions outside component to prevent recreation
const SOURCE_COLORS = {
  reddit: '#ff4500',
  google_news_rss: '#00d4ff',
  newsapi: '#7b61ff',
  csv_upload: '#ff9f43',
};
const getSourceColor = (source) => SOURCE_COLORS[source] || '#00d4ff';

// Memoized table row component to prevent unnecessary re-renders
const TableRow = memo(function TableRow({ post, index, isSelected, onRowClick }) {
  const postId = post?.post_id || `row-${index}`;
  const handleClick = useCallback(() => onRowClick(post), [post, onRowClick]);

  return (
    <tr
      onClick={handleClick}
      style={{
        cursor: 'pointer',
        background: isSelected ? 'rgba(123,97,255,0.15)' : undefined,
        borderLeft: isSelected ? '3px solid #7b61ff' : '3px solid transparent',
        transition: 'all 0.2s ease',
      }}
    >
      <td style={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {truncate(post?.title || 'Untitled', 60)}
      </td>
      <td>
        <span style={{
          color: getSourceColor(post?.source),
          fontWeight: 600,
          fontSize: 12,
          textTransform: 'uppercase',
        }}>
          {post?.source || '—'}
        </span>
      </td>
      <td>
        <span style={{ fontWeight: 700, color: '#7b61ff' }}>
          {safeFixed(post?.virality_score, 1, '0.0')}
        </span>
      </td>
      <td>{safeLocaleString(post?.engagement_total, '0')}</td>
      <td style={{ color: 'rgba(255,255,255,0.5)', fontSize: 12 }}>
        {formatRelativeTime(post?.timestamp)}
      </td>
      <td style={{ fontSize: 12 }}>{post?.region || '—'}</td>
    </tr>
  );
});

function NarrativeTable({ posts = [], onSelectPost }) {
  const [sortField, setSortField] = useState('virality_score');
  const [selectedId, setSelectedId] = useState(null);

  // Safety: ensure posts is always an array and sorted safely
  const displayed = useMemo(() => {
    const safePosts = ensureArray(posts);
    const sorted = [...safePosts].sort((a, b) => {
      const aVal = safeNumber(a?.[sortField], 0);
      const bVal = safeNumber(b?.[sortField], 0);
      return bVal - aVal;
    });
    return sorted.slice(0, 20);
  }, [posts, sortField]);

  const handleRowClick = useCallback(async (post) => {
    console.log('🔵 [NarrativeTable] Row clicked:', post?.title);

    if (!post?.post_id) {
      console.log('⚠️ [NarrativeTable] No post_id, using simulated breakdown');
      const simulated = generateSimulatedBreakdown(post);
      onSelectPost?.(simulated);
      return;
    }

    setSelectedId(post.post_id);

    try {
      console.log('🔄 [NarrativeTable] Fetching detail for:', post.post_id);
      const detail = await fetchNarrativeDetail(post.post_id);

      console.log('✅ [NarrativeTable] API Response:', detail);

      if (detail && !detail.error && detail.virality_breakdown) {
        console.log('📊 [NarrativeTable] Using API breakdown');
        onSelectPost?.(detail);
      } else {
        console.log('⚠️ [NarrativeTable] No API breakdown, generating simulated data');
        // Fallback: generate simulated breakdown from post data
        const simulated = generateSimulatedBreakdown(post);
        onSelectPost?.(simulated);
      }
    } catch (err) {
      console.log('❌ [NarrativeTable] Fetch failed:', err.message, '- using simulated data');
      const simulated = generateSimulatedBreakdown(post);
      onSelectPost?.(simulated);
    }
  }, [onSelectPost]);

  // Memoized sort handlers
  const handleSortSource = useCallback(() => setSortField('source'), []);
  const handleSortVirality = useCallback(() => setSortField('virality_score'), []);
  const handleSortEngagement = useCallback(() => setSortField('engagement_total'), []);

  return (
    <div style={{ maxHeight: 400, overflowY: 'auto' }}>
      <table className="data-table">
        <thead>
          <tr>
            <th>Title</th>
            <th
              style={{ cursor: 'pointer', userSelect: 'none' }}
              onClick={handleSortSource}
            >
              Source {sortField === 'source' && '↓'}
            </th>
            <th
              style={{ cursor: 'pointer', userSelect: 'none' }}
              onClick={handleSortVirality}
            >
              Virality {sortField === 'virality_score' && '↓'}
            </th>
            <th
              style={{ cursor: 'pointer', userSelect: 'none' }}
              onClick={handleSortEngagement}
            >
              Engagement {sortField === 'engagement_total' && '↓'}
            </th>
            <th>Time</th>
            <th>Region</th>
          </tr>
        </thead>
        <tbody>
          {displayed.map((post, index) => {
            const postId = post?.post_id || `row-${index}`;
            return (
              <TableRow
                key={postId}
                post={post}
                index={index}
                isSelected={selectedId === postId}
                onRowClick={handleRowClick}
              />
            );
          })}
          {displayed.length === 0 && (
            <tr>
              <td colSpan={6} style={{ textAlign: 'center', color: 'rgba(255,255,255,0.3)', padding: 40 }}>
                No narratives yet. Waiting for data...
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

export default memo(NarrativeTable);
