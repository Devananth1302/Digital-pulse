import { useEffect, useMemo, memo } from 'react';
import { InsightPanel } from './InsightBadge';
import {
  generatePulseInsight,
  generateSignalInsight,
  generateForecastInsight,
  generateNarrativeInsight,
} from '../lib/insightGenerator';

function DetailModal({ data, type, onClose }) {
  // Close on Escape key
  useEffect(() => {
    const handleKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [onClose]);

  // Memoize expensive computations
  const fields = useMemo(() => data ? buildFields(data, type) : null, [data, type]);
  const insight = useMemo(() => data ? generateInsight(data, type) : null, [data, type]);

  if (!data || !fields) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <div>
            <h2 className="modal-title">{fields.title}</h2>
            {fields.category && (
              <span className="modal-category">{fields.category}</span>
            )}
          </div>
          <button className="modal-close" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>

        {/* Primary Value */}
        {fields.value != null && (
          <div className="modal-value-section">
            <div className="modal-value">{fields.value}</div>
            {fields.valueLabel && (
              <div className="modal-value-label">{fields.valueLabel}</div>
            )}
          </div>
        )}

        {/* Change / Trend Row */}
        {(fields.change || fields.trend) && (
          <div className="modal-stats-row">
            {fields.change && (
              <div className="modal-stat">
                <span className="modal-stat-label">Change</span>
                <span className={`modal-stat-value ${fields.trend === 'rising' ? 'positive' : fields.trend === 'falling' ? 'negative' : ''}`}>
                  {fields.change}
                </span>
              </div>
            )}
            {fields.trend && (
              <div className="modal-stat">
                <span className="modal-stat-label">Trend</span>
                <span className={`trend-badge ${fields.trend}`}>
                  {fields.trend === 'rising' ? '▲' : fields.trend === 'falling' ? '▼' : '●'} {fields.trend}
                </span>
              </div>
            )}
          </div>
        )}

        {/* AI Insight Panel */}
        {insight && <InsightPanel insight={insight} />}

        {/* Detail Grid */}
        <div className="modal-details-grid">
          {fields.details.map((item, i) => (
            <div key={i} className="modal-detail-item">
              <span className="modal-detail-label">{item.label}</span>
              <span className="modal-detail-value">{item.value ?? '—'}</span>
            </div>
          ))}
        </div>

        {/* Insight / Prediction */}
        {fields.insight && (
          <div className="modal-insight">
            <span className="modal-insight-label">Insight</span>
            <p>{fields.insight}</p>
          </div>
        )}

        {/* Timestamp */}
        {fields.timestamp && (
          <div className="modal-timestamp">
            Last updated: {fields.timestamp}
          </div>
        )}
      </div>
    </div>
  );
}

