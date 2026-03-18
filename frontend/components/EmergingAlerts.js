import { memo, useMemo } from 'react';

// Move helper functions outside component to prevent recreation
function formatTime(ts) {
  if (!ts) return '';
  try {
    const d = new Date(ts);
    if (isNaN(d.getTime())) return '';
    const now = new Date();
    const diffM = Math.round((now - d) / 60000);
    if (diffM < 1) return 'Just now';
    if (diffM < 60) return `${diffM}m ago`;
    return `${Math.round(diffM / 60)}h ago`;
  } catch {
    return '';
  }
}

function safeGrowthPct(rate) {
  const numRate = Number(rate);
  if (isNaN(numRate) || !isFinite(numRate)) return '0';
  return ((numRate - 1) * 100).toFixed(0);
}

// Memoized individual alert item to prevent unnecessary re-renders
const AlertItem = memo(function AlertItem({ signal, index }) {
  const severity = signal?.severity || 'low';
  const topic = signal?.topic || 'Unknown Signal';
  const detectedAt = signal?.detected_at;
  const growthRate = signal?.growth_rate ?? 1;

  return (
    <div
      key={signal?.id ?? index}
      style={{
        padding: '12px 14px',
        background: 'rgba(255,255,255,0.02)',
        borderRadius: 10,
        borderLeft: `3px solid ${
          severity === 'high' ? '#ff3d8e' :
          severity === 'medium' ? '#ff9f43' : '#00ff88'
        }`,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
        <span className={`severity-badge ${severity}`}>
          {severity}
        </span>
        <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>
          {formatTime(detectedAt)}
        </span>
      </div>
      <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 4 }}>
        {topic}
      </div>
      <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)' }}>
        Growth: <span style={{ color: '#00ff88', fontWeight: 600 }}>
          +{safeGrowthPct(growthRate)}%
        </span>
        {' '}in 2h
      </div>
    </div>
  );
});

function EmergingAlerts({ signals = [] }) {
  // Safety: ensure signals is always an array and limit display
  const safeSignals = useMemo(() => {
    const arr = Array.isArray(signals) ? signals : [];
    return arr.slice(0, 20); // Limit to 20 signals for performance
  }, [signals]);

  return (
    <div className="glass-card" style={{ height: '380px', overflowY: 'auto' }}>
      <div className="section-header">
        <h2>Emerging Signals</h2>
        <span className="count">{safeSignals.length} alerts</span>
      </div>

      {safeSignals.length === 0 ? (
        <div style={{ textAlign: 'center', color: 'rgba(255,255,255,0.3)', paddingTop: 60 }}>
          No emerging signals detected
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {safeSignals.map((signal, i) => (
            <AlertItem key={signal?.id ?? i} signal={signal} index={i} />
          ))}
        </div>
      )}
    </div>
  );
}

export default memo(EmergingAlerts);
