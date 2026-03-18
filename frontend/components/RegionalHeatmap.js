import { useMemo, memo } from 'react';

const INDIA_REGIONS = [
  { name: 'Delhi', x: 200, y: 80, aliases: ['delhi', 'new delhi'] },
  { name: 'Mumbai', x: 145, y: 195, aliases: ['mumbai', 'bombay'] },
  { name: 'Bangalore', x: 170, y: 275, aliases: ['bangalore', 'bengaluru'] },
  { name: 'Chennai', x: 210, y: 280, aliases: ['chennai', 'madras'] },
  { name: 'Kolkata', x: 280, y: 160, aliases: ['kolkata', 'calcutta'] },
  { name: 'Hyderabad', x: 190, y: 230, aliases: ['hyderabad'] },
  { name: 'Pune', x: 155, y: 210, aliases: ['pune'] },
  { name: 'Ahmedabad', x: 120, y: 145, aliases: ['ahmedabad'] },
  { name: 'Jaipur', x: 155, y: 105, aliases: ['jaipur'] },
  { name: 'Lucknow', x: 215, y: 110, aliases: ['lucknow'] },
];

function RegionalHeatmap({ posts = [] }) {
  // Memoize safe posts array
  const safePosts = useMemo(() => Array.isArray(posts) ? posts : [], [posts]);

  const regionData = useMemo(() => {
    const indiaPosts = safePosts.filter((p) => p?.region === 'India');
    const counts = {};

    INDIA_REGIONS.forEach((r) => { counts[r.name] = 0; });

    indiaPosts.forEach((p) => {
      const text = `${p.title} ${p.content}`.toLowerCase();
      INDIA_REGIONS.forEach((r) => {
        if (r.aliases.some((a) => text.includes(a))) {
          counts[r.name] += 1;
        }
      });
    });

    // If no specific city detected, distribute generally
    if (Object.values(counts).every((v) => v === 0) && indiaPosts.length > 0) {
      counts['Delhi'] = Math.ceil(indiaPosts.length * 0.25);
      counts['Mumbai'] = Math.ceil(indiaPosts.length * 0.2);
      counts['Bangalore'] = Math.ceil(indiaPosts.length * 0.15);
      counts['Chennai'] = Math.ceil(indiaPosts.length * 0.1);
      counts['Kolkata'] = Math.ceil(indiaPosts.length * 0.1);
    }

    const maxCount = Math.max(1, ...Object.values(counts));

    return INDIA_REGIONS.map((r) => ({
      ...r,
      count: counts[r.name],
      intensity: counts[r.name] / maxCount,
    }));
  }, [safePosts]);

  return (
    <div style={{ position: 'relative', height: 320 }}>
      <svg viewBox="0 0 380 380" style={{ width: '100%', height: '100%' }}>
        {/* Simplified India outline */}
        <path
          d="M 165 30 L 220 25 L 280 40 L 310 70 L 320 110 L 310 140 L 290 160 L 300 180 L 280 200 L 260 210 L 240 250 L 230 290 L 210 330 L 190 350 L 170 330 L 160 300 L 145 270 L 130 250 L 120 220 L 110 190 L 100 160 L 105 130 L 120 100 L 140 60 Z"
          fill="rgba(255,255,255,0.03)"
          stroke="rgba(255,255,255,0.1)"
          strokeWidth="1"
        />

        {/* Regional hotspots */}
        {regionData.map((r) => (
          <g key={r.name}>
            {/* Glow effect */}
            <circle
              cx={r.x}
              cy={r.y}
              r={12 + r.intensity * 20}
              fill={`rgba(0, 212, 255, ${r.intensity * 0.15})`}
            />
            {/* Core dot */}
            <circle
              cx={r.x}
              cy={r.y}
              r={4 + r.intensity * 6}
              fill={r.intensity > 0.5 ? '#ff3d8e' : r.intensity > 0 ? '#00d4ff' : 'rgba(255,255,255,0.1)'}
              opacity={Math.max(0.3, r.intensity)}
            />
            {/* Label */}
            <text
              x={r.x}
              y={r.y - 12 - r.intensity * 8}
              textAnchor="middle"
              fill="rgba(255,255,255,0.6)"
              fontSize="9"
            >
              {r.name}
            </text>
            {r.count > 0 && (
              <text
                x={r.x}
                y={r.y + 18 + r.intensity * 6}
                textAnchor="middle"
                fill="rgba(255,255,255,0.4)"
                fontSize="8"
              >
                {r.count} posts
              </text>
            )}
          </g>
        ))}
      </svg>

      {/* Legend */}
      <div style={{
        position: 'absolute', bottom: 0, left: 0, right: 0,
        display: 'flex', justifyContent: 'center', gap: 16, fontSize: 10, color: 'rgba(255,255,255,0.4)',
      }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#00d4ff' }} /> Active
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#ff3d8e' }} /> Hotspot
        </span>
      </div>
    </div>
  );
}

export default memo(RegionalHeatmap);
