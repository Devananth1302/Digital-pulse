export default function PDFReport({ pulseData, narratives, emerging, forecasts, generatedAt }) {
  const posts = narratives?.posts || [];
  const clusters = narratives?.clusters || [];
  const signals = emerging?.signals || [];
  const forecastList = forecasts?.forecasts || [];
  const score = pulseData?.score ?? 0;
  const breakdown = pulseData?.breakdown || {};
  const trend = pulseData?.trend_direction || 'stable';
  const meta = pulseData?.meta || {};

  return (
    <div className="pdf-report">
      {/* ── Header ── */}
      <div className="pdf-header">
        <div>
          <h1 className="pdf-title">Digital Pulse</h1>
          <p className="pdf-subtitle">Cultural Intelligence Report</p>
        </div>
        <div className="pdf-meta">
          <p>Generated: {generatedAt || new Date().toLocaleString()}</p>
          <p>{meta.posts_analyzed ?? posts.length} posts analyzed</p>
        </div>
      </div>

      <div className="pdf-divider" />

      {/* ── Pulse Score Summary ── */}
      <div className="pdf-section">
        <h2 className="pdf-section-title">Pulse Score Overview</h2>
        <div className="pdf-stats-row">
          <div className="pdf-stat-card pdf-stat-highlight">
            <span className="pdf-stat-value">{Math.round(score)}</span>
            <span className="pdf-stat-label">Pulse Score</span>
          </div>
          <div className="pdf-stat-card">
            <span className="pdf-stat-value">{trend === 'rising' ? '▲ Rising' : trend === 'falling' ? '▼ Falling' : '● Stable'}</span>
            <span className="pdf-stat-label">Trend Direction</span>
          </div>
          <div className="pdf-stat-card">
            <span className="pdf-stat-value">{meta.signals_detected ?? signals.length}</span>
            <span className="pdf-stat-label">Signals Detected</span>
          </div>
          <div className="pdf-stat-card">
            <span className="pdf-stat-value">{meta.active_clusters ?? clusters.length}</span>
            <span className="pdf-stat-label">Active Clusters</span>
          </div>
        </div>

        {/* Breakdown */}
        <div className="pdf-breakdown">
          <div className="pdf-breakdown-item">
            <span className="pdf-breakdown-label">Engagement Intensity</span>
            <div className="pdf-bar-track">
              <div className="pdf-bar-fill pdf-bar-blue" style={{ width: `${(breakdown.engagement_intensity || 0) / 40 * 100}%` }} />
            </div>
            <span className="pdf-breakdown-value">{(breakdown.engagement_intensity || 0).toFixed(1)} / 40</span>
          </div>
          <div className="pdf-breakdown-item">
            <span className="pdf-breakdown-label">Emerging Signals</span>
            <div className="pdf-bar-track">
              <div className="pdf-bar-fill pdf-bar-purple" style={{ width: `${(breakdown.emerging_signals || 0) / 30 * 100}%` }} />
            </div>
            <span className="pdf-breakdown-value">{(breakdown.emerging_signals || 0).toFixed(1)} / 30</span>
          </div>
          <div className="pdf-breakdown-item">
            <span className="pdf-breakdown-label">Cluster Activity</span>
            <div className="pdf-bar-track">
              <div className="pdf-bar-fill pdf-bar-green" style={{ width: `${(breakdown.cluster_activity || 0) / 30 * 100}%` }} />
            </div>
            <span className="pdf-breakdown-value">{(breakdown.cluster_activity || 0).toFixed(1)} / 30</span>
          </div>
        </div>
      </div>

      {/* ── Top Narratives ── */}
      {posts.length > 0 && (
        <div className="pdf-section">
          <h2 className="pdf-section-title">Top Narratives</h2>
          <table className="pdf-table">
            <thead>
              <tr>
                <th style={{ width: '40%' }}>Title</th>
                <th>Source</th>
                <th>Virality</th>
                <th>Engagement</th>
                <th>Region</th>
              </tr>
            </thead>
            <tbody>
              {posts.slice(0, 15).map((post, i) => (
                <tr key={post.post_id || i}>
                  <td className="pdf-cell-title">{post.title?.substring(0, 60)}{post.title?.length > 60 ? '...' : ''}</td>
                  <td>{post.source || '—'}</td>
                  <td className="pdf-cell-number">{(post.virality_score || 0).toFixed(1)}</td>
                  <td className="pdf-cell-number">{Math.round(post.engagement_total || 0).toLocaleString()}</td>
                  <td>{post.region || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {posts.length > 15 && (
            <p className="pdf-note">Showing top 15 of {posts.length} narratives</p>
          )}
        </div>
      )}

      {/* ── Emerging Signals ── */}
      {signals.length > 0 && (
        <div className="pdf-section">
          <h2 className="pdf-section-title">Emerging Signals</h2>
          <div className="pdf-signals-grid">
            {signals.slice(0, 10).map((signal, i) => (
              <div key={signal.id || i} className="pdf-signal-card">
                <div className="pdf-signal-header">
                  <span className={`pdf-severity pdf-severity-${signal.severity || 'low'}`}>
                    {signal.severity || 'low'}
                  </span>
                  <span className="pdf-signal-growth">+{signal.growth_rate != null ? ((signal.growth_rate - 1) * 100).toFixed(0) : '0'}%</span>
                </div>
                <p className="pdf-signal-topic">{signal.topic || 'Unknown'}</p>
                <div className="pdf-signal-stats">
                  <span>Current: {signal.current_engagement?.toFixed(0) ?? '—'}</span>
                  <span>Previous: {signal.previous_engagement?.toFixed(0) ?? '—'}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Forecast Summary ── */}
      {forecastList.length > 0 && (
        <div className="pdf-section">
          <h2 className="pdf-section-title">48-Hour Forecast</h2>
          <table className="pdf-table">
            <thead>
              <tr>
                <th style={{ width: '40%' }}>Topic</th>
                <th>Trend</th>
                <th>Confidence</th>
                <th>Predicted Engagement</th>
              </tr>
            </thead>
            <tbody>
              {forecastList.map((f, i) => (
                <tr key={i}>
                  <td>{f.topic || '—'}</td>
                  <td>
                    <span className={`pdf-trend pdf-trend-${f.trend_prediction || 'stable'}`}>
                      {f.trend_prediction === 'rising' ? '▲' : f.trend_prediction === 'falling' ? '▼' : '●'} {f.trend_prediction || 'stable'}
                    </span>
                  </td>
                  <td className="pdf-cell-number">{f.confidence_score != null ? `${(f.confidence_score * 100).toFixed(0)}%` : '—'}</td>
                  <td className="pdf-cell-number">{f.predicted_engagement?.toFixed(0) ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Cluster Summary ── */}
      {clusters.length > 0 && (
        <div className="pdf-section">
          <h2 className="pdf-section-title">Narrative Clusters</h2>
          <table className="pdf-table">
            <thead>
              <tr>
                <th style={{ width: '35%' }}>Topic</th>
                <th>Posts</th>
                <th>Influence</th>
                <th>Avg Virality</th>
                <th>Keywords</th>
              </tr>
            </thead>
            <tbody>
              {clusters.slice(0, 10).map((c, i) => (
                <tr key={c.cluster_id || i}>
                  <td>{c.topic_label || '—'}</td>
                  <td className="pdf-cell-number">{c.post_count || 0}</td>
                  <td className="pdf-cell-number">{(c.influence_score || 0).toFixed(1)}</td>
                  <td className="pdf-cell-number">{(c.avg_virality || 0).toFixed(1)}</td>
                  <td className="pdf-cell-keywords">{(c.keywords || []).slice(0, 3).join(', ')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Footer ── */}
      <div className="pdf-footer">
        <p>Digital Pulse — Cultural Intelligence Engine</p>
        <p>Report generated on {new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</p>
      </div>
    </div>
  );
}
