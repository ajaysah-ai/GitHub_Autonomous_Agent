import { useState, useEffect } from 'react';
import { MessagesSquare, CheckCircle2, XCircle } from 'lucide-react';
import { api, ApiError } from '../api/client.js';

export default function AllFeedbacksPage() {
  const [feedbacks, setFeedbacks] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    (async () => {
      try {
        const res = await api.allFeedbacks();
        setFeedbacks(res.feedbacks);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : 'Could not load feedback.');
      }
    })();
  }, []);

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Feedback</h1>
        <p className="page-subtitle">What everyone's tasks looked like, and how they went.</p>
      </div>

      {error && <div className="error-banner">{error}</div>}
      {feedbacks === null && !error && <div className="spinner" />}

      {feedbacks && feedbacks.length === 0 && (
        <div className="empty-state">
          <div className="icon"><MessagesSquare size={28} /></div>
          <p>No feedback yet.</p>
        </div>
      )}

      {feedbacks && feedbacks.length > 0 && (
        <div className="list">
          {feedbacks.map((f, i) => (
            <div key={i} className="card feedback-item">
              <div className="feedback-goal">{f.goal}</div>
              <div className="feedback-meta">
                <span>{f.username}</span>
                <span>·</span>
                <span className={`badge ${f.goal_achieved ? 'badge-ok' : 'badge-danger'}`}>
                  {f.goal_achieved ? <CheckCircle2 size={11} /> : <XCircle size={11} />}
                  {f.goal_achieved ? 'Achieved' : 'Not achieved'}
                </span>
                <span>·</span>
                <span className="badge badge-neutral">{f.rating}</span>
              </div>
              {f.comment && <div className="feedback-comment">{f.comment}</div>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}