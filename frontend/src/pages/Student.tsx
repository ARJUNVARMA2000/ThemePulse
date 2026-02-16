import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { getSession, submitResponse } from '../api';

export default function Student() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [question, setQuestion] = useState('');
  const [studentName, setStudentName] = useState('');
  const [answer, setAnswer] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!sessionId) return;
    getSession(sessionId)
      .then((data) => {
        setQuestion(data.question);
        setLoading(false);
      })
      .catch(() => {
        setError('Session not found. It may have expired.');
        setLoading(false);
      });
  }, [sessionId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!sessionId || !studentName.trim() || !answer.trim()) return;

    setSubmitting(true);
    setError('');
    try {
      await submitResponse(sessionId, studentName.trim(), answer.trim());
      setSubmitted(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="page">
        <div className="container">
          <div className="loading">Loading session...</div>
        </div>
      </div>
    );
  }

  if (submitted) {
    return (
      <div className="page">
        <div className="container">
          <div className="success-card">
            <div className="success-icon">&#10003;</div>
            <h2>Response Submitted!</h2>
            <p>Thank you, <strong>{studentName}</strong>. Your response has been recorded.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="container">
        <h1 className="logo logo-small">ThemePulse</h1>

        {error ? (
          <div className="error-card">
            <p>{error}</p>
          </div>
        ) : (
          <>
            <div className="question-display">
              <span className="question-label">Question</span>
              <h2 className="question-text">{question}</h2>
            </div>

            <form onSubmit={handleSubmit} className="response-form">
              <label htmlFor="name" className="form-label">Your name</label>
              <input
                id="name"
                type="text"
                className="form-input"
                placeholder="Enter your name"
                value={studentName}
                onChange={(e) => setStudentName(e.target.value)}
                maxLength={100}
                required
              />

              <label htmlFor="answer" className="form-label">Your answer</label>
              <textarea
                id="answer"
                className="form-textarea"
                placeholder="Share your thoughts..."
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                rows={5}
                maxLength={5000}
                required
              />

              <button
                type="submit"
                className="btn btn-primary"
                disabled={submitting || !studentName.trim() || !answer.trim()}
              >
                {submitting ? 'Submitting...' : 'Submit Response'}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
