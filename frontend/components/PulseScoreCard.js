import { useEffect, useRef, useMemo, memo } from 'react';
import { safeNumber, safeFixed } from '../lib/safeUtils';

// Move drawing function outside component to prevent recreation
function drawRing(canvas, scoreValue) {
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const size = 160;
  const center = size / 2;
  const radius = 60;
  const lineWidth = 10;

  canvas.width = size;
  canvas.height = size;
  ctx.clearRect(0, 0, size, size);

  // Background ring
  ctx.beginPath();
  ctx.arc(center, center, radius, 0, Math.PI * 2);
  ctx.strokeStyle = 'rgba(255,255,255,0.05)';
  ctx.lineWidth = lineWidth;
  ctx.stroke();

  // Score ring - ensure score is valid
  const safeScore = safeNumber(scoreValue, 0);
  const clampedScore = Math.max(0, Math.min(100, safeScore));
  const progress = (clampedScore / 100) * Math.PI * 2;

  if (progress > 0) {
    const gradient = ctx.createLinearGradient(0, 0, size, size);
    gradient.addColorStop(0, '#00d4ff');
    gradient.addColorStop(1, '#7b61ff');

    ctx.beginPath();
    ctx.arc(center, center, radius, -Math.PI / 2, -Math.PI / 2 + progress);
    ctx.strokeStyle = gradient;
    ctx.lineWidth = lineWidth;
    ctx.lineCap = 'round';
    ctx.stroke();
  }
}

function PulseScoreCard({ data, loading }) {
  const canvasRef = useRef(null);

  // Safely extract data with defaults
  const score = useMemo(() => safeNumber(data?.score, 0), [data?.score]);
  const direction = data?.trend_direction || 'stable';
  const breakdown = useMemo(() => data?.breakdown || {}, [data?.breakdown]);

  useEffect(() => {
    if (!canvasRef.current) return;
    drawRing(canvasRef.current, score);
  }, [score]);

  return (
    <div className="glass-card pulse-score-container">
      <div className="section-header">
        <h2>Pulse Score</h2>
      </div>

      <div className="pulse-ring" style={{ position: 'relative' }}>
        <canvas ref={canvasRef} style={{ width: 160, height: 160 }} />
        <div
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            textAlign: 'center',
          }}
        >
          <div style={{ fontSize: 42, fontWeight: 800 }}>
            {loading ? '--' : Math.round(score)}
          </div>
        </div>
      </div>

      <div className="pulse-label">Cultural Intensity</div>

      <div style={{ marginTop: 12, textAlign: 'center' }}>
        <span className={`trend-badge ${direction}`}>
          {direction === 'rising' ? '▲' : direction === 'falling' ? '▼' : '●'}{' '}
          {direction}
        </span>
      </div>

      {/* Breakdown */}
      <div style={{ marginTop: 20, fontSize: 13 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
          <span style={{ color: 'rgba(255,255,255,0.5)' }}>Engagement</span>
          <span>{safeFixed(breakdown.engagement_intensity, 1, '0.0')}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
          <span style={{ color: 'rgba(255,255,255,0.5)' }}>Signals</span>
          <span>{safeFixed(breakdown.emerging_signals, 1, '0.0')}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: 'rgba(255,255,255,0.5)' }}>Clusters</span>
          <span>{safeFixed(breakdown.cluster_activity, 1, '0.0')}</span>
        </div>
      </div>
    </div>
  );
}

export default memo(PulseScoreCard);
