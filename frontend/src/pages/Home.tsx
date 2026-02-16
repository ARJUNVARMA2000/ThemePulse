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
          <h1 className="logo">ThemePulse</h1>
          <p className="tagline">
            Live classroom theme extraction. Ask a question, let students respond,
            and watch AI surface the key themes in real time.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="create-form">
          <label htmlFor="question" className="form-label">
            Your question for the class
          </label>
          <textarea
            id="question"
            className="form-textarea"
            placeholder="e.g., What do you think deep learning is?"
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
            {loading ? 'Creating...' : 'Create Session'}
          </button>
          {error && <p className="error-text">{error}</p>}
        </form>
      </div>
    </div>
  );
}
