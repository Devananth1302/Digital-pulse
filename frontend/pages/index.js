import Head from 'next/head';
import dynamic from 'next/dynamic';
import { useState, useEffect, useCallback, useRef, useMemo, memo } from 'react';
import Sidebar from '../components/Sidebar';
import PulseScoreCard from '../components/PulseScoreCard';
import NarrativeTable from '../components/NarrativeTable';
import EmergingAlerts from '../components/EmergingAlerts';
import DetailModal from '../components/DetailModal';
import PDFReport from '../components/PDFReport';
import Ticker from '../components/Ticker';
import LoadingCard from '../components/LoadingCard';
import { DashboardSummaryBar } from '../components/InsightBadge';
import { generateDashboardSummary } from '../lib/insightGenerator';
import {
  fetchNarratives,
  fetchPulseScore,
  fetchEmerging,
  fetchForecasts,
} from '../lib/api';

// Lazy load heavy components
const ForecastChart = dynamic(() => import('../components/ForecastChart'), {
  ssr: false,
  loading: () => <LoadingCard height={300} />,
});
const ClusterGraph = dynamic(() => import('../components/ClusterGraph'), {
  ssr: false,
  loading: () => <LoadingCard height={300} />,
});
const ViralityBreakdown = dynamic(() => import('../components/ViralityBreakdown'), {
  ssr: false,
  loading: () => <LoadingCard height={200} />,
});
const RegionalHeatmap = dynamic(() => import('../components/RegionalHeatmap'), {
  ssr: false,
  loading: () => <LoadingCard height={200} />,
});
const CSVUpload = dynamic(() => import('../components/CSVUpload'), {
  ssr: false,
  loading: () => <LoadingCard height={150} />,
});

