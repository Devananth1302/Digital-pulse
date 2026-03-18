import { useState, useRef, memo, useCallback } from 'react';
import { uploadCSV, clearCache } from '../lib/api';

/**
 * Calculate virality score for a single post (client-side).
 * Mirrors backend formula: shares*0.4 + comments*0.3 + likes*0.2 + velocity*0.1
 */
function calculatePostVirality(post) {
  const likes = Number(post.likes) || 0;
  const shares = Number(post.shares) || 0;
  const comments = Number(post.comments) || 0;
  const engagement = likes + shares + comments;

  // Calculate time difference in hours
  let timeDiffHours = 1;
  try {
    const ts = new Date(post.timestamp);
    if (!isNaN(ts.getTime())) {
      timeDiffHours = Math.max(1, (Date.now() - ts.getTime()) / 3600000);
    }
  } catch { /* use default */ }

  const velocity = engagement / timeDiffHours;
  const score = shares * 0.4 + comments * 0.3 + likes * 0.2 + velocity * 0.1;

  return {
    engagement_total: engagement,
    engagement_velocity: Math.round(velocity * 100) / 100,
    virality_score: Math.round(score * 100) / 100,
  };
}

export default memo(function CSVUpload({ onUploadComplete }) {
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [uploadStage, setUploadStage] = useState('');
  const [preview, setPreview] = useState(null);
  const inputRef = useRef(null);

  async function handleFile(file) {
    if (!file || !file.name.endsWith('.csv')) {
      setResult({ error: 'Please select a .csv file' });
      return;
    }

    setUploading(true);
    setResult(null);
    setPreview(null);
    setUploadStage('Parsing CSV...');

    try {
      // Dynamic import PapaParse
      const Papa = (await import('papaparse')).default;

      // Parse CSV client-side first for validation and immediate display
      const parseResult = await new Promise((resolve, reject) => {
        Papa.parse(file, {
          header: true,
          skipEmptyLines: true,
          complete: (results) => resolve(results),
          error: (err) => reject(err),
        });
      });

      if (!parseResult.data || parseResult.data.length === 0) {
        setResult({ error: 'CSV is empty or could not be parsed' });
        setUploading(false);
        setUploadStage('');
        return;
      }

      // Normalize and validate every row
      setUploadStage(`Normalizing ${parseResult.data.length} rows...`);

      const cleaned = parseResult.data
        .filter(row => row.title || row.content) // Skip rows with no title AND no content
        .map((row, i) => {
          const post = {
            post_id: `csv_${Date.now()}_${i}`,
            title: (row.title || 'Untitled').trim(),
            content: (row.content || '').trim(),
            timestamp: row.timestamp || new Date().toISOString(),
            likes: Math.max(0, Number(row.likes) || 0),
            shares: Math.max(0, Number(row.shares) || 0),
            comments: Math.max(0, Number(row.comments) || 0),
            source: 'csv_upload',
            region: row.region || null,
          };

          // Calculate virality metrics client-side
          const metrics = calculatePostVirality(post);
          return { ...post, ...metrics };
        });

      if (cleaned.length === 0) {
        setResult({ error: 'No valid rows found. Ensure CSV has "title" or "content" columns.' });
        setUploading(false);
        setUploadStage('');
        return;
      }

      // Show preview immediately
      setPreview({
        total: parseResult.data.length,
        valid: cleaned.length,
        skipped: parseResult.data.length - cleaned.length,
        sample: cleaned.slice(0, 3),
      });

      // Inject parsed data into dashboard immediately (before backend)
      if (onUploadComplete) {
        onUploadComplete(cleaned);
      }

      // Now send to backend for persistent storage
      setUploadStage('Sending to backend pipeline...');
      clearCache();

      const res = await uploadCSV(file);

      if (res && !res.error) {
        clearCache();

        // Trigger full refresh from backend to get processed data
        setUploadStage('Refreshing from backend...');
        await new Promise(r => setTimeout(r, 1000));

        setResult({
          success: true,
          message: res.message || 'Upload successful',
          rows_read: res.rows_read || parseResult.data.length,
          posts_stored: res.posts_stored || cleaned.length,
          normalized: res.normalized || 0,
          clientParsed: cleaned.length,
        });

        // Final refresh with backend data
        if (onUploadComplete) {
          onUploadComplete(null); // null signals "refresh from API"
        }
      } else {
        // Backend failed but client data is already showing
        setResult({
          success: true,
          message: 'Showing local data (backend sync pending)',
          rows_read: parseResult.data.length,
          posts_stored: cleaned.length,
          normalized: 0,
          clientParsed: cleaned.length,
          backendWarning: res?.error || res?.detail || 'Backend unavailable',
        });
      }
    } catch (err) {
      setResult({ error: 'Parse failed: ' + (err.message || 'Unknown error') });
    }

    setUploading(false);
    setUploadStage('');
  }

  function handleDrop(e) {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files[0];
    handleFile(file);
  }

  function handleDragOver(e) {
    e.preventDefault();
    setDragActive(true);
  }

  return (
    <div style={{ position: 'relative' }}>
      {/* Upload Zone */}
      <div
        className={`upload-zone ${dragActive ? 'active' : ''}`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={() => setDragActive(false)}
        onClick={() => !uploading && inputRef.current?.click()}
        style={{
          padding: 40,
          border: '2px dashed rgba(123, 97, 255, 0.3)',
          borderRadius: 12,
          textAlign: 'center',
          cursor: uploading ? 'wait' : 'pointer',
          transition: 'all 0.2s',
          background: dragActive ? 'rgba(123, 97, 255, 0.1)' : 'transparent',
        }}
      >
        {uploading ? (
          <div>
            <div className="processing-indicator" style={{ marginBottom: 8 }}>
              <span className="processing-dots">
                <span /><span /><span />
              </span>
            </div>
            <div style={{ color: '#7b61ff', fontSize: 14 }}>{uploadStage}</div>
          </div>
        ) : (
          <>
            <div style={{ fontSize: 32, marginBottom: 8 }}>📁</div>
            <div style={{ fontSize: 14, color: 'rgba(255,255,255,0.7)', marginBottom: 8 }}>
              Drop CSV file here or click to browse
            </div>
            <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>
              Required columns: title, content, timestamp, likes, shares, comments
            </div>
          </>
        )}
      </div>

      <input
        ref={inputRef}
        type="file"
        accept=".csv"
        style={{ display: 'none' }}
        onChange={(e) => {
          handleFile(e.target.files[0]);
          e.target.value = '';
        }}
      />

      {/* Full-screen drop overlay */}
      {dragActive && (
        <div
          style={{
            position: 'fixed', inset: 0, zIndex: 999,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: 'rgba(0,0,0,0.8)', backdropFilter: 'blur(4px)',
          }}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={() => setDragActive(false)}
        >
          <div style={{
            fontSize: 24, fontWeight: 600, color: '#7b61ff',
            padding: 40, border: '3px dashed #7b61ff', borderRadius: 16,
          }}>
            Drop CSV file here
          </div>
        </div>
      )}

      {/* Preview - shows immediately after parsing */}
      {preview && !result && (
        <div style={{
          marginTop: 16, padding: 16, borderRadius: 10,
          background: 'rgba(0,212,255,0.08)',
          border: '1px solid rgba(0,212,255,0.2)',
        }}>
          <div style={{ fontSize: 13, color: '#00d4ff', fontWeight: 600, marginBottom: 8 }}>
            Parsed {preview.valid} valid rows
            {preview.skipped > 0 && (
              <span style={{ color: '#ff9f43', fontWeight: 400 }}> ({preview.skipped} skipped)</span>
            )}
          </div>
          <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.5)' }}>
            {preview.sample.map((row, i) => (
              <div key={i} style={{ marginBottom: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {row.title} — virality: {row.virality_score}
              </div>
            ))}
            {preview.valid > 3 && <div>...and {preview.valid - 3} more</div>}
          </div>
        </div>
      )}

      {/* Result toast */}
      {result && (
        <div style={{
          marginTop: 16, padding: 16, borderRadius: 10,
          background: result.error ? 'rgba(255,61,142,0.1)' : 'rgba(0,255,136,0.1)',
          border: `1px solid ${result.error ? 'rgba(255,61,142,0.3)' : 'rgba(0,255,136,0.3)'}`,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              {result.error ? (
                <div style={{ color: '#ff3d8e', fontSize: 13 }}>
                  {result.error}
                </div>
              ) : (
                <>
                  <div style={{ color: '#00ff88', fontSize: 14, fontWeight: 600, marginBottom: 8 }}>
                    Upload Successful
                  </div>
                  <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.6)' }}>
                    <div>Rows parsed: {result.rows_read}</div>
                    <div>Posts stored: {result.posts_stored}</div>
                    {result.clientParsed > 0 && (
                      <div>Client-side: {result.clientParsed} rows processed instantly</div>
                    )}
                  </div>
                  {result.backendWarning && (
                    <div style={{ fontSize: 11, color: '#ff9f43', marginTop: 6 }}>
                      Note: {result.backendWarning}
                    </div>
                  )}
                  <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginTop: 8 }}>
                    Data is live in the dashboard
                  </div>
                </>
              )}
            </div>
            <button
              onClick={() => { setResult(null); setPreview(null); }}
              style={{
                background: 'none', border: 'none', color: 'rgba(255,255,255,0.5)',
                cursor: 'pointer', fontSize: 16, padding: 4,
              }}
            >
              ×
            </button>
          </div>
        </div>
      )}
    </div>
  );
});