function buildFields(data, type) {
  switch (type) {
    case 'pulse':
      return {
        title: 'Pulse Score',
        category: 'Cultural Intelligence',
        value: data?.score != null ? Math.round(data.score) : '—',
        valueLabel: 'Cultural Intensity Index',
        trend: data?.trend_direction || 'stable',
        change: data?.score != null ? `${data.score > 50 ? '+' : ''}${(data.score - 50).toFixed(1)} from baseline` : null,
        details: [
          { label: 'Engagement Intensity', value: data?.breakdown?.engagement_intensity?.toFixed(1) },
          { label: 'Emerging Signals', value: data?.breakdown?.emerging_signals?.toFixed(1) },
          { label: 'Cluster Activity', value: data?.breakdown?.cluster_activity?.toFixed(1) },
          { label: 'Total Posts Analyzed', value: data?.total_posts ?? '—' },
        ],
        insight: data?.score >= 70
          ? 'High cultural activity detected. Multiple narratives gaining traction simultaneously.'
          : data?.score >= 40
          ? 'Moderate cultural activity. Some narratives showing growth potential.'
          : 'Low cultural activity. Monitoring for emerging signals.',
        timestamp: new Date().toLocaleString(),
      };

    case 'signal':
      return {
        title: data?.topic || 'Emerging Signal',
        category: data?.severity ? `${data.severity.toUpperCase()} Severity` : 'Signal',
        value: data?.growth_rate != null ? `+${((data.growth_rate - 1) * 100).toFixed(0)}%` : '—',
        valueLabel: 'Growth Rate (2h window)',
        trend: 'rising',
        change: data?.current_engagement != null && data?.previous_engagement != null
          ? `${(data.current_engagement - data.previous_engagement).toFixed(0)} engagement change`
          : null,
        details: [
          { label: 'Current Engagement', value: data?.current_engagement?.toFixed(0) },
          { label: 'Previous Engagement', value: data?.previous_engagement?.toFixed(0) },
          { label: 'Severity', value: data?.severity },
          { label: 'Detected At', value: data?.detected_at ? new Date(data.detected_at).toLocaleString() : '—' },
        ],
        insight: data?.growth_rate > 2.5
          ? 'Rapid growth detected. This signal is spreading significantly faster than baseline.'
          : 'Signal shows notable growth above the 150% threshold.',
        timestamp: data?.detected_at ? new Date(data.detected_at).toLocaleString() : null,
      };

    case 'forecast':
      return {
        title: data?.topic || 'Forecast',
        category: 'Trend Prediction',
        value: data?.predicted_engagement?.toFixed(0) ?? '—',
        valueLabel: 'Predicted Engagement',
        trend: data?.trend_prediction || 'stable',
        change: data?.confidence_score != null ? `${(data.confidence_score * 100).toFixed(0)}% confidence` : null,
        details: [
          { label: 'Trend Prediction', value: data?.trend_prediction },
          { label: 'Confidence Score', value: data?.confidence_score != null ? `${(data.confidence_score * 100).toFixed(0)}%` : '—' },
          { label: 'Data Points', value: data?.data_points?.length ?? 0 },
          { label: 'Forecast Window', value: '48 hours' },
        ],
        insight: data?.trend_prediction === 'rising'
          ? 'This topic is predicted to gain significant traction over the next 48 hours.'
          : data?.trend_prediction === 'falling'
          ? 'This topic is expected to decline in engagement over the forecast window.'
          : 'This topic is expected to remain stable in the near term.',
        timestamp: new Date().toLocaleString(),
      };

    case 'narrative':
      return {
        title: data?.title || 'Narrative',
        category: data?.source ? `Source: ${data.source}` : 'Narrative',
        value: data?.virality_score?.toFixed(1) ?? '—',
        valueLabel: 'Virality Score',
        trend: data?.virality_score > 20 ? 'rising' : data?.virality_score > 10 ? 'stable' : 'falling',
        change: data?.engagement_total != null ? `${Math.round(data.engagement_total).toLocaleString()} total engagement` : null,
        details: [
          { label: 'Source', value: data?.source },
          { label: 'Region', value: data?.region || '—' },
          { label: 'Engagement', value: data?.engagement_total != null ? Math.round(data.engagement_total).toLocaleString() : '—' },
          { label: 'Cluster', value: data?.cluster_label || '—' },
          { label: 'Likes', value: data?.likes?.toLocaleString?.() ?? '—' },
          { label: 'Shares', value: data?.shares?.toLocaleString?.() ?? '—' },
          { label: 'Comments', value: data?.comments?.toLocaleString?.() ?? '—' },
          { label: 'Published', value: data?.timestamp ? new Date(data.timestamp).toLocaleString() : '—' },
        ],
        insight: data?.content?.substring(0, 200) || null,
        timestamp: data?.timestamp ? new Date(data.timestamp).toLocaleString() : null,
      };

    default:
      return {
        title: data?.title || data?.topic || 'Details',
        category: null,
        value: null,
        valueLabel: null,
        trend: null,
        change: null,
        details: Object.entries(data || {})
          .filter(([k, v]) => typeof v !== 'object')
          .slice(0, 8)
          .map(([k, v]) => ({ label: k.replace(/_/g, ' '), value: String(v) })),
        insight: null,
        timestamp: null,
      };
  }
}

function generateInsight(data, type) {
  switch (type) {
    case 'pulse':
      return generatePulseInsight(data);
    case 'signal':
      return generateSignalInsight(data);
    case 'forecast':
      return generateForecastInsight(data);
    case 'narrative':
      return generateNarrativeInsight(data);
    default:
      return null;
  }
}

export default memo(DetailModal);
