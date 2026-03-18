import { memo, useMemo } from 'react';

// Memoized individual ticker item to prevent unnecessary re-renders
const TickerItem = memo(function TickerItem({ post, index }) {
  return (
    <div className="ticker-item" key={`${post.post_id}-${index}`}>
      <span className="source-tag">
        {post.source === 'reddit' ? 'Reddit' : post.source === 'google_news' ? 'News' : post.source}
      </span>
      {post.title?.substring(0, 60)}
      {post.title?.length > 60 ? '...' : ''}
      {post.virality_score > 0 && (
        <span style={{ marginLeft: 8, color: '#7b61ff', fontWeight: 600, fontSize: 11 }}>
          v:{post.virality_score?.toFixed(1)}
        </span>
      )}
    </div>
  );
});

function Ticker({ posts = [] }) {
  // Safety: ensure posts is always an array and memoize ticker items
  const items = useMemo(() => {
    const safePosts = Array.isArray(posts) ? posts : [];
    if (safePosts.length === 0) return [];
    // Show latest 20 posts in ticker, duplicate for seamless loop
    const tickerPosts = safePosts.slice(0, 20);
    return [...tickerPosts, ...tickerPosts];
  }, [posts]);

  if (items.length === 0) return null;

  return (
    <div className="ticker-container">
      <div className="ticker-track">
        {items.map((post, i) => (
          <TickerItem key={`${post.post_id}-${i}`} post={post} index={i} />
        ))}
      </div>
    </div>
  );
}

export default memo(Ticker);
