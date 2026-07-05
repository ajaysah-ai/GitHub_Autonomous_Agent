import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { History as HistoryIcon, CheckCircle2, Clock } from 'lucide-react';
import { useAuth } from '../context/Authcontext.jsx';
import { api, ApiError } from '../api/client.js';

export default function HistoryPage() {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [threads, setThreads] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    (async () => {
      try {
        const res = await api.getHistory(token);
        setThreads(res.threads);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : 'Could not load history.');
      }
    })();
  }, [token]);

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">History</h1>
        <p className="page-subtitle">Every goal you've run, across all sessions.</p>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {threads === null && !error && <div className="spinner" />}

      {threads && threads.length === 0 && (
        <div className="empty-state">
          <div className="icon"><HistoryIcon size={28} /></div>
          <p>No tasks yet.</p>
          <p>Start one from "New goal" in the sidebar.</p>
        </div>
      )}

      {threads && threads.length > 0 && (
        <div className="list">
          {threads.map((t) => (
            <div key={t.thread_id} className="list-item" onClick={() => navigate(`/chat/${t.thread_id}`)}>
              <div className="list-item-main">
                <div className="list-item-title">{t.goal}</div>
                <div className="list-item-sub">{t.last_message}</div>
              </div>
              <span className={`badge ${t.completed ? 'badge-ok' : t.awaiting_input ? 'badge-pending' : 'badge-neutral'}`}>
                {t.completed ? <CheckCircle2 size={12} /> : <Clock size={12} />}
                {t.completed ? 'Done' : t.awaiting_input ? 'Waiting' : 'Ended'}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}