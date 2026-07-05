import { useState } from 'react';
import { X } from 'lucide-react';
import { useAuth } from '../context/Authcontext.jsx';
import { api, ApiError } from '../api/client.js';

export default function FeedbackModal({ threadId, onClose, onSubmitted }) {
  const { token, isDemo, guestId } = useAuth();
  const [rating, setRating] = useState('good');
  const [comment, setComment] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(e) {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await api.submitFeedback(isDemo ? null : token, isDemo ? guestId : null, {
        thread_id: threadId,
        rating,
        comment: comment.trim() || undefined,
      });
      onSubmitted();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save feedback.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={overlayStyle} onClick={onClose}>
      <div className="card" style={{ maxWidth: 420, width: '100%' }} onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.1rem', margin: 0 }}>Feedback</h2>
          <button className="btn btn-ghost" onClick={onClose}><X size={16} /></button>
        </div>

        {error && <div className="error-banner">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="field">
            <label className="label">How did it go?</label>
            <div style={{ display: 'flex', gap: 8 }}>
              {['good', 'okay', 'bad'].map((r) => (
                <button type="button" key={r}
                  className="btn"
                  style={rating === r ? { borderColor: 'var(--accent)', color: 'var(--accent)' } : {}}
                  onClick={() => setRating(r)}>
                  {r}
                </button>
              ))}
            </div>
          </div>
          <div className="field">
            <label className="label">Comment (optional)</label>
            <textarea className="textarea" rows={3} value={comment} placeholder="good"
              onChange={(e) => setComment(e.target.value)} />
          </div>
          <button className="btn btn-primary" type="submit" disabled={busy} style={{ width: '100%', justifyContent: 'center' }}>
            {busy ? <span className="spinner" /> : 'Submit feedback'}
          </button>
        </form>
      </div>
    </div>
  );
}

const overlayStyle = {
  position: 'fixed', inset: 0, background: 'rgba(10,13,18,0.6)',
  display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20, zIndex: 60,
};