export default function Dashboard() {
  const [activeView, setActiveView] = useState('dashboard');
  const [pulseData, setPulseData] = useState(null);
  const [narratives, setNarratives] = useState({ posts: [], clusters: [] });
  const [emerging, setEmerging] = useState({ signals: [] });
  const [forecasts, setForecasts] = useState({ forecasts: [] });
  const [selectedPost, setSelectedPost] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [modalData, setModalData] = useState(null);
  const [modalType, setModalType] = useState(null);

  // Debug: Log when selectedPost changes
  useEffect(() => {
    if (selectedPost) {
      console.log('🎯 [Dashboard] selectedPost updated:', {
        hasPost: !!selectedPost.post,
        hasBreakdown: !!selectedPost.virality_breakdown,
        title: selectedPost.post?.title || selectedPost.title,
      });
    } else {
      console.log('🎯 [Dashboard] selectedPost cleared');
    }
  }, [selectedPost]);

  const openModal = useCallback((data, type) => {
    setModalData(data);
    setModalType(type);
  }, []);

  const closeModal = useCallback(() => {
    setModalData(null);
    setModalType(null);
  }, []);

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      // Reduced limits for demo performance (was 50/20/10)
      const [pulse, narr, emerg, fore] = await Promise.all([
        fetchPulseScore(),
        fetchNarratives({ limit: 20 }),  // Reduced from 50
        fetchEmerging({ limit: 10 }),    // Reduced from 20
        fetchForecasts({ limit: 8 }),    // Reduced from 10
      ]);

      // Always update state with safe defaults to prevent stale data
      setPulseData(pulse || null);
      setNarratives({
        posts: narr?.posts || [],
        clusters: narr?.clusters || [],
      });
      setEmerging({
        signals: emerg?.signals || [],
      });
      setForecasts({
        forecasts: fore?.forecasts || [],
      });
      setLastUpdate(new Date());
    } catch (err) {
      console.error('[Digital Pulse] Data fetch failed:', err);
    } finally {
      // CRITICAL: Always set loading to false, even on error
      setLoading(false);
    }
  }, []);

  // Handle CSV upload: accepts parsed data array or null to refresh from API
  const handleUploadComplete = useCallback((csvParsedData) => {
    if (csvParsedData === null) {
      // null means "refresh from backend" - reload everything
      loadAll();
      return;
    }

    if (Array.isArray(csvParsedData) && csvParsedData.length > 0) {
      // Immediately merge CSV data into dashboard state for instant display
      setNarratives((prev) => {
        // Deduplicate by post_id
        const existingIds = new Set(prev.posts.map(p => p.post_id));
        const newPosts = csvParsedData.filter(p => !existingIds.has(p.post_id));
        return {
          ...prev,
          posts: [...newPosts, ...prev.posts],
        };
      });
      setLastUpdate(new Date());

      // Switch to dashboard view to show the data immediately
      setActiveView('dashboard');
    }
  }, [loadAll]);

  useEffect(() => {
    loadAll();
    // Auto-refresh disabled for demo performance
    // Manual refresh available via button in topbar
    // const interval = setInterval(loadAll, 60000);
    // return () => clearInterval(interval);
  }, [loadAll]);

  return (
    <>
      <Head>
        <title>Digital Pulse - Cultural Intelligence Engine</title>
        <meta name="description" content="Contextual Cultural Intelligence Engine" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap"
          rel="stylesheet"
        />
      </Head>

      <div className="app-layout">
        <Sidebar activeView={activeView} onNavigate={setActiveView} />

        <main className="main-content">
          {/* Top bar */}
          <header className="topbar">
            <div>
              <h1 className="topbar-title">
                {activeView === 'dashboard' && 'Dashboard'}
                {activeView === 'narratives' && 'Trending Narratives'}
                {activeView === 'emerging' && 'Emerging Signals'}
                {activeView === 'forecast' && '48-Hour Forecast'}
                {activeView === 'upload' && 'Upload Data'}
              </h1>
              <p className="topbar-sub">
                {lastUpdate
                  ? `Updated ${lastUpdate.toLocaleTimeString()}`
                  : 'Loading...'}
              </p>
            </div>
            <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
              <button className="btn" onClick={loadAll} disabled={loading}>
                {loading ? 'Refreshing...' : 'Refresh'}
              </button>
              <ExportButton
                pulseData={pulseData}
                narratives={narratives}
                emerging={emerging}
                forecasts={forecasts}
              />
            </div>
          </header>

          {/* Ticker */}
          <Ticker posts={(narratives && narratives.posts) || []} />

          {/* Views */}
          {activeView === 'dashboard' && (
            <DashboardView
              pulseData={pulseData}
              narratives={narratives}
              emerging={emerging}
              forecasts={forecasts}
              selectedPost={selectedPost}
              setSelectedPost={setSelectedPost}
              loading={loading}
              onCardClick={openModal}
            />
          )}

          {activeView === 'narratives' && (
            <NarrativesView
              narratives={narratives}
              selectedPost={selectedPost}
              setSelectedPost={setSelectedPost}
              onCardClick={openModal}
            />
          )}

          {activeView === 'emerging' && (
            <EmergingView emerging={emerging} onCardClick={openModal} />
          )}

          {activeView === 'forecast' && (
            <ForecastView forecasts={forecasts} onCardClick={openModal} />
          )}

          {activeView === 'upload' && (
            <UploadView onUploadComplete={handleUploadComplete} />
          )}
        </main>
      </div>

      {/* Detail Modal */}
      {modalData && (
        <DetailModal data={modalData} type={modalType} onClose={closeModal} />
      )}
    </>
  );
}

