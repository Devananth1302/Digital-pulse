import { useMemo, memo } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { safeNumber, ensureArray, truncate } from '../lib/safeUtils';

const COLORS = ['#00d4ff', '#7b61ff', '#ff3d8e', '#00ff88', '#ff9f43'];

export default memo(function ForecastChart({ forecasts }) {
  // Ensure forecasts is an array
  const safeForecasts = useMemo(() => ensureArray(forecasts), [forecasts]);

  // Build chart data with safety
  const chartData = useMemo(() => {
    if (safeForecasts.length === 0) return [];

    const hourSet = new Set();
    safeForecasts.forEach((f) => {
      ensureArray(f?.data_points).forEach((dp) => {
        if (dp?.hour != null) hourSet.add(dp.hour);
      });
    });
    const hours = [...hourSet].sort((a, b) => a - b);

    return hours.map((h) => {
      const point = { hour: `+${h}h` };
      safeForecasts.forEach((f, i) => {
        const dp = ensureArray(f?.data_points).find((d) => d?.hour === h);
        const value = dp?.projected_engagement;
        point[`topic_${i}`] = value != null ? safeNumber(value, null) : null;
      });
      return point;
    });
  }, [safeForecasts]);

  if (safeForecasts.length === 0) {
    return (
      <div style={{ height: 280, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(255,255,255,0.3)' }}>
        No forecast data available
      </div>
    );
  }

  return (
    <div style={{ height: 280 }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
          <XAxis dataKey="hour" stroke="rgba(255,255,255,0.3)" fontSize={11} />
          <YAxis stroke="rgba(255,255,255,0.3)" fontSize={11} />
          <Tooltip
            contentStyle={{
              background: 'rgba(17,17,50,0.95)',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: 8,
              fontSize: 12,
            }}
            formatter={(value) => [safeNumber(value, 0).toLocaleString(), 'Engagement']}
          />
          <Legend
            formatter={(value) => {
              const idx = parseInt(value.split('_')[1], 10);
              const f = safeForecasts[idx];
              if (!f) return value;
              const topic = truncate(f.topic || 'Unknown', 20);
              const trend = f.trend_prediction || 'stable';
              return `${topic} (${trend})`;
            }}
            wrapperStyle={{ fontSize: 11 }}
          />
          {safeForecasts.slice(0, 5).map((f, i) => (
            <Line
              key={f?.topic || i}
              type="monotone"
              dataKey={`topic_${i}`}
              stroke={COLORS[i % COLORS.length]}
              strokeWidth={2}
              dot={false}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>

      {/* Forecast summary badges */}
      <div style={{ display: 'flex', gap: 8, marginTop: 12, flexWrap: 'wrap' }}>
        {safeForecasts.slice(0, 5).map((f, i) => {
          const topic = truncate(f?.topic || 'Unknown', 25);
          const trend = f?.trend_prediction || 'stable';
          const confidence = safeNumber(f?.confidence_score, 0);

          return (
            <div
              key={f?.topic || i}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '4px 10px',
                background: 'rgba(255,255,255,0.03)',
                borderRadius: 8,
                fontSize: 11,
              }}
            >
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: COLORS[i % COLORS.length] }} />
              <span>{topic}</span>
              <span className={`trend-badge ${trend}`} style={{ padding: '2px 6px', fontSize: 10 }}>
                {confidence > 0 ? `${Math.round(confidence * 100)}%` : '—'}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
});
