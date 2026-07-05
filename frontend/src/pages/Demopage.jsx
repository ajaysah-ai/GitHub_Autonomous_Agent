import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Terminal, FileText } from 'lucide-react';
import { useAuth } from '../context/Authcontext.jsx';
import { api, ApiError } from '../api/client.js';

export default function DemoPage() {
  const { setDemoSession } = useAuth();
  const navigate = useNavigate();
  const [goal, setGoal] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await api.demoStart(goal);
      setDemoSession(res.guest_id);
      navigate(`/chat/${res.thread_id}`, { state: { seed: res } });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not start demo.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <div className="nav-brand" style={{ justifyContent: 'center', padding: '0 0 18px' }}>
          <Terminal size={18} /> agent.console
        </div>
        <div className="card">
          <h1 className="auth-title">Try the demo</h1>
          <p className="auth-sub">
            <FileText size={13} style={{ verticalAlign: -2, marginRight: 4 }} />
            No account needed — README and requirements.txt generation only. Sign up for repo actions.
          </p>

          {error && <div className="error-banner">{error}</div>}

          <form onSubmit={handleSubmit}>
            <div className="field">
              <label className="label">Your goal</label>
              <textarea className="textarea" value={goal} autoFocus
                placeholder="write a readme for my_project folder"
                onChange={(e) => setGoal(e.target.value)} required />
            </div>
            <button className="btn btn-primary" type="submit" disabled={loading} style={{ width: '100%', justifyContent: 'center' }}>
              {loading ? <span className="spinner" /> : 'Start'}
            </button>
          </form>
        </div>
        <div className="auth-switch">
          Have an account? <Link to="/login"><button type="button">Log in</button></Link>
        </div>
      </div>
    </div>
  );
}