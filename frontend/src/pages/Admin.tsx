import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { QRCodeSVG } from 'qrcode.react';
import { getSession, getStreamUrl } from '../api';
import type { SummaryPayload, StatusPayload } from '../api';
import ThemeCard from '../components/ThemeCard';

export default function Admin() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [searchParams] = useSearchParams();
  const adminToken = searchParams.get('token') || '';

  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [responseCount, setResponseCount] = useState(0);
  const [minRequired, setMinRequired] = useState(3);
  const [summary, setSummary] = useState<SummaryPayload | null>(null);
  const [sseError, setSseError] = useState('');
  const [connected, setConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const responseCountRef = useRef(responseCount);
  useEffect(() => { responseCountRef.current = responseCount; }, [responseCount]);

  // Load session info
  useEffect(() => {
    if (!sessionId) return;
    getSession(sessionId)
      .then((data) => {
        setQuestion(data.question);
        setResponseCount(data.response_count);
        setLoading(false);
      })
      .catch(() => {
        setError('Session not found');
        setLoading(false);
      });
  }, [sessionId]);

  // SSE connection
  const connectSSE = useCallback(() => {
    if (!sessionId || !adminToken) return;

    const url = getStreamUrl(sessionId, adminToken);
    const es = new EventSource(url);
    eventSourceRef.current = es;

    es.onopen = () => {
      setConnected(true);
      setSseError('');
    };

    es.addEventListener('summary', (e) => {
      try {
        const data: SummaryPayload = JSON.parse(e.data);
        setSummary(data);
        setResponseCount(data.response_count);
        setSseError('');
      } catch {
        console.error('Failed to parse summary event');
      }
    });

    es.addEventListener('status', (e) => {
      try {
        const data: StatusPayload = JSON.parse(e.data);
        setResponseCount(data.response_count);
        setMinRequired(data.min_required);
      } catch {
        console.error('Failed to parse status event');
      }
    });

    es.addEventListener('error', (e) => {
      try {
        const data = JSON.parse((e as MessageEvent).data);
        setSseError(data.message || 'Summarization error');
        setResponseCount(data.response_count || responseCountRef.current);
      } catch {
        // Connection error, will auto-reconnect
      }
    });

    es.onerror = () => {
      setConnected(false);
      es.close();
      // Auto-reconnect after 3 seconds
      setTimeout(connectSSE, 3000);
    };
  }, [sessionId, adminToken]);

  useEffect(() => {
    connectSSE();
    return () => {
      eventSourceRef.current?.close();
    };
  }, [connectSSE]);

  const studentUrl = sessionId
    ? `${window.location.origin}/session/${sessionId}`
    : '';

  const copyLink = () => {
    navigator.clipboard.writeText(studentUrl).catch(() => {});
  };

  if (loading) {
    return (
      <div className="page">
        <div className="container">
          <div className="loading">Initializing command center...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page">
        <div className="container">
          <div className="error-card"><p>{error}</p></div>
        </div>
      </div>
    );
  }

  return (
    <div className="page admin-page">
      <div className="container admin-container">
        <header className="admin-header">
          <h1 className="logo logo-small">CLASSPULSE</h1>
          <div className="connection-badge" data-connected={connected}>
            <span className="connection-dot" />
            {connected ? 'Live Telemetry' : 'Signal Lost'}
          </div>
        </header>

        <div className="admin-layout">
          {/* Sidebar with QR + info */}
          <aside className="admin-sidebar">
            <div className="question-display">
              <span className="question-label">// mission briefing</span>
              <h2 className="question-text">{question}</h2>
            </div>

            <div className="qr-section">
              <p className="qr-label">// uplink coordinates</p>
              <div className="qr-wrapper">
                <QRCodeSVG value={studentUrl} size={180} level="M" />
              </div>
              <div className="link-row">
                <input
                  type="text"
                  className="form-input link-input"
                  value={studentUrl}
                  readOnly
                />
                <button className="btn btn-secondary" onClick={copyLink}>
                  Copy
                </button>
              </div>
            </div>

            <div className="response-counter">
              <span className="counter-label-top">// incoming signals</span>
              <span className="counter-number">{responseCount}</span>
              <span className="counter-label">
                {responseCount === 1 ? 'response' : 'responses'}
              </span>
            </div>

            {responseCount < minRequired && (
              <p className="waiting-text">
                Awaiting {minRequired - responseCount} more signal{minRequired - responseCount !== 1 ? 's' : ''} to begin decode...
              </p>
            )}
          </aside>

          {/* Main area with theme cards */}
          <main className="admin-main">
            {sseError && (
              <div className="error-banner">{sseError}</div>
            )}

            {summary && summary.themes.length > 0 ? (
              <>
                <h2 className="themes-heading">// decoded signals</h2>
                <div className="themes-grid">
                  {summary.themes.map((theme, i) => (
                    <ThemeCard key={i} theme={theme} index={i} />
                  ))}
                </div>
                <p className="summary-meta">
                  Decoded from {summary.response_count} transmissions
                  {summary.model_used && <> &middot; {summary.model_used}</>}
                </p>
              </>
            ) : (
              <div className="empty-state">
                <div className="radar-sweep">
                  <div className="cross-h" />
                  <div className="cross-v" />
                </div>
                <h2>Scanning for signals</h2>
                <p>
                  As students transmit responses, AI will automatically
                  decode and surface the key themes from their answers.
                </p>
              </div>
            )}
          </main>
        </div>
      </div>
    </div>
  );
}