/* ── Dashboard View ── */
const DashboardView = memo(function DashboardView({ pulseData, narratives, emerging, forecasts, selectedPost, setSelectedPost, loading, onCardClick }) {
  const posts = useMemo(() => narratives?.posts || [], [narratives?.posts]);
  const clusters = useMemo(() => narratives?.clusters || [], [narratives?.clusters]);
  const signals = useMemo(() => emerging?.signals || [], [emerging?.signals]);
  const forecastList = useMemo(() => forecasts?.forecasts || [], [forecasts?.forecasts]);

  // Generate AI-powered dashboard summary (memoized)
  const summary = useMemo(
    () => generateDashboardSummary(pulseData, narratives, emerging, forecasts),
    [pulseData, narratives, emerging, forecasts]
  );

  return (
    <>
      {/* AI Summary Bar */}
      {!loading && summary && <DashboardSummaryBar summary={summary} />}

      <div className="dashboard-grid">
      {/* Pulse Score */}
      <div className="span-3">
        <div className="card-clickable" onClick={() => pulseData && onCardClick(pulseData, 'pulse')}>
          <PulseScoreCard data={pulseData} loading={loading} />
        </div>
      </div>

      {/* Cluster Graph */}
      <div className="span-6">
        <div className="glass-card" style={{ height: 380 }}>
          <div className="section-header">
            <h2>Narrative Clusters</h2>
            <span className="count">{clusters.length} clusters</span>
          </div>
          {clusters.length > 0 || posts.length > 0 ? (
            <ClusterGraph clusters={clusters} posts={posts} />
          ) : (
            <div className="empty-state">No cluster data available</div>
          )}
        </div>
      </div>

      {/* Emerging Alerts */}
      <div className="span-3">
        <EmergingAlerts signals={signals} />
      </div>

      {/* Trending Narratives */}
      <div className="span-8">
        <div className="glass-card">
          <div className="section-header">
            <h2>Trending Narratives</h2>
            <span className="count">{posts.length} posts</span>
          </div>
          {posts.length > 0 ? (
            <NarrativeTable posts={posts} onSelectPost={setSelectedPost} />
          ) : (
            <div className="empty-state">No narratives available yet</div>
          )}
        </div>
      </div>

      {/* Virality Breakdown */}
      <div className="span-4">
        <ViralityBreakdown post={selectedPost} />
      </div>

      {/* Forecast */}
      <div className="span-8">
        <div className="glass-card">
          <div className="section-header">
            <h2>48-Hour Forecast</h2>
          </div>
          {Array.isArray(forecastList) && forecastList.length > 0 ? (
            <ForecastChart forecasts={forecastList} />
          ) : (
            <div className="empty-state" style={{ height: 280 }}>No forecast data available</div>
          )}
        </div>
      </div>

      {/* Regional Heatmap */}
      <div className="span-4">
        <div className="glass-card">
          <div className="section-header">
            <h2>Regional Activity (India)</h2>
          </div>
          <RegionalHeatmap posts={posts} />
        </div>
      </div>
    </div>
    </>
  );
});

/* ── Narratives View ── */
const NarrativesView = memo(function NarrativesView({ narratives, selectedPost, setSelectedPost, onCardClick }) {
  const posts = useMemo(() => narratives?.posts || [], [narratives?.posts]);
  const clusters = useMemo(() => narratives?.clusters || [], [narratives?.clusters]);

  return (
    <div className="dashboard-grid">
      <div className="span-8">
        <div className="glass-card">
          <div className="section-header">
            <h2>All Narratives</h2>
            <span className="count">{posts.length} posts</span>
          </div>
          <NarrativeTable posts={posts} onSelectPost={setSelectedPost} />
        </div>
      </div>
      <div className="span-4">
        <ViralityBreakdown post={selectedPost} />
        <div className="glass-card" style={{ marginTop: 20, height: 320 }}>
          <div className="section-header">
            <h2>Cluster Network</h2>
          </div>
          <ClusterGraph clusters={clusters} posts={posts} />
        </div>
      </div>
    </div>
  );
});

