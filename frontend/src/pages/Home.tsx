import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createSession } from '../api';

export default function Home() {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;

    setLoading(true);
    setError('');
    try {
      const data = await createSession(question.trim());
      navigate(`/session/${data.session_id}/admin?token=${data.admin_token}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <div className="container">
        <div className="hero">
          <div className="hero-badge">// mission control</div>
          <h1 className="logo">CLASSPULSE</h1>
          <p className="tagline">
            Deploy a question to your class. Gather live responses.
            Watch AI decode the key themes in real time.
          </p>
          <div className="hero-divider">
            <span>SYS.ONLINE</span>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="create-form">
          <span className="panel-label">// new mission</span>
          <label htmlFor="question" className="form-label">
            Briefing Question
          </label>
          <textarea
            id="question"
            className="form-textarea"
            placeholder="e.g., How do you think Large Language Models work?"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            rows={3}
            maxLength={1000}
            required
          />
          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading || !question.trim()}
          >
            {loading ? 'Initializing...' : 'Launch Session'}
          </button>
          {error && <p className="error-text">{error}</p>}
        </form>

        <div className="footer-badge">classpulse v1.0 // classroom intelligence</div>
      </div>
    </div>
  );
}
