export default function LoadingCard({ height = 200 }) {
  return (
    <div
      className="glass-card loading-card"
      style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
    >
      <div className="loading-spinner">
        <div className="spinner-ring" />
        <span className="loading-text">Loading...</span>
      </div>
      <style jsx>{`
        .loading-card {
          background: rgba(255, 255, 255, 0.03);
          animation: pulse 1.5s ease-in-out infinite;
        }
        @keyframes pulse {
          0%, 100% { opacity: 0.6; }
          50% { opacity: 1; }
        }
        .loading-spinner {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 12px;
        }
        .spinner-ring {
          width: 32px;
          height: 32px;
          border: 3px solid rgba(255, 255, 255, 0.1);
          border-top-color: var(--accent-blue);
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        .loading-text {
          font-size: 12px;
          color: var(--text-muted);
          text-transform: uppercase;
          letter-spacing: 1px;
        }
      `}</style>
    </div>
  );
}
