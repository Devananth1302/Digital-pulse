import { memo } from 'react';
import { getConfidenceColor, getSeverityColor } from '../lib/insightGenerator';

/**
 * Compact insight badge for displaying on cards
 */
export const InsightBadge = memo(function InsightBadge({ insight, compact = false }) {
  if (!insight) return null;

  if (compact) {
    return (
      <div className="insight-badge-compact">
        <span
          className="insight-dot"
          style={{ background: getSeverityColor(insight.severity) }}
        />
        <span className="insight-action-short">{insight.action?.split('.')[0]}</span>
        {insight.urgency === 'high' && (
          <span style={{ marginLeft: 6, fontSize: 10, color: '#ff3d8e' }}>URGENT</span>
        )}
      </div>
    );
  }

  return (
    <div className="insight-badge">
      <div className="insight-header">
        <span className="insight-label">AI Insight</span>
        <span
          className="confidence-badge"
          style={{ background: `${getConfidenceColor(insight.confidence)}20`, color: getConfidenceColor(insight.confidence) }}
        >
          {insight.confidence} confidence
        </span>
      </div>
      <p className="insight-text">{insight.insight}</p>
      <p className="insight-action">{insight.action}</p>
    </div>
  );
});

/**
 * Full insight panel for modals/detail views
 */
export const InsightPanel = memo(function InsightPanel({ insight }) {
  if (!insight) return null;

  const urgencyColors = {
    high: '#ff3d8e',
    medium: '#ff9f43',
    low: '#00ff88',
  };

  return (
    <div className="insight-panel">
      <div className="insight-panel-header">
        <div className="insight-panel-icon">💡</div>
        <div style={{ flex: 1 }}>
          <h4 className="insight-panel-title">AI Analysis</h4>
          <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
            <span
              className="confidence-badge"
              style={{
                background: `${getConfidenceColor(insight.confidence)}20`,
                color: getConfidenceColor(insight.confidence),
              }}
            >
              {insight.confidence} confidence
            </span>
            {insight.urgency && (
              <span
                className="confidence-badge"
                style={{
                  background: `${urgencyColors[insight.urgency]}20`,
                  color: urgencyColors[insight.urgency],
                }}
              >
                {insight.urgency} urgency
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="insight-panel-content">
        {/* What's happening */}
        <div className="insight-row">
          <span className="insight-row-label">What</span>
          <span className="insight-row-value">{insight.insight}</span>
        </div>

        {/* Context */}
        {insight.context && (
          <div className="insight-row">
            <span className="insight-row-label">Context</span>
            <span className="insight-row-value insight-context">{insight.context}</span>
          </div>
        )}

        {/* Impact */}
        <div className="insight-row">
          <span className="insight-row-label">Impact</span>
          <span className="insight-row-value">{insight.impact}</span>
        </div>

        {/* Time to Peak (if available) */}
        {insight.timeToPeak && (
          <div className="insight-row">
            <span className="insight-row-label">Peak ETA</span>
            <span className="insight-row-value" style={{ color: '#00d4ff', fontWeight: 600 }}>
              {insight.timeToPeak}
            </span>
          </div>
        )}

        {/* Topic Category (if available) */}
        {insight.topicCategory && insight.topicCategory !== 'general' && (
          <div className="insight-row">
            <span className="insight-row-label">Category</span>
            <span className="insight-row-value">
              <span style={{
                textTransform: 'capitalize',
                padding: '2px 8px',
                borderRadius: 4,
                background: 'rgba(123,97,255,0.15)',
                color: '#7b61ff',
                fontSize: 12,
              }}>
                {insight.topicCategory}
              </span>
              {insight.keywords?.length > 0 && (
                <span style={{ marginLeft: 8, fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>
                  {insight.keywords.join(', ')}
                </span>
              )}
            </span>
          </div>
        )}

        {/* Why This Matters */}
        {insight.whyThisMatters && (
          <div className="insight-why-matters" style={{
            marginTop: 12,
            padding: 12,
            background: 'rgba(0, 212, 255, 0.05)',
            border: '1px solid rgba(0, 212, 255, 0.15)',
            borderRadius: 8,
          }}>
            <span style={{ fontSize: 11, color: '#00d4ff', fontWeight: 600, display: 'block', marginBottom: 4 }}>
              WHY THIS MATTERS
            </span>
            <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.7)', margin: 0, lineHeight: 1.5 }}>
              {insight.whyThisMatters}
            </p>
          </div>
        )}

        {/* Action */}
        <div className="insight-action-box" style={{ borderColor: getSeverityColor(insight.severity), marginTop: 12 }}>
          <span className="insight-action-label">Recommended Action</span>
          <p className="insight-action-text">{insight.action}</p>
        </div>
      </div>
    </div>
  );
});

/**
 * Dashboard summary bar
 */
export const DashboardSummaryBar = memo(function DashboardSummaryBar({ summary }) {
  if (!summary) return null;

  const urgencyColors = {
    high: { bg: 'rgba(255, 61, 142, 0.1)', border: '#ff3d8e', text: '#ff3d8e' },
    medium: { bg: 'rgba(255, 159, 67, 0.1)', border: '#ff9f43', text: '#ff9f43' },
    low: { bg: 'rgba(0, 255, 136, 0.1)', border: '#00ff88', text: '#00ff88' },
  };

  const colors = urgencyColors[summary.urgency] || urgencyColors.low;

  return (
    <div
      className="dashboard-summary-bar"
      style={{ background: colors.bg, borderColor: colors.border }}
    >
      <div className="summary-status">
        <span className="summary-dot" style={{ background: colors.text }} />
        <span className="summary-status-text" style={{ color: colors.text }}>
          {summary.status?.toUpperCase?.() || 'MONITORING'}
        </span>
      </div>
      <div className="summary-content">
        <p className="summary-text">{summary.summary || 'Analyzing cultural signals...'}</p>
        {summary.dominantCategories && summary.dominantCategories !== 'general' && (
          <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginLeft: 8 }}>
            Dominant: {summary.dominantCategories}
          </span>
        )}
      </div>
      <div className="summary-action">
        <span className="summary-recommendation">{summary.recommendation || 'Continue monitoring'}</span>
      </div>
    </div>
  );
});

export default InsightBadge;