/* ── Emerging View ── */
const EmergingView = memo(function EmergingView({ emerging, onCardClick }) {
  const signals = useMemo(() => emerging?.signals || [], [emerging?.signals]);

  return (
    <div className="dashboard-grid">
      <div className="span-12">
        <div className="glass-card">
          <div className="section-header">
            <h2>Emerging Signal Alerts</h2>
            <span className="count">{signals.length} detected</span>
          </div>
          {signals.length === 0 ? (
            <div className="empty-state" style={{ padding: 60 }}>
              No emerging signals detected yet. The pipeline monitors for growth rate exceeding 150% within a 2-hour window.
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 16 }}>
              {signals.map((signal, i) => (
                <SignalCard key={signal.id || i} signal={signal} onClick={() => onCardClick(signal, 'signal')} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
});

const SignalCard = memo(function SignalCard({ signal, onClick }) {
  const growthRate = signal?.growth_rate;
  const growthPct = (growthRate != null && isFinite(growthRate))
    ? ((growthRate - 1) * 100).toFixed(0)
    : '—';
  const currentEng = signal?.current_engagement;
  const prevEng = signal?.previous_engagement;
  return (
    <div
      className="card-clickable signal-card-item"
      onClick={onClick}
      style={{
        padding: 20, borderRadius: 12,
        background: 'rgba(255,255,255,0.03)',
        borderLeft: `4px solid ${signal?.severity === 'high' ? '#ff3d8e' : signal?.severity === 'medium' ? '#ff9f43' : '#00ff88'}`,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
        <span className={`severity-badge ${signal?.severity || ''}`}>{signal?.severity || 'unknown'}</span>
        <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>
          {signal?.detected_at ? new Date(signal.detected_at).toLocaleString() : ''}
        </span>
      </div>
      <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 8 }}>{signal?.topic || 'Unknown Signal'}</h3>
      <div style={{ display: 'flex', gap: 24, fontSize: 13, color: 'rgba(255,255,255,0.6)' }}>
        <span>Growth: <strong style={{ color: '#00ff88' }}>+{growthPct}%</strong></span>
        <span>Current: {currentEng != null ? Math.round(currentEng).toLocaleString() : '—'}</span>
        <span>Previous: {prevEng != null ? Math.round(prevEng).toLocaleString() : '—'}</span>
      </div>
    </div>
  );
});

/* ── Forecast View ── */
const ForecastView = memo(function ForecastView({ forecasts, onCardClick }) {
  const forecastList = useMemo(() => forecasts?.forecasts || [], [forecasts?.forecasts]);

  return (
    <div className="dashboard-grid">
      <div className="span-12">
        <div className="glass-card">
          <div className="section-header">
            <h2>48-Hour Trend Forecast</h2>
            <span className="count">{forecastList.length} topics</span>
          </div>
          {Array.isArray(forecastList) && forecastList.length > 0 ? (
            <ForecastChart forecasts={forecastList} />
          ) : (
            <div className="empty-state" style={{ height: 280 }}>No forecast data available</div>
          )}
        </div>
      </div>
      {forecastList.length > 0 && (
        <div className="span-12">
          <div className="glass-card">
            <div className="section-header">
              <h2>Forecast Details</h2>
            </div>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Topic</th>
                  <th>Trend</th>
                  <th>Confidence</th>
                  <th>Predicted Engagement</th>
                </tr>
              </thead>
              <tbody>
                {forecastList.map((f, i) => (
                  <tr key={i} className="card-clickable" onClick={() => onCardClick(f, 'forecast')}>
                    <td>{f?.topic ?? '—'}</td>
                    <td><span className={`trend-badge ${f?.trend_prediction || ''}`}>{f?.trend_prediction || '—'}</span></td>
                    <td>{f?.confidence_score != null ? `${Math.round(f.confidence_score * 100)}%` : '—'}</td>
                    <td>{f?.predicted_engagement != null ? Math.round(f.predicted_engagement).toLocaleString() : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
});

/* ── Upload View ── */
const UploadView = memo(function UploadView({ onUploadComplete }) {
  return (
    <div className="dashboard-grid">
      <div className="span-6">
        <div className="glass-card">
          <div className="section-header">
            <h2>Upload CSV Dataset</h2>
          </div>
          <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: 13, marginBottom: 20, lineHeight: 1.6 }}>
            Upload a CSV file with columns: <code>title</code>, <code>content</code>,
            <code> timestamp</code>, <code>likes</code>, <code>shares</code>, <code>comments</code>.
            Data will be processed through the same ingestion pipeline as live sources.
          </p>
          <CSVUpload onUploadComplete={onUploadComplete} />
        </div>
      </div>
      <div className="span-6">
        <div className="glass-card">
          <div className="section-header">
            <h2>Pipeline Flow</h2>
          </div>
          <div className="pipeline-diagram">
            <PipelineStep label="Google News RSS" color="#00d4ff" />
            <PipelineArrow />
            <PipelineStep label="NewsAPI" color="#7b61ff" />
            <PipelineArrow />
            <PipelineStep label="CSV Upload" color="#ff9f43" />
            <PipelineArrow />
            <PipelineStep label="Normalize & Score" color="#00ff88" />
            <PipelineArrow />
            <PipelineStep label="Supabase" color="#ff3d8e" />
          </div>
        </div>
      </div>
    </div>
  );
});

const PipelineStep = memo(function PipelineStep({ label, color }) {
  return (
    <div style={{
      padding: '12px 18px', borderRadius: 10,
      background: `${color}15`, border: `1px solid ${color}30`,
      color, fontSize: 13, fontWeight: 600, textAlign: 'center',
    }}>
      {label}
    </div>
  );
});

const PipelineArrow = memo(function PipelineArrow() {
  return (
    <div style={{ textAlign: 'center', color: 'rgba(255,255,255,0.2)', fontSize: 18, padding: '4px 0' }}>
      ↓
    </div>
  );
});

/* ── Export ── */
const ExportButton = memo(function ExportButton({ pulseData, narratives, emerging, forecasts }) {
  const pdfRef = useRef(null);
  const [exporting, setExporting] = useState(false);
  const [showPdf, setShowPdf] = useState(false);

  const handleExport = async () => {
    setExporting(true);
    setShowPdf(true);

    // Wait for the PDF component to render
    await new Promise((r) => setTimeout(r, 300));

    try {
      const { default: html2canvas } = await import('html2canvas');
      const { default: jsPDF } = await import('jspdf');

      const target = pdfRef.current;
      if (!target) throw new Error('PDF render target not found');

      const canvas = await html2canvas(target, {
        scale: 2,
        useCORS: true,
        backgroundColor: '#ffffff',
        width: 800,
        windowWidth: 800,
      });

      const imgData = canvas.toDataURL('image/png');
      const imgWidth = 210; // A4 width in mm (portrait)
      const imgHeight = (canvas.height * imgWidth) / canvas.width;
      const pageHeight = 297; // A4 height in mm

      const pdf = new jsPDF('p', 'mm', 'a4');
      let position = 0;

      // Multi-page support
      if (imgHeight <= pageHeight) {
        pdf.addImage(imgData, 'PNG', 0, 0, imgWidth, imgHeight);
      } else {
        let remainingHeight = imgHeight;
        while (remainingHeight > 0) {
          pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
          remainingHeight -= pageHeight;
          position -= pageHeight;
          if (remainingHeight > 0) {
            pdf.addPage();
          }
        }
      }

      pdf.save(`digital-pulse-report-${new Date().toISOString().slice(0, 10)}.pdf`);
    } catch (err) {
      console.error('Export failed:', err);
    } finally {
      setShowPdf(false);
      setExporting(false);
    }
  };

  return (
    <>
      <button className="btn" onClick={handleExport} disabled={exporting}>
        {exporting ? 'Exporting...' : 'Export PDF'}
      </button>

      {/* Hidden PDF render target */}
      {showPdf && (
        <div className="pdf-render-target">
          <div ref={pdfRef}>
            <PDFReport
              pulseData={pulseData}
              narratives={narratives}
              emerging={emerging}
              forecasts={forecasts}
              generatedAt={new Date().toLocaleString()}
            />
          </div>
        </div>
      )}
    </>
  );
});